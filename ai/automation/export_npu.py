"""CLI to export trained model checkpoints to RKNN format."""
import argparse
import datetime
import json
import subprocess
from pathlib import Path

import yaml

from ai.core.rknn.baseline import ExportConfig, export_baseline

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = Path(__file__).resolve().parent / "runs"


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", help="an existing directory under ai/automation/runs/")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    train_cfg = yaml.safe_load((run_dir / "config.yaml").read_text())
    weights = run_dir / "weights" / "best.pt"

    export_cfg = ExportConfig(weights=str(weights), dataset=train_cfg["dataset"])
    rknn_model_dir = export_baseline(export_cfg)

    benchmark = {
        "run_id": args.run_id,
        "export_tier": "baseline_native_api",
        "rknn_model_dir": rknn_model_dir,
        "exported_at": datetime.datetime.now().isoformat(),
        "git_commit": git_commit(),
        # Metrics requiring on-device inference are left unpopulated until benchmark_npu.py is run.
        "map50_95_fp32": None,
        "map50_95_int8": None,
        "latency_ms": None,
        "fps": None,
        "status": "exported, mAP/latency not computed by this script yet",
    }
    out_path = run_dir / "npu_benchmark.json"
    out_path.write_text(json.dumps(benchmark, indent=2) + "\n")
    print(f"Done: {out_path}")


if __name__ == "__main__":
    main()
