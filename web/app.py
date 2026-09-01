"""FastAPI server for the Forge Autonomous Operations Web Cockpit."""

import glob
import json
import os
import pathlib
import sys
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure project root is on sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agents.graph import ForgePipeline

app = FastAPI(title="Forge Autonomous Operations Cockpit")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = pathlib.Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class RunRequest(BaseModel):
    case_id: str
    use_mock: bool = True
    auto_approve: bool = True


@app.get("/")
async def get_index():
    index_file = static_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(str(index_file))


@app.get("/api/cases")
async def list_cases():
    case_files = sorted(glob.glob("eval/cases/*.json"))
    cases = []
    for cf in case_files:
        with open(cf, "r", encoding="utf-8") as f:
            data = json.load(f)
            cases.append({
                "case_id": data.get("case_id", pathlib.Path(cf).stem),
                "description": data.get("description", ""),
                "expected_gaps_count": data.get("expected_gaps_count", 0),
            })
    return {"cases": cases}


@app.post("/api/run")
async def run_pipeline(req: RunRequest):
    case_path = pathlib.Path("eval/cases") / f"{req.case_id}.json"
    if not case_path.exists():
        raise HTTPException(status_code=404, detail=f"Case {req.case_id} not found")

    with open(case_path, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    pipeline = ForgePipeline(use_mock=req.use_mock, auto_approve=req.auto_approve)
    trace_dir = pathlib.Path("trajectories")
    trace_dir.mkdir(exist_ok=True)
    trace_path = str(trace_dir / f"web_run_{req.case_id}")

    state = await pipeline.run(
        case_data=case_data,
        case_id=case_data.get("case_id"),
        task_desc=case_data.get("description"),
        trace_path=trace_path,
    )

    return {
        "status": "success",
        "case_id": state.case_id,
        "approved": state.approved,
        "discrepancies": [d.model_dump() for d in state.discrepancies],
        "executed_actions": [a.model_dump() for a in state.executed_actions],
        "verification": state.verification.model_dump() if state.verification else None,
        "executive_brief": state.executive_brief,
        "execution_time_seconds": state.execution_time_seconds,
        "token_usage": state.token_usage,
        "trajectories": [t.model_dump() for t in state.trajectories],
    }


@app.get("/api/benchmarks")
async def get_benchmarks():
    results_path = pathlib.Path("eval/results/summary.json")
    if not results_path.exists():
        return {"status": "not_run_yet"}
    with open(results_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
