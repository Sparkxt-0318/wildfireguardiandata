# firewitness coordination folder

This branch (`coord`) is the shared copy of `wildfire 3 (1)/firewitness_coord/`. Clone it there:

    git clone -b coord https://github.com/Sparkxt-0318/wildfireguardiandata "/home/user/wildfire 3 (1)/firewitness_coord"

## Who writes what (never edit another track's files)
- Track `<t>` writes ONLY `board/<t>.md` (its BOARD section) and `outbox/<t>.md` (its messages to others).
- The orchestrator writes `BOARD.md` (assembled from board/), `inbox/*.md`, `NEEDS.md`, `logs/`.
- To sync: `git pull --rebase -q origin coord && git add board/<t>.md outbox/<t>.md && git commit -qm "<t> heartbeat" && git push -q origin HEAD:coord` (retry pull+push if rejected).

## Rules
- NEVER write a key, token or password here. This branch is public.
- Heartbeat: every 30 minutes and at the end of each step, rewrite board/<t>.md: state, last heartbeat (UTC ISO time), current step, blockers, PRs open, session id.
- Read inbox/<t>.md every 30 minutes and act on new items.
- A request to another track goes in outbox/<t>.md, headed `## <UTC time> TO <track>: <subject>`. Keep working on something else meanwhile.
- When every step, gate and deliverable in the brief is done: state `DONE <commit hash on main>`.
