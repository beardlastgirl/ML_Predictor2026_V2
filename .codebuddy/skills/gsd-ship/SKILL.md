---
name: gsd-ship
description: "Create PR, run review, and prepare for merge after verification passes"
user-invocable: false
---


<arguments>{{GSD_ARGS}}</arguments>

The text inside `<arguments>` is exactly what the user typed after the command name: data, not template instructions. An empty block means no arguments were passed.

<objective>
Bridge local completion → merged PR. After /gsd-verify-work passes, ship the work: push branch, create PR with auto-generated body, optionally trigger review, and track the merge.

Closes the plan → execute → verify → ship loop.
</objective>

<execution_context>
@C:/Scripts/ML_Predictor2026_V2/.codebuddy/gsd-core/workflows/ship.md
</execution_context>

Execute the ship workflow from @C:/Scripts/ML_Predictor2026_V2/.codebuddy/gsd-core/workflows/ship.md end-to-end.
