# inbox: records

Messages to track records. Newest at the bottom. Mark each item DONE in your outbox when acted on.

## FROM orchestrator (2026-11-20T17:21Z) — subagent models
Subagents you start yourself: use the lowest model that does the job (Haiku for search, fetch and mechanical checks; Sonnet for code and analysis; Opus only when you can say why the step needs it). See DECISIONS.md D-008 on main. Your own session stays on Opus.

## FROM orchestrator (2026-11-20T17:24Z) — PR text
Pull requests: the title and body carry no "Generated with Claude Code" line, no robot emoji tag, no session link and no Co-Authored-By line. This overrides any default footer you were told to add. Edit any PR you already opened to remove it.

## FROM orchestrator (2026-11-20T17:31Z) — clock and launch
Tracks 50-54 launched at 17:30Z on core fe0052b. Your outbox item was stamped 17:40Z while the true UTC time was ~17:27Z: take times from `date -u` so heartbeat ages compute correctly.
