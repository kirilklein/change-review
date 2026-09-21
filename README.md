# Change Review

A small local diff viewer with hover explanations, pinned context, source evidence,
related changes, and a suggested reading order. Output is a standalone HTML file:
no server, JavaScript dependencies, or CDN. Requires Python 3.10+ and Git.

## Try it

```bash
git clone git@github.com:kirilklein/change-review.git
cd change-review
python3 review.py \
  --repo /path/to/your/worktree --base origin/dev --explain --open
```

`--explain` uses your installed Claude CLI and its existing login. Run `claude auth
login` in your terminal if needed. It sends the captured diff, bounded source
excerpts, and supplied intent to Claude using your account. It does not resume
your coding conversation. Add `--intent 'The original request'` to preserve the
reason for the change, or use the existing-session workflow below.

Without `--explain`, the viewer opens with the real diff and source context but
no AI explanations. This mode makes no model calls.

### Choose a comparison

```bash
# Staged, unstaged, and untracked changes relative to HEAD
python3 review.py --repo /path/to/worktree --explain --open

# Everything on this worktree since it diverged from dev, including local edits
python3 review.py --repo /path/to/worktree --base origin/dev --explain --open

# A committed branch, ignoring local edits
python3 review.py --repo /path/to/repo --base origin/dev --head feature-name --explain --open

# A PR, using its exact base/head commits and description
python3 review.py --repo /path/to/repo --pr 123 --explain --open
```

PR URLs also work with `--pr`. Requires `gh` authentication and both PR commits
already present in the local repository. Fetch the PR branch and its base first
if needed. The tool does not fetch, checkout, stage, or edit the reviewed repo.
Rename detection is disabled: moves appear as deletion and addition in this version.

### Use the agent session that wrote the code

Prepare the review without a model call:

```bash
python3 review.py --repo /path/to/worktree --base origin/dev \
  --intent 'Your original request' --output /tmp/my-review
```

In Claude Code or another coding-agent session, ask:

> Read /tmp/my-review/request.txt and produce the requested JSON as
> /tmp/my-review-annotations.json. Use the supplied source evidence. If this
> session contains additional rationale, keep it explicitly marked as inferred
> unless it is also in the captured intent. Do not edit the code.

Then render the same snapshot with those annotations:

```bash
python3 review.py --snapshot /tmp/my-review/snapshot.json \
  --annotations /tmp/my-review-annotations.json --output /tmp/my-review-explained --open
```

This import validates the snapshot ID and all source/hunk links. Existing output
directories are refused to avoid overwriting earlier reviews. Without `--output`,
each run gets a unique temporary directory. Keep output outside the reviewed repo.

## Read the review

- Hover **Context** for a quick explanation; click to pin it beside the diff.
- **Focus first** shows the blocks the model considers worth your attention.
- **Read together** connects related edits. Source buttons open captured excerpts
  with line numbers and before/after labels.
- **Mark read** saves progress in this browser for this exact snapshot.
- Open `index.html` in a browser, or open the HTML path in Claude Desktop's Code
  tab to use its Browser pane.

## Limits of this prototype

Explanations are model suggestions, not verified correctness or test results.
Rationale is labeled stated, inferred, or unknown. Context includes changed-file
excerpts, README/overview text, and up to eight files with lexical references to
changed declarations. These references are not a verified call graph. Context is
bounded at 80 KB; source excerpts shown in the viewer are exactly what goes into
the model request. The review is a fixed snapshot; regenerate after editing.

Binary files, symlinks, submodules, files over 300 KB, common credential filenames,
and protocol JSON are omitted with visible reasons. Diffs beyond 250 KB omit
additional files. This is a filename exclusion list, not a secret scanner; review
what is in the snapshot before sharing it. The HTML contains the captured source.

The Claude process has no tools or configured MCP servers and uses a temporary
working directory. A failed model call exits with an error and leaves the
unannotated report and request available for retry or manual annotation.

## Verify

```bash
python3 -m unittest -v
```

Tests cover Git comparisons, source versions, exclusions, annotation validation,
safe embedding, and the CLI transport with a fake Claude executable. No model
calls are made by the tests.
