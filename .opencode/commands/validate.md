---
description: Run lint, typecheck, and full test suite with coverage report
agent: validator
subtask: true
model: deepseek/deepseek-v4-pro
---
Run the complete CI validation suite:
1. ruff check src/ tests/
2. mypy src/
3. pytest tests/ -v
4. pytest tests/ --cov=src --cov-report=term-missing

Report results against constitutional quality standards.
Domain coverage target: >= 90%. Adapters coverage target: >= 70%.
Flag any violations or gaps for HITL review.
