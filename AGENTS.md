# Agent Guidelines & Engineering Principles

## Principles (pstack & Clean Code)
1. **Boundary Discipline**: Keep infrastructure calls strictly encapsulated in `infrastructure/`. Domain logic in `services/` must remain decoupled from specific SDK bindings.
2. **Deterministic Verification**: Every change must be verified against the 10 benchmark test cases in `eval/cases/` using `python eval/score.py`.
3. **Zero Slop**: Write direct, active-voice descriptions. No decorative jargon or superficial filler.
4. **Human-in-the-Loop Safety**: All destructive or high-risk state changes must pass through the `Approve` checkpoint interrupt before synchronization.
5. **Canonical Trajectories**: Every run must log full JSON traces and formatted Markdown summaries to `trajectories/`.

## Common Commands
- Run test suite: `pytest -v`
- Run evaluation benchmarks: `python eval/score.py`
- Run pipeline on a single case: `python agents/graph.py --case eval/cases/case_01.json`
- Launch Web Control Cockpit: `uvicorn web.app:app --reload`
