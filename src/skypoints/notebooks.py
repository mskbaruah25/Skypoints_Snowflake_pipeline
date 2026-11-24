"""Execute one notebook in a fresh kernel and save its results separately."""

import argparse
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGES = ("raw", "staging", "gold")


def validate_partition_date(value: str) -> str:
    """Require a real date written as exactly eight ASCII digits."""
    if (
        not isinstance(value, str)
        or len(value) != 8
        or not value.isascii()
        or not value.isdigit()
    ):
        raise ValueError("Partition date must be a string in DDMMYYYY format, such as 23112026.")
    try:
        parsed = datetime.strptime(value, "%d%m%Y")
    except ValueError as exc:
        raise ValueError(f"Partition date {value!r} is not a valid calendar date.") from exc
    if parsed.strftime("%d%m%Y") != value:
        raise ValueError("Partition date must use DDMMYYYY format.")
    return value


def execute_stage(
    stage: str,
    partition_date: str,
    *,
    run_id: str,
    attempt: int = 1,
    project_root: Path = PROJECT_ROOT,
    output_root: Path | None = None,
    kernel_name: str = "skypoints",
) -> Path:
    """Run a source notebook without changing the original file."""
    partition_date = validate_partition_date(partition_date)
    if stage not in STAGES:
        raise ValueError(f"Unknown notebook stage: {stage!r}.")
    if attempt < 1:
        raise ValueError("Task attempt must be at least 1.")

    source = project_root / "src" / "skypoints" / "stages" / f"{stage}.ipynb"
    notebook = json.loads(source.read_text())
    parameter_cells = [
        cell for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
        and "parameters" in cell.get("metadata", {}).get("tags", [])
    ]
    if len(parameter_cells) != 1:
        raise RuntimeError(
            f"{source.name} needs one cell tagged 'parameters' before Airflow can run it. "
            "Apply the approved notebook configuration changes first."
        )

    # Keep dates, separate manual runs, and retries in different output directories.
    # Hashing the run ID also prevents slashes or other path characters entering it.
    run_folder = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]
    output_root = output_root if output_root is not None else project_root / "logs" / "notebooks"
    destination = (
        output_root / partition_date / run_folder / f"attempt-{attempt}" / f"{stage}.ipynb"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Import only at execution time; DAG parsing never loads notebook dependencies.
    import papermill

    logging.info("Running %s for partition %s; output: %s", stage, partition_date, destination)
    papermill.execute_notebook(
        input_path=str(source),
        output_path=str(destination),
        parameters={"partition_date": partition_date},
        kernel_name=kernel_name,
        cwd=str(project_root),
        log_output=True,
        progress_bar=False,
        start_timeout=120,
        execution_timeout=3600,
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one SkyPoints notebook for a selected date.")
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--partition-date", default=os.environ.get("SKYPOINTS_PARTITION_DATE"))
    parser.add_argument("--run-id", default=os.environ.get("SKYPOINTS_RUN_ID", "local"))
    parser.add_argument("--attempt", type=int, default=os.environ.get("SKYPOINTS_TASK_ATTEMPT", "1"))
    args = parser.parse_args()

    try:
        partition_date = validate_partition_date(args.partition_date)
    except ValueError as exc:
        parser.error(str(exc))

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    project_root = Path(os.environ.get("SKYPOINTS_PROJECT_ROOT", PROJECT_ROOT))
    output_root = Path(os.environ.get(
        "SKYPOINTS_NOTEBOOK_OUTPUT_DIR", project_root / "logs" / "notebooks"
    ))
    destination = execute_stage(
        args.stage,
        partition_date,
        run_id=args.run_id,
        attempt=args.attempt,
        project_root=project_root,
        output_root=output_root,
        kernel_name=os.environ.get("SKYPOINTS_NOTEBOOK_KERNEL", "skypoints"),
    )
    print(f"Completed {args.stage} for partition {partition_date}. Results: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
