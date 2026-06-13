"""独立 LLM Verifier — 与执行 Agent 分离的验证逻辑。"""

import json
import logging
import re

import httpx

from app.config import get_settings
from app.models.entities import Feedback, Task, TaskRun
from app.services.verifier import VERDICT_FAILED, VERDICT_NEEDS_CONTINUE, VERDICT_PASSED, VerificationOutcome

logger = logging.getLogger(__name__)

VERIFIER_SYSTEM_PROMPT = """你是 Task Platform 的独立验证 Agent，只负责判断任务是否完成。
你不能替代执行 Agent 的工作，只根据目标、完成标准和 Agent 回传结果做裁决。

输出仅 JSON（无 markdown）:
{
  "verdict": "passed" | "failed" | "needs_continue",
  "reason": "中文简要说明",
  "confidence": 0.0-1.0
}

裁决原则:
- passed: 明确满足完成标准或目标已达成
- needs_continue: 有进展但未达标，应继续迭代
- failed: 明确失败、不可恢复或违反失败判据
"""


def _mock_verify(task: Task, feedback: Feedback, agent_status: str) -> VerificationOutcome:
    payload = feedback.result_payload or {}
    status = agent_status.lower()

    if status == "failed":
        return VerificationOutcome(
            verdict=VERDICT_FAILED,
            reason="[Mock Verifier] Agent 报告失败",
            signals={"mock": True, "confidence": 0.9},
            verified_by="llm_agent_mock",
        )

    criteria = task.success_criteria or {}
    rules = criteria.get("rules") or []
    if rules:
        for rule in rules:
            if rule.get("type") == "field_equals":
                path = rule.get("path", "")
                expected = rule.get("value")
                parts = path.split(".")
                val = payload
                for p in parts:
                    val = val.get(p) if isinstance(val, dict) else None
                if val != expected:
                    return VerificationOutcome(
                        verdict=VERDICT_NEEDS_CONTINUE,
                        reason=f"[Mock Verifier] 字段 {path} 未满足",
                        signals={"mock": True, "confidence": 0.75},
                        verified_by="llm_agent_mock",
                    )

    if status == "success":
        return VerificationOutcome(
            verdict=VERDICT_PASSED,
            reason="[Mock Verifier] 结果符合目标",
            signals={"mock": True, "confidence": 0.85},
            verified_by="llm_agent_mock",
        )

    return VerificationOutcome(
        verdict=VERDICT_NEEDS_CONTINUE,
        reason="[Mock Verifier] 需要继续执行",
        signals={"mock": True, "confidence": 0.7},
        verified_by="llm_agent_mock",
    )


async def _llm_verify(task: Task, feedback: Feedback, run: TaskRun, agent_status: str) -> VerificationOutcome:
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set, llm verifier fallback to mock")
        return _mock_verify(task, feedback, agent_status)

    user_content = json.dumps(
        {
            "objective": task.objective,
            "success_criteria": task.success_criteria,
            "failure_criteria": task.failure_criteria,
            "agent_status": agent_status,
            "iteration": run.iteration_count,
            "result_payload": feedback.result_payload,
            "logs_summary": (feedback.logs or [])[-5:],
        },
        ensure_ascii=False,
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "messages": [
                        {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        data = json.loads(cleaned)
        verdict = data.get("verdict", VERDICT_NEEDS_CONTINUE)
        if verdict not in {VERDICT_PASSED, VERDICT_FAILED, VERDICT_NEEDS_CONTINUE}:
            verdict = VERDICT_NEEDS_CONTINUE

        logger.info("llm verifier run=%s verdict=%s", run.id, verdict)
        return VerificationOutcome(
            verdict=verdict,
            reason=data.get("reason", "LLM 验证完成"),
            signals={"confidence": data.get("confidence"), "llm": True},
            verified_by="llm_agent",
        )
    except Exception as exc:
        logger.exception("llm verifier failed run=%s: %s", run.id, exc)
        return VerificationOutcome(
            verdict=VERDICT_NEEDS_CONTINUE,
            reason=f"LLM 验证异常，保守继续: {exc}",
            signals={"llm_error": str(exc)},
            verified_by="llm_agent_fallback",
        )


async def verify_with_llm(
    task: Task,
    feedback: Feedback,
    run: TaskRun,
    *,
    agent_status: str,
) -> VerificationOutcome:
    settings = get_settings()
    if settings.ai_mock_mode:
        return _mock_verify(task, feedback, agent_status)
    return await _llm_verify(task, feedback, run, agent_status)
