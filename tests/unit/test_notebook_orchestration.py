import json
from pathlib import Path
import runpy
import sys
from unittest.mock import Mock

import pytest

from skypoints.notebooks import execute_stage, main, validate_partition_date


@pytest.mark.parametrize("value", [None, 23112026, "231126", "23-11-2026", "31022026", "２３１１２０２６"])
def test_invalid_processing_dates_fail_before_a_notebook_is_opened(tmp_path, value):
    with pytest.raises(ValueError, match="[Pp]artition date"):
        execute_stage("raw", value, run_id="test", project_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("value", ["01012026", "29022024", "23112026"])
def test_valid_dates_remain_strings_with_leading_zeroes(value):
    assert validate_partition_date(value) == value


def test_unprepared_source_notebooks_cannot_run_with_the_wrong_date(tmp_path):
    source = tmp_path / "src" / "skypoints" / "stages" / "raw.ipynb"
    source.parent.mkdir(parents=True)
    original = json.dumps({"cells": [{"cell_type": "code", "metadata": {}, "source": []}]})
    source.write_text(original)

    with pytest.raises(RuntimeError, match="approved notebook configuration changes"):
        execute_stage("raw", "23112026", run_id="test", project_root=tmp_path)

    assert source.read_text() == original
    assert not (tmp_path / "logs").exists()


def test_command_line_receives_airflow_environment_and_uses_the_runtime_project(tmp_path, monkeypatch):
    monkeypatch.setenv("SKYPOINTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("SKYPOINTS_PARTITION_DATE", "01012026")
    monkeypatch.setenv("SKYPOINTS_RUN_ID", "manual__selected-date")
    monkeypatch.setenv("SKYPOINTS_TASK_ATTEMPT", "2")
    monkeypatch.delenv("SKYPOINTS_NOTEBOOK_OUTPUT_DIR", raising=False)
    monkeypatch.setenv("SKYPOINTS_NOTEBOOK_KERNEL", "skypoints")
    monkeypatch.setattr(sys, "argv", ["notebooks", "--stage", "raw"])
    executor = Mock(return_value=tmp_path / "executed.ipynb")
    monkeypatch.setattr("skypoints.notebooks.execute_stage", executor)

    assert main() == 0
    executor.assert_called_once_with(
        "raw", "01012026", run_id="manual__selected-date", attempt=2,
        project_root=tmp_path, output_root=tmp_path / "logs" / "notebooks",
        kernel_name="skypoints",
    )


@pytest.fixture(scope="module")
def manual_dag():
    path = Path(__file__).resolve().parents[2] / "dags" / "skypoints.py"
    return runpy.run_path(str(path))["dag"]


def test_dag_runs_three_notebooks_in_order_only_when_manually_triggered(manual_dag):
    assert manual_dag.schedule is None
    assert manual_dag.catchup is False
    assert manual_dag.max_active_runs == 1
    assert manual_dag.max_active_tasks == 1
    assert manual_dag.task_ids == ["load_raw", "load_staging", "load_gold"]
    assert manual_dag.get_task("load_raw").downstream_task_ids == {"load_staging"}
    assert manual_dag.get_task("load_staging").downstream_task_ids == {"load_gold"}
    assert manual_dag.get_task("load_gold").downstream_task_ids == set()
    for task in manual_dag.tasks:
        assert task.trigger_rule == "all_success"
        assert task.do_xcom_push is False


def test_trigger_requires_a_date_and_passes_it_as_environment_data(manual_dag):
    parameter = manual_dag.params.get_param("partition_date")
    with pytest.raises(Exception, match="[Nn]o value|[Rr]equired"):
        parameter.resolve()
    assert parameter.resolve("01012026") == "01012026"
    for task in manual_dag.tasks:
        assert task.env["SKYPOINTS_PARTITION_DATE"] == "{{ params.partition_date }}"
        assert "{{" not in task.bash_command
        assert task.append_env is True
