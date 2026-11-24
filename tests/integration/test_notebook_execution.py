"""Small local kernels only: these tests do not start Spark, Docker, or Snowflake."""

import hashlib
import nbformat
from papermill.exceptions import PapermillExecutionError
import pytest

from skypoints.notebooks import execute_stage


def make_notebook(project_root, stage, code):
    source = project_root / "src" / "skypoints" / "stages" / f"{stage}.ipynb"
    source.parent.mkdir(parents=True, exist_ok=True)
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell("partition_date = None", metadata={"tags": ["parameters"]}),
            *[nbformat.v4.new_code_cell(cell) for cell in code],
        ],
        metadata={"language_info": {"name": "python"}},
    )
    nbformat.write(notebook, source)
    return source


def test_real_kernel_receives_selected_date_and_retries_keep_separate_results(tmp_path):
    source = make_notebook(tmp_path, "raw", [
        'assert partition_date == "01012026"\n'
        'assert isinstance(partition_date, str)\n'
        'print("Processed " + partition_date)',
    ])
    original = source.read_bytes()

    outputs = [
        execute_stage(
            "raw", "01012026", run_id="manual__/../../other", attempt=attempt,
            project_root=tmp_path,
        )
        for attempt in (1, 2)
    ]

    assert outputs[0] != outputs[1]
    assert source.read_bytes() == original
    for output in outputs:
        assert output.is_relative_to(tmp_path / "logs" / "notebooks")
        executed = nbformat.read(output, as_version=4)
        assert executed.metadata.papermill.parameters.partition_date == "01012026"
        assert executed.metadata.papermill.exception is None
        assert "Processed 01012026" in executed.cells[-1].outputs[0].text


def test_notebook_failure_is_propagated_and_keeps_debug_output(tmp_path):
    marker = tmp_path / "must-not-run.txt"
    source = make_notebook(tmp_path, "staging", [
        'raise RuntimeError("Deliberate test failure")',
        f'from pathlib import Path\nPath({str(marker)!r}).write_text("wrong")',
    ])
    original = source.read_bytes()

    with pytest.raises(PapermillExecutionError, match="Deliberate test failure"):
        execute_stage("staging", "23112026", run_id="failure", project_root=tmp_path)

    assert not marker.exists()
    assert source.read_bytes() == original
    run_folder = hashlib.sha256(b"failure").hexdigest()[:16]
    output = tmp_path / "logs" / "notebooks" / "23112026" / run_folder / "attempt-1" / "staging.ipynb"
    executed = nbformat.read(output, as_version=4)
    assert executed.metadata.papermill.exception is True
