import asyncio
import hashlib
import hmac
import json
import logging
import os
import random
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("agent-simulator")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CALLBACK_DELAY = float(os.getenv("SIMULATOR_CALLBACK_DELAY_SECONDS", "2"))
SUCCESS_RATE = float(os.getenv("SIMULATOR_SUCCESS_RATE", "0.9"))
TIMEOUT_RATE = float(os.getenv("SIMULATOR_TIMEOUT_RATE", "0.0"))
PULL_ADAPTER_NAME = os.getenv("PULL_ADAPTER_NAME", "Hermes")
PULL_INTERVAL = float(os.getenv("PULL_INTERVAL_SECONDS", "3"))
PULL_API_KEY = os.getenv("PULL_API_KEY", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret-change-me")
WEBHOOK_HMAC_ENABLED = os.getenv("WEBHOOK_HMAC_ENABLED", "false").lower() == "true"
SIGNATURE_HEADER = "X-Webhook-Signature"
FORCE_STATUS = os.getenv("SIMULATOR_FORCE_STATUS", "").strip().lower()
FIXED_PAYLOAD_RAW = os.getenv("SIMULATOR_FIXED_PAYLOAD", "").strip()


def sign_callback_body(body: bytes) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if WEBHOOK_HMAC_ENABLED:
        sig = hmac.new(WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
        headers[SIGNATURE_HEADER] = sig
    return headers


class TaskPayload(BaseModel):
    task_id: str
    run_id: str
    objective: str
    context: dict = {}
    constraints: dict = {}
    callback_url: str


async def send_callback(payload: TaskPayload):
    await asyncio.sleep(CALLBACK_DELAY)
    if random.random() < TIMEOUT_RATE:
        logger.warning("simulating timeout run_id=%s (no callback)", payload.run_id)
        return

    if FORCE_STATUS:
        status = FORCE_STATUS
    else:
        roll = random.random()
        if roll < SUCCESS_RATE:
            status = "success"
        elif roll < SUCCESS_RATE + 0.05:
            status = "requires_action"
        else:
            status = "failed"

    if FIXED_PAYLOAD_RAW:
        try:
            result_payload = json.loads(FIXED_PAYLOAD_RAW)
        except json.JSONDecodeError:
            logger.error("invalid SIMULATOR_FIXED_PAYLOAD, using default")
            result_payload = {"summary": f"Simulated result for: {payload.objective[:50]}"}
    else:
        result_payload = {"summary": f"Simulated result for: {payload.objective[:50]}", "tokens_used": 120}

    feedback = {
        "run_id": payload.run_id,
        "feedback_id": str(uuid.uuid4()),
        "status": status,
        "result_payload": result_payload,
        "logs": [{"level": "info", "message": f"Simulated {status} callback"}],
        "error_code": None if status != "failed" else "SIMULATED_FAILURE",
    }
    body = json.dumps(feedback, ensure_ascii=False).encode("utf-8")
    headers = sign_callback_body(body)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(payload.callback_url, content=body, headers=headers)
            resp.raise_for_status()
        logger.info("callback sent run_id=%s status=%s payload_keys=%s", payload.run_id, status, list(result_payload.keys()))
    except Exception as exc:
        logger.error("callback failed run_id=%s error=%s", payload.run_id, exc)


async def pull_loop():
    headers = {"X-API-Key": PULL_API_KEY} if PULL_API_KEY else {}
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{API_BASE_URL}/v1/agent/pull",
                    params={"adapter_name": PULL_ADAPTER_NAME},
                    headers=headers,
                )
                if resp.status_code == 200 and resp.text and resp.text != "null":
                    data = resp.json()
                    if data:
                        payload = TaskPayload(
                            task_id=data["task_id"],
                            run_id=data["run_id"],
                            objective=data["objective"],
                            context=data.get("context", {}),
                            constraints=data.get("constraints", {}),
                            callback_url=data["callback_url"],
                        )
                        logger.info("pull task received run_id=%s", payload.run_id)
                        asyncio.create_task(send_callback(payload))
        except Exception as exc:
            logger.debug("pull poll error: %s", exc)
        await asyncio.sleep(PULL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Agent Simulator starting API_BASE_URL=%s", API_BASE_URL)
    task = asyncio.create_task(pull_loop())
    yield
    task.cancel()


app = FastAPI(title="Agent Simulator", lifespan=lifespan)


@app.post("/v1/tasks")
async def receive_push_task(payload: TaskPayload):
    logger.info("push task received run_id=%s objective=%s", payload.run_id, payload.objective[:50])
    asyncio.create_task(send_callback(payload))
    return {"accepted": True, "run_id": payload.run_id}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-simulator"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "simulator.main:app",
        host=os.getenv("SIMULATOR_HOST", "0.0.0.0"),
        port=int(os.getenv("SIMULATOR_PORT", "8100")),
        reload=False,
    )
