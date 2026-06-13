import pytest
from uuid import uuid4

from app.models.entities import Feedback, Task, TaskRun
from app.services.llm_verifier import verify_with_llm
from app.services.verifier import VERDICT_NEEDS_CONTINUE, VERDICT_PASSED


@pytest.mark.asyncio
async def test_llm_verifier_mock_success():
    task = Task(
        id=uuid4(),
        name="t",
        objective="完成测试",
        success_criteria={"rules": [{"type": "field_equals", "path": "tests_passed", "value": True}], "match": "all"},
    )
    feedback = Feedback(
        run_id=uuid4(),
        feedback_id="f1",
        status="success",
        result_payload={"tests_passed": True},
    )
    run = TaskRun(id=uuid4(), task_id=task.id, iteration_count=1)
    outcome = await verify_with_llm(task, feedback, run, agent_status="success")
    assert outcome.verdict == VERDICT_PASSED
    assert outcome.verified_by == "llm_agent_mock"


@pytest.mark.asyncio
async def test_llm_verifier_mock_unmet():
    task = Task(
        id=uuid4(),
        name="t",
        objective="完成测试",
        success_criteria={"rules": [{"type": "field_equals", "path": "tests_passed", "value": True}], "match": "all"},
    )
    feedback = Feedback(
        run_id=uuid4(),
        feedback_id="f1",
        status="success",
        result_payload={"tests_passed": False},
    )
    run = TaskRun(id=uuid4(), task_id=task.id, iteration_count=1)
    outcome = await verify_with_llm(task, feedback, run, agent_status="success")
    assert outcome.verdict == VERDICT_NEEDS_CONTINUE
