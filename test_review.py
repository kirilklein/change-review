import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import review


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-b", "feature")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.write("delivery.py", "def send_batch(batch):\n    return deliver(batch)\n")
        self.write(
            "caller.py",
            "from delivery import send_batch\n\ndef upload(batch):\n    return send_batch(batch)\n",
        )
        self.write("README.md", "Shared delivery library.\n")
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return review.git(self.repo, *args)

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def commit(self):
        self.git("add", ".")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-m", "Test snapshot")

    def change(self):
        self.write(
            "delivery.py", "def send_batch(batch):\n    return retry(deliver, batch)\n"
        )
        return review.collect(self.repo, intent="Retry failed uploads.")

    def annotations(self, snapshot):
        return {
            "snapshot_id": snapshot["snapshot_id"],
            "summary": "Retries are now shared.",
            "annotations": [
                {
                    "hunk_id": snapshot["files"][0]["hunks"][0]["id"],
                    "title": "Shared retries",
                    "importance": "focus",
                    "what": "Retries deliveries.",
                    "why": "Retry failed uploads.",
                    "why_basis": "stated intent",
                    "where": "Used by upload.",
                    "check": "Are retries idempotent?",
                    "evidence_ids": [snapshot["evidence"][0]["id"]],
                    "related_hunks": [],
                }
            ],
        }

    def test_working_tree_includes_staged_unstaged_and_untracked_without_mutating_git(
        self,
    ):
        self.change()
        self.git("add", "delivery.py")
        self.write(
            "delivery.py",
            "def send_batch(batch):\n    return retry(deliver, batch, attempts=3)\n",
        )
        self.write("new file.py", "VALUE = 1\n")
        status = self.git("status", "--porcelain")
        staged = self.git("diff", "--cached")
        snapshot = review.collect(self.repo)
        self.assertEqual(
            {f["path"] for f in snapshot["files"]}, {"delivery.py", "new file.py"}
        )
        self.assertIn("attempts=3", snapshot["files"][0]["patch"])
        self.assertEqual(self.git("status", "--porcelain"), status)
        self.assertEqual(self.git("diff", "--cached"), staged)
        self.assertTrue(any(e["path"] == "caller.py" for e in snapshot["evidence"]))

    def test_committed_head_ignores_dirty_files_and_uses_revision_context(self):
        self.change()
        self.commit()
        head = self.git("rev-parse", "HEAD").strip()
        self.write("delivery.py", "UNCOMMITTED_SECRET = 123\n")
        self.write("caller.py", "UNCOMMITTED_CALLER = 123\n")
        snapshot = review.collect(self.repo, base=self.base, head=head)
        self.assertFalse(snapshot["working_tree"])
        self.assertNotIn("UNCOMMITTED", json.dumps(snapshot))
        self.assertIn("retry(deliver", snapshot["files"][0]["patch"])

    def test_base_comparison_uses_merge_base(self):
        self.git("branch", "base-branch")
        self.change()
        self.commit()
        feature = self.git("rev-parse", "HEAD").strip()
        self.git("switch", "base-branch")
        self.write("base-only.py", "BASE_ONLY = True\n")
        self.commit()
        snapshot = review.collect(self.repo, base="base-branch", head=feature)
        self.assertEqual(snapshot["base"], self.base)
        self.assertEqual([f["path"] for f in snapshot["files"]], ["delivery.py"])

    def test_deleted_renamed_empty_and_unusual_paths(self):
        self.git("mv", "delivery.py", "moved file.py")
        self.write('a "quote" <tag>.py', "x = 1\n")
        self.write("empty.py", "")
        snapshot = review.collect(self.repo)
        files = {f["path"]: f for f in snapshot["files"]}
        self.assertIn("delivery.py", files)
        self.assertIn("moved file.py", files)
        self.assertIn('a "quote" <tag>.py', files)
        self.assertIn("empty.py", files)
        self.assertTrue(
            any(
                l["kind"] == "del"
                for h in files["delivery.py"]["hunks"]
                for l in h["lines"]
            )
        )

    def test_exclusions_do_not_read_sensitive_protocol_binary_or_symlink_targets(self):
        self.write(".env", "TOKEN=DO_NOT_READ")
        self.write("protocol/nsqip/example.json", '{"DO_NOT_READ": true}')
        (self.repo / "image.bin").write_bytes(b"\x00DO_NOT_READ")
        outside = self.root / "outside.txt"
        outside.write_text("DO_NOT_READ")
        (self.repo / "linked.py").symlink_to(outside)
        snapshot = review.collect(self.repo)
        self.assertEqual(len(snapshot["omitted"]), 4)
        self.assertNotIn("DO_NOT_READ", json.dumps(snapshot))

    def test_annotations_are_bound_to_content_and_links_are_validated(self):
        snapshot = self.change()
        annotations = self.annotations(snapshot)
        review.validate_annotations(snapshot, annotations)
        annotations["annotations"][0]["evidence_ids"] = ["made-up"]
        with self.assertRaisesRegex(review.ReviewError, "evidence_ids"):
            review.validate_annotations(snapshot, annotations)
        self.write("delivery.py", "def send_batch(batch):\n    return False\n")
        changed = review.collect(self.repo)
        with self.assertRaisesRegex(review.ReviewError, "different snapshot"):
            review.validate_annotations(changed, annotations)

    def test_deleted_line_numbers_and_no_newline_marker(self):
        patch_text = "@@ -2,2 +2,1 @@ def f():\n-old\n-older\n+new\n\\ No newline at end of file\n"
        lines = review.parse_hunks(patch_text, "f1")[0]["lines"]
        self.assertEqual(
            [(l["old"], l["new"]) for l in lines],
            [(2, None), (3, None), (None, 2), (None, None)],
        )

    def test_pathspec_characters_are_literal_and_do_not_include_other_files(self):
        self.write("[a].py", "VALUE = 1\n")
        self.write("a.py", "OTHER = 2\n")
        self.commit()
        self.write("[a].py", "VALUE = 3\n")
        self.write("a.py", "OTHER = 4\n")
        snapshot = review.collect(self.repo)
        file = next(f for f in snapshot["files"] if f["path"] == "[a].py")
        self.assertIn("VALUE = 3", file["patch"])
        self.assertNotIn("OTHER", file["patch"])

    def test_diff_preserves_unicode_line_separator_inside_source_line(self):
        hunk = review.parse_hunks('@@ -0,0 +1 @@\n+text = "a\u2028b"\n', "f1")[0]
        self.assertEqual(len(hunk["lines"]), 1)
        self.assertEqual(hunk["lines"][0]["text"], 'text = "a\u2028b"')

    def test_render_does_not_allow_source_to_escape_json_script(self):
        snapshot = self.change()
        snapshot["intent"] = '</script><script>alert("xss")</script>'
        output = self.root / "review.html"
        review.render(snapshot, None, output)
        html = output.read_text()
        self.assertNotIn(snapshot["intent"], html)
        embedded = html.split('<script id="review-data" type="application/json">')[
            1
        ].split("</script>")[0]
        self.assertEqual(json.loads(embedded)["snapshot"]["intent"], snapshot["intent"])

    def test_pr_uses_immutable_commit_ids(self):
        self.change()
        self.commit()
        head = self.git("rev-parse", "HEAD").strip()
        metadata = {
            "number": 7,
            "title": "Shared retries",
            "body": "Retry uploads",
            "url": "https://github.com/example/repo/pull/7",
            "baseRefOid": self.base,
            "headRefOid": head,
            "headRefName": "feature",
            "baseRefName": "dev",
        }
        original_run = review.run

        def fake_run(args, **kwargs):
            return (
                json.dumps(metadata)
                if args[0] == "gh"
                else original_run(args, **kwargs)
            )

        with patch.object(review, "run", side_effect=fake_run):
            snapshot = review.collect(self.repo, pr="7")
        self.assertEqual(snapshot["head"], head)
        self.assertEqual(snapshot["title"], "Shared retries")
        self.assertFalse(snapshot["working_tree"])

    def test_cli_round_trip_with_a_fake_claude_process(self):
        self.change()
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text(
            f"#!{sys.executable}\nimport json, sys\n"
            "args = sys.argv\nassert args[args.index('--tools') + 1] == ''\n"
            "assert '--strict-mcp-config' in args\n"
            "snapshot = json.loads(sys.stdin.read().split('\\n\\nSNAPSHOT\\n')[1])\n"
            "print(json.dumps({'structured_output': {'snapshot_id': snapshot['snapshot_id'], 'summary': 'Transport fixture', 'annotations': []}}))\n"
        )
        fake.chmod(0o755)
        output = self.root / "output"
        result = subprocess.run(
            [
                sys.executable,
                str(review.ROOT / "review.py"),
                "--repo",
                str(self.repo),
                "--explain",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "request.txt").is_file())
        self.assertIn("Transport fixture", (output / "index.html").read_text())
        snapshot = json.loads((output / "snapshot.json").read_text())
        self.assertEqual(snapshot["snapshot_id"], review.fingerprint(snapshot))


if __name__ == "__main__":
    unittest.main()
