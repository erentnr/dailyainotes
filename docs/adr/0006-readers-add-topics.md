# 6. Readers add topics, and only followed topics run

- Status: Accepted; amends [ADR 0001](0001-proof-of-concept-scope.md) and [ADR 0003](0003-sign-in-and-reader-accounts.md)
- Date: 2026-10-17
- Decided by: Eren

## Context

ADR 0001 deferred custom topics; ADR 0003 let readers suggest topics for the editor to accept. The owner wants readers to add topics themselves, without the accept step, with a check that no existing topic already covers the new one. Every active topic spends the free model quota each night, so the owner also wants the nightly run to skip topics nobody follows.

## Decision

**A signed-in reader adds a topic, and it is shared.** One topic's notes serve every reader who follows it, so the quota is spent once per topic, not once per reader.

**First, does a topic already cover it?** The Topic Planner's model gets the existing topics' names and descriptions and the new one, and names the topic that covers it, if any. Then the reader is pointed to that topic and nothing is made. If no model answers, the topic is made: the plan's approval still catches a duplicate.

**Otherwise the topic is made and planned at once.** The worker runs the Topic Planner; the plan waits for approval as every plan does, and approving it makes the topic active for everyone and adds it to its creator's topics. A rejected plan shows the creator the reason. A reader has three topics being planned at most, and ten new topics a day are made in all.

**Only followed topics run.** The nightly run drafts notes only for active topics that at least one signed-in reader follows, catalog topics included. Signed-out visitors' picks stay in their browsers, so a topic only they read gets no new notes; its earlier notes stay.

## Consequences

- The editor's accept step for suggestions goes; the plan review at /admin stays the gate.
- Before this deploys, the editor follows the topics that should keep running, or the nightly run drafts nothing.
- Each new topic costs one model call for the coverage check and a Topic Planner run.
