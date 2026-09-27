"""Resolve dataset.yaml paths produced by scripts/data/prepare_<name>.py."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def dataset_yaml_path(name: str) -> Path:
    path = REPO_ROOT / "data" / name / "processed" / "dataset.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist. Run scripts/data/prepare_{name}.py first."
        )
    return path
