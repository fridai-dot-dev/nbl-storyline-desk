# Lessons

Patterns learned while building this project. Read at session start.

1. **Agents roam; code gates what goes out.** Bart wants agents to branch beyond the starting data (history, social threads, other sources). Determinism belongs at the output: rechecks, sign-off, packet rules. Don't shrink the research to a fixed pipeline. (2026-10-28)
2. **Don't cut items from Bart's core workflow on my own judgement.** I dropped the pre-game run as "my call" and it was central to the workflow. Ask before removing anything from the brief's core loop. (2026-10-28)
3. **Timing requirements come from the job, not the data.** The post-game briefing has a hard cap of 30 minutes after the final whistle. I'd stretched cutoffs to suit the data instead. (2026-10-28)
4. **Cap memory before any heavy data job on this machine.** WSL has ~7.7 GB. Parsing a 370 MB R object in pure Python crashed WSL repeatedly and killed the session and its background agents. (2026-10-28)
5. **Live runs share Bart's Pro window with the working session.** Keep the session lean while runs are in flight, start each run at the top of a fresh window, and treat a "session limit" result as a failed run, never as output. (2026-10-28)
6. **Track every background job.** Launch long work with the harness's tracked background mode, never a detached `&` subshell. Otherwise no completion notice arrives and the work looks stalled. (2026-10-28)
7. **Bring Bart into choosing follow-up questions.** The angle is a creative, editorial call. Present candidates grounded in what the data can answer, then shape the question together before running it. (2026-10-28)
8. **Live runs find what offline checks can't.** Every major defect after the first build came from a real run: abandoned background specialists, search order, lock contention, the whistle versus stats sign-off, session limits, and buried record claims. Run real data early, and turn each surprise into a failing check before fixing it. (2026-10-28)
