import logging
from dataclasses import dataclass, field
from typing import Any

from app.models.entities import Feedback, Task, TaskRun

logger = logging.getLogger(__name__)

VERDICT_PASSED = "passed"
VERDICT_FAILED = "failed"
VERDICT_NEEDS_CONTINUE = "needs_continue"


@dataclass
class VerificationOutcome:
    verdict: str
    reason: str
    signals: dict = field(default_factory=dict)
    verified_by: str = "rule_based"


def _get_path(data: dict, path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _has_rules(criteria: dict | None) -> bool:
    if not criteria:
        return False
    rules = criteria.get("rules") or []
    return bool(rules)


def _evaluate_rule(rule: dict, payload: dict, agent_status: str) -> tuple[bool, str]:
    rule_type = rule.get("type")
    if rule_type == "field_exists":
        path = rule.get("path", "")
        ok = _get_path(payload, path) is not None
        return ok, f"field_exists({path})={ok}"
    if rule_type == "field_equals":
        path = rule.get("path", "")
        expected = rule.get("value")
        actual = _get_path(payload, path)
        ok = actual == expected
        return ok, f"field_equals({path}) expected={expected!r} actual={actual!r}"
    if rule_type == "field_not_exists":
        path = rule.get("path", "")
        ok = _get_path(payload, path) is None
        return ok, f"field_not_exists({path})={ok}"
    if rule_type == "status_in":
        values = rule.get("values") or []
        ok = agent_status in values
        return ok, f"status_in({values}) status={agent_status!r}"
    return False, f"unknown_rule_type({rule_type})"


def _evaluate_criteria(criteria: dict, payload: dict, agent_status: str) -> tuple[bool, list[str]]:
    rules = criteria.get("rules") or []
    match_mode = criteria.get("match", "all")
    results: list[tuple[bool, str]] = [_evaluate_rule(r, payload, agent_status) for r in rules]
    signals = [s for _, s in results]
    if match_mode == "any":
        return any(ok for ok, _ in results), signals
    return all(ok for ok, _ in results), signals


class VerifierService:
    def verify(
        self,
        task: Task,
        feedback: Feedback,
        run: TaskRun,
        *,
        agent_status: str,
    ) -> VerificationOutcome:
        payload = feedback.result_payload or {}
        status = agent_status.lower()

        if not _has_rules(task.success_criteria) and not _has_rules(task.failure_criteria):
            if status == "success":
                return VerificationOutcome(
                    verdict=VERDICT_PASSED,
                    reason="无完成标准，Agent success 视为通过",
                    signals={"compat_mode": True},
                )
            if status == "requires_action":
                return VerificationOutcome(
                    verdict=VERDICT_NEEDS_CONTINUE,
                    reason="Agent 请求继续执行",
                    signals={"compat_mode": True},
                )
            return VerificationOutcome(
                verdict=VERDICT_FAILED,
                reason=f"Agent 状态为 {status}，且无完成标准",
                signals={"compat_mode": True},
            )

        if _has_rules(task.failure_criteria):
            failed, fail_signals = _evaluate_criteria(task.failure_criteria, payload, status)
            if failed:
                return VerificationOutcome(
                    verdict=VERDICT_FAILED,
                    reason="命中失败判据",
                    signals={"failure_rules": fail_signals},
                )

        if status == "requires_action":
            return VerificationOutcome(
                verdict=VERDICT_NEEDS_CONTINUE,
                reason="Agent 显式请求继续",
                signals={"agent_status": status},
            )

        if _has_rules(task.success_criteria):
            passed, pass_signals = _evaluate_criteria(task.success_criteria, payload, status)
            if passed:
                return VerificationOutcome(
                    verdict=VERDICT_PASSED,
                    reason="满足完成标准",
                    signals={"success_rules": pass_signals},
                )
            return VerificationOutcome(
                verdict=VERDICT_NEEDS_CONTINUE,
                reason="尚未满足完成标准",
                signals={"success_rules": pass_signals, "unmet": True},
            )

        if status == "success":
            return VerificationOutcome(
                verdict=VERDICT_PASSED,
                reason="Agent success 且无 success_criteria",
            )

        return VerificationOutcome(
            verdict=VERDICT_FAILED,
            reason=f"未满足完成条件，Agent 状态={status}",
            signals={"agent_status": status},
        )
