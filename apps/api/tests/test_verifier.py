import pytest
from uuid import uuid4

from app.models.entities import Feedback, Task, TaskRun
from app.services.verifier import VERDICT_FAILED, VERDICT_NEEDS_CONTINUE, VERDICT_PASSED, VerifierService


def _task(**kwargs) -> Task:
    return Task(id=uuid4(), name="t", objective="obj", **kwargs)


def _feedback(status: str, payload: dict | None = None) -> Feedback:
    return Feedback(
        run_id=uuid4(),
        feedback_id="fb1",
        status=status,
        result_payload=payload or {},
    )


def _run() -> TaskRun:
    return TaskRun(id=uuid4(), task_id=uuid4(), iteration_count=1)


@pytest.fixture
def verifier():
    return VerifierService()


def test_compat_mode_success_passes(verifier):
    task = _task(success_criteria={}, failure_criteria={})
    outcome = verifier.verify(task, _feedback("success"), _run(), agent_status="success")
    assert outcome.verdict == VERDICT_PASSED
    assert outcome.signals.get("compat_mode") is True


def test_compat_mode_requires_action_continues(verifier):
    task = _task(success_criteria={}, failure_criteria={})
    outcome = verifier.verify(task, _feedback("requires_action"), _run(), agent_status="requires_action")
    assert outcome.verdict == VERDICT_NEEDS_CONTINUE


def test_success_criteria_all_rules_pass(verifier):
    task = _task(
        success_criteria={
            "rules": [
                {"type": "field_equals", "path": "tests_passed", "value": True},
                {"type": "field_exists", "path": "report_url"},
            ],
            "match": "all",
        }
    )
    outcome = verifier.verify(
        task,
        _feedback("success", {"tests_passed": True, "report_url": "http://x"}),
        _run(),
        agent_status="success",
    )
    assert outcome.verdict == VERDICT_PASSED


def test_success_criteria_unmet_needs_continue(verifier):
    task = _task(
        success_criteria={
            "rules": [{"type": "field_equals", "path": "tests_passed", "value": True}],
            "match": "all",
        }
    )
    outcome = verifier.verify(
        task,
        _feedback("success", {"tests_passed": False}),
        _run(),
        agent_status="success",
    )
    assert outcome.verdict == VERDICT_NEEDS_CONTINUE


def test_failure_criteria_triggers_failed(verifier):
    task = _task(
        success_criteria={"rules": [{"type": "field_equals", "path": "ok", "value": True}], "match": "all"},
        failure_criteria={
            "rules": [{"type": "field_exists", "path": "fatal_error"}],
            "match": "any",
        },
    )
    outcome = verifier.verify(
        task,
        _feedback("success", {"fatal_error": "boom", "ok": True}),
        _run(),
        agent_status="success",
    )
    assert outcome.verdict == VERDICT_FAILED


def test_status_in_rule(verifier):
    task = _task(
        success_criteria={
            "rules": [{"type": "status_in", "values": ["success", "completed"]}],
            "match": "all",
        }
    )
    outcome = verifier.verify(task, _feedback("completed"), _run(), agent_status="completed")
    assert outcome.verdict == VERDICT_PASSED
