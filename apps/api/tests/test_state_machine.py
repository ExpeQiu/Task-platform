import pytest
from app.models.entities import TaskStatus
from app.services.state_machine import TRANSITIONS, StateMachineService


def test_valid_transitions():
    assert TaskStatus.READY.value in TRANSITIONS[TaskStatus.DRAFT.value]
    assert TaskStatus.SUCCESS.value in TRANSITIONS[TaskStatus.REVIEWING.value]
    assert TaskStatus.SCHEDULED.value in TRANSITIONS[TaskStatus.FAILED.value]


def test_can_transition():
    sm = StateMachineService(db=None)  # type: ignore
    assert sm.can_transition(TaskStatus.DRAFT.value, TaskStatus.READY.value)
    assert not sm.can_transition(TaskStatus.SUCCESS.value, TaskStatus.RUNNING.value)


def test_terminal_states_have_no_outgoing():
    sm = StateMachineService(db=None)  # type: ignore
    assert not sm.can_transition(TaskStatus.SUCCESS.value, TaskStatus.FAILED.value)
    assert not sm.can_transition(TaskStatus.CANCELLED.value, TaskStatus.RUNNING.value)
