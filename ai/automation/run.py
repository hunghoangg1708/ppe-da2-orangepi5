"""CLI entrypoint for running standardized training, evaluation, and logging."""
import argparse
import csv
import datetime
import importlib
import shutil
import subprocess
from pathlib import Path

import yaml

from ai.core.trainer import TrainConfig, evaluate, train

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTOMATION_DIR = Path(__file__).resolve().parent
RUNS_DIR = AUTOMATION_DIR / "runs"
LEADERBOARDS_DIR = AUTOMATION_DIR / "leaderboards"


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def sort_plots(source_dir: Path, plots_dir: Path, split_label: str) -> None:
    """Organize generated plot artifacts into structured directories by split."""
    stats_dir = plots_dir / "dataset_stats"
    samples_dir = plots_dir / "sample_predictions" / split_label
    curves_dir = plots_dir / "eval_curves" / split_label
    for d in (stats_dir, samples_dir, curves_dir):
        d.mkdir(parents=True, exist_ok=True)

    for f in list(source_dir.glob("*.jpg")) + list(source_dir.glob("*.png")):
        if f.name.startswith(("labels.jpg", "labels_correlogram")):
            dest = stats_dir / f.name
        elif f.name.startswith(("train_batch", "val_batch")):
            dest = samples_dir / f.name
        else:
            dest = curves_dir / f.name
        shutil.move(str(f), str(dest))


def append_leaderboard(dataset: str, row: dict) -> None:
    LEADERBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    path = LEADERBOARDS_DIR / f"{dataset}.csv"
    is_new = not path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    model_weights = importlib.import_module(f"ai.models.{cfg['model']}").WEIGHTS

    run_id = f"{datetime.date.today().isoformat()}_{cfg['dataset']}_{cfg['model']}_{cfg['epochs']}ep"

    train_cfg = TrainConfig(
        model=model_weights,
        dataset=cfg["dataset"],
        epochs=cfg["epochs"],
        imgsz=cfg.get("imgsz", 640),
        batch=cfg.get("batch", 16),
        seed=cfg["seed"],
        device=cfg.get("device", "0"),
        project=str(RUNS_DIR),
        run_name=run_id,
    )

    model = train(train_cfg)
    run_dir = RUNS_DIR / run_id

    results_csv = run_dir / "results.csv"
    if results_csv.exists():
        shutil.move(str(results_csv), run_dir / "metrics.csv")

    sort_plots(run_dir, run_dir / "plots", split_label="val")

    test_results = evaluate(
        model, cfg["dataset"], split="test", project=str(run_dir), run_name="test_eval"
    )
    test_eval_dir = run_dir / "test_eval"
    sort_plots(test_eval_dir, run_dir / "plots", split_label="test")
    shutil.rmtree(test_eval_dir, ignore_errors=True)

    shutil.copy(args.config, run_dir / "config.yaml")
    (run_dir / "git_commit.txt").write_text(git_commit() + "\n")

    append_leaderboard(
        cfg["dataset"],
        {
            "run_id": run_id,
            "model": cfg["model"],
            "epochs": cfg["epochs"],
            "seed": cfg["seed"],
            "test_map50": round(float(test_results.box.map50), 4),
            "test_map50_95": round(float(test_results.box.map), 4),
            "test_precision": round(float(test_results.box.mp), 4),
            "test_recall": round(float(test_results.box.mr), 4),
        },
    )

    print(f"Done: {run_dir}")


if __name__ == "__main__":
    main()
