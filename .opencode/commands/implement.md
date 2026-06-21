---
description: Execute implementation tasks following TDD — Red → Green → Refactor
agent: implementer
subtask: true
model: deepseek/deepseek-v4-pro
---
Execute the next pending implementation task from the plan.
Follow TDD strictly: write failing test → write code → verify green → refactor.
Respect hexagonal architecture, SOLID, and all constitutional constraints.
One task per invocation. Report results to HITL after each task.

Load context from @docs/constitution.md, @docs/plan.md, and @docs/adr/.
