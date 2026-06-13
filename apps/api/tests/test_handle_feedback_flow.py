"""Baseline tests for feedback → verification state flow (unit-level, no DB)."""

from uuid import uuid4

from app.models.entities import Feedback, Task, TaskRun, TaskStatus
from app.services.verifier import VERDICT_NEEDS_CONTINUE, VERDICT_PASSED, VerifierService


def test_success_without_criteria_should_pass_verifier():
    """Regression: empty criteria + Agent success must still pass."""
    task = Task(id=uuid4(), name="t", objective="obj", success_criteria={}, failure_criteria={})
    feedback = Feedback(
        run_id=uuid4(),
        feedback_id="f1",
        status="success",
        result_payload={"summary": "done"},
    )
    run = TaskRun(id=uuid4(), task_id=task.id, status=TaskStatus.REVIEWING.value)
    outcome = VerifierService().verify(task, feedback, run, agent_status="success")
    assert outcome.verdict == VERDICT_PASSED


def test_criteria_unmet_should_continue():
    task = Task(
        id=uuid4(),
        name="t",
        objective="obj",
        success_criteria={
            "rules": [{"type": "field_equals", "path": "done", "value": True}],
            "match": "all",
        },
    )
    feedback = Feedback(
        run_id=uuid4(),
        feedback_id="f1",
        status="success",
        result_payload={"done": False},
    )
    run = TaskRun(id=uuid4(), task_id=task.id, iteration_count=1)
    outcome = VerifierService().verify(task, feedback, run, agent_status="success")
    assert outcome.verdict == VERDICT_NEEDS_CONTINUE


def test_state_machine_reviewing_to_iterating_allowed():
    from app.services.state_machine import StateMachineService

    sm = StateMachineService(db=None)  # type: ignore
    assert sm.can_transition(TaskStatus.REVIEWING.value, TaskStatus.ITERATING.value)
    assert sm.can_transition(TaskStatus.ITERATING.value, TaskStatus.RUNNING.value)
