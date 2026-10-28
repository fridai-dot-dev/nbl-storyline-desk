# Lessons

Patterns learned while building this project. Read at session start.

1. **Agents roam; code gates what goes out.** Bart wants agents to branch beyond the starting data (history, social threads, other sources). Determinism belongs at the output: rechecks, sign-off, packet rules. Don't shrink the research to a fixed pipeline. (2026-10-28)
2. **Don't cut items from Bart's core workflow on my own judgement.** I dropped the pre-game run as "my call" and it was central to the workflow. Ask before removing anything from the brief's core loop. (2026-10-28)
3. **Timing requirements come from the job, not the data.** The post-game briefing has a hard cap of 30 minutes after the final whistle. I'd stretched cutoffs to suit the data instead. (2026-10-28)
4. **Cap memory before any heavy data job on this machine.** WSL has ~7.7 GB. Parsing a 370 MB R object in pure Python crashed WSL repeatedly and killed the session and its background agents. (2026-10-28)
