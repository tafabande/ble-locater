"""Unit tests for subprocess cancellation, process termination, and concurrency locking."""
import os
import sys
import time
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from server.app import (
    _terminate_process_tree,
    _is_pipeline_running,
    cancel_training_run,
    trigger_training_run,
    TrainingRequest,
    web_service_state,
    _training_launch_lock,
)
import server.app as app_module


def test_terminate_process_tree_live_process():
    """Verify _terminate_process_tree terminates a running subprocess, waits, and reaps exit code."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    assert proc.poll() is None, "Subprocess should be actively running."

    success = _terminate_process_tree(proc, timeout=2.0)
    assert success is True, "Process tree termination should return True."
    assert proc.poll() is not None, "Subprocess must be terminated and reaped by the OS."


def test_terminate_process_tree_already_exited():
    """Verify _terminate_process_tree safely handles a process that already terminated."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.exit(0)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    proc.wait(timeout=2.0)
    assert proc.poll() is not None

    success = _terminate_process_tree(proc, timeout=1.0)
    assert success is True


@pytest.mark.anyio
async def test_prevent_concurrent_training_runs():
    """Verify trigger_training_run rejects secondary execution when a run is already active."""
    with _training_launch_lock:
        original_status = web_service_state["training_job"]["status"]
        web_service_state["training_job"]["status"] = "TRAINING"

    try:
        req = TrainingRequest(algorithm="XGBoost", dataset="observations.csv")
        with pytest.raises(HTTPException) as exc_info:
            await trigger_training_run(req)
        assert exc_info.value.status_code == 400
        assert "already in progress" in str(exc_info.value.detail)
    finally:
        with _training_launch_lock:
            web_service_state["training_job"]["status"] = original_status


@pytest.mark.anyio
async def test_cancel_training_run_terminates_and_resets():
    """Verify cancel_training_run cleanly reaps active process and marks job state CANCELLED."""
    # Spawn dummy pipeline process
    dummy_proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    app_module._active_pipeline_proc = dummy_proc

    try:
        res = await cancel_training_run()
        assert res["status"] == "ok"
        assert res["was_running"] is True
        assert app_module._active_pipeline_proc is None
        assert dummy_proc.poll() is not None
        assert web_service_state["training_job"]["status"] == "CANCELLED"
    finally:
        if dummy_proc.poll() is None:
            dummy_proc.kill()
        app_module._active_pipeline_proc = None


def test_terminate_process_tree_multiple_descendants():
    """Verify _terminate_process_tree kills both parent and all spawned child processes."""
    import psutil
    script = (
        "import subprocess, sys, time\n"
        "p1 = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "p2 = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "print('READY', flush=True)\n"
        "time.sleep(30)\n"
    )
    parent = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        text=True
    )
    line = parent.stdout.readline().strip()
    assert line == "READY"

    # Identify children via psutil
    p_obj = psutil.Process(parent.pid)
    children = p_obj.children(recursive=True)
    assert len(children) >= 2

    # Terminate process tree
    success = _terminate_process_tree(parent, timeout=3.0)
    assert success is True
    assert parent.poll() is not None

    # Verify every child process was terminated
    for c in children:
        assert not c.is_running() or c.status() == psutil.STATUS_ZOMBIE


@pytest.mark.anyio
async def test_cancellation_race_handling():
    """Verify rapid/concurrent cancel invocations resolve cleanly without deadlocks or errors."""
    import anyio
    dummy_proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    app_module._active_pipeline_proc = dummy_proc

    try:
        # Launch 3 simultaneous cancel requests
        async with anyio.create_task_group() as tg:
            results = []
            async def _do_cancel():
                r = await cancel_training_run()
                results.append(r)
            for _ in range(3):
                tg.start_soon(_do_cancel)

        assert len(results) == 3
        assert all(r["status"] == "ok" for r in results)
        assert dummy_proc.poll() is not None
    finally:
        if dummy_proc.poll() is None:
            dummy_proc.kill()
        app_module._active_pipeline_proc = None
