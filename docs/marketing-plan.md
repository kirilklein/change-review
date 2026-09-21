# Change Review: marketing and launch plan

Saved September 21, 2026. Status: proposed; no public launch yet.

## Positioning

**Your agent wrote the code. Make it yours.**

Explore the diff, understand its consequences, and follow the evidence—without
reading another wall of AI prose.

Lead with the moment after a coding agent finishes: the code works, but the
programmer still needs to understand the change before taking responsibility for
it. The product helps them inspect and question it. Avoid implying that generated
explanations prove correctness or that suggested ordering is a verified risk score.

## First audience

Start with programmers who use coding agents daily and review the resulting code
themselves. The initial workflow fits Claude Code users and people who can ask
their existing agent session to annotate a captured snapshot.

The early question is whether this helps them build a mental model of their own
changes. Broad team adoption and enterprise workflows can wait for that evidence.

## The demonstration

Create a 30-second recording and an interactive version of the same fictional
shared-retries example:

1. Open the review at the shared delivery change.
2. Hover to reveal that manual uploads now retry too.
3. Open the evidence for the unchanged upload caller.
4. Return to the diff, mark the block read, and let it collapse.
5. Expand it again with the read marker intact, or continue to the next file.

The memorable moment: **“An unchanged file now behaves differently.”**

Keep the recording focused on that discovery. Show the evidence that supports it;
do not spend the opening explaining the interface or listing features.

## Assets to prepare

- [ ] Public interactive demo using fictional code, with no account or install.
- [ ] A short screen recording of the demonstration above.
- [ ] README opening with the pitch, current screenshot, demo link, and quick start.
- [ ] One clear path from the demo to reviewing the visitor's own branch.
- [ ] A short technical post explaining the problem, design decisions, and limits.

The repository was private when this plan was written. Decide whether to publish
the source or host a separate demo before sharing installation links publicly.
The current self-contained HTML output is suitable for a static demo.

## Pilot before a broader launch

- [ ] Invite 5–10 developers who already review agent-written code.
- [ ] Have them use it on one real change of their own.
- [ ] Watch where they hesitate, lose their place, or need more explanation.
- [ ] Ask: “What did this help you understand that the diff alone didn't?”
- [ ] Ask what felt unnecessary and what they still had to look up elsewhere.
- [ ] Fix recurring friction and use their language to improve the pitch.

This is a qualitative pilot, not a performance benchmark. Avoid time-saving or
bug-detection claims until they have supporting measurements.

## Distribution

First share the demo and a concrete technical story with relevant developer
communities where we already participate. Ask for feedback on a real review task.

Then consider a Show HN submission once the demo is publicly usable. Its
[guidelines](https://news.ycombinator.com/showhn.html) emphasize something people
can try, ideally without signup barriers. Be available to discuss the work and
answer questions; do not solicit votes.

Working title: **“Show HN: Change Review — understand the code your agent wrote”**

## What to measure

The first useful signal: **does someone review a second change without a reminder?**

Also record whether they finish their first review, discover a useful consequence,
and can explain why they would use the tool again. Collect this through pilot
feedback initially. Stars and launch traffic are secondary discovery signals.

## Next action

Prepare the public-ready fictional demo and its 30-second recording, then run the
small pilot. Use the feedback to decide when the broader launch is ready.
