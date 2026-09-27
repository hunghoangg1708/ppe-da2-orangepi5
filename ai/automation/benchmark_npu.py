"""CLI to benchmark an exported RKNN model on an RK3588 device.

Populates latency, throughput, and quantized mAP metrics into npu_benchmark.json.
"""
import argparse
import datetime
import json
from pathlib import Path

import yaml

from ai.core.rknn.benchmark import connect_board, measure_latency, measure_map_drop

RUNS_DIR = Path(__file__).resolve().parent / "runs"
LEADERBOARDS_DIR = Path(__file__).resolve().parent / "leaderboards"


def fp32_row(dataset: str, run_id: str) -> dict:
    import csv

    with (LEADERBOARDS_DIR / f"{dataset}.csv").open() as f:
        for row in csv.DictReader(f):
            if row["run_id"] == run_id:
                return row
    raise ValueError(f"No leaderboard row for run_id={run_id} in {dataset}.csv")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", help="an existing directory under ai/automation/runs/")
    parser.add_argument("device_id", help="board address, e.g. 192.168.1.50:5555")
    parser.add_argument("--core-mask", default="AUTO", choices=["AUTO", "CORE_0", "CORE_1", "CORE_2", "CORE_0_1", "CORE_0_1_2"])
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    benchmark = json.loads((run_dir / "npu_benchmark.json").read_text())
    train_cfg = yaml.safe_load((run_dir / "config.yaml").read_text())
    dataset = train_cfg["dataset"]

    rknn_path = next(Path(benchmark["rknn_model_dir"]).glob("*.rknn"))
    fp32 = fp32_row(dataset, args.run_id)

    with connect_board(str(rknn_path), args.device_id, core_mask=args.core_mask) as rknn:
        sdk_version_raw = rknn.get_sdk_version()
        latency = measure_latency(rknn)
        accuracy = measure_map_drop(rknn, dataset)

    benchmark["benchmarked_at"] = datetime.datetime.now().isoformat()
    benchmark["board"] = {
        "target": "rk3588",
        "device_id": args.device_id,
        # Store raw SDK version string returned by runtime
        "sdk_version_raw": str(sdk_version_raw),
    }
    benchmark["benchmark_config"] = {"core_mask": args.core_mask}
    benchmark["accuracy"] = {
        "map50_fp32": float(fp32["test_map50"]),
        "map50_95_fp32": float(fp32["test_map50_95"]),
        "precision_fp32": float(fp32["test_precision"]),
        "recall_fp32": float(fp32["test_recall"]),
        **accuracy,
    }
    benchmark["latency"] = {"latency_ms": latency["latency_ms"], "fps": latency["fps"]}
    benchmark["resource"] = {
        "npu_time_us": latency["npu_time_us"],
        "cpu_time_us": latency["cpu_time_us"],
        "cpu_fallback_ops": latency["cpu_fallback_ops"],
    }
    benchmark["energy"] = {
        "measured": False,
        "reason": "Orange Pi 5 has no built-in power sensor; requires external power meter",
    }
    benchmark.pop("map50_95_fp32", None)
    benchmark.pop("map50_95_int8", None)
    benchmark.pop("latency_ms", None)
    benchmark.pop("fps", None)
    benchmark["status"] = "benchmarked"

    out_path = run_dir / "npu_benchmark.json"
    out_path.write_text(json.dumps(benchmark, indent=2) + "\n")
    print(f"Done: {out_path}")


if __name__ == "__main__":
    main()
