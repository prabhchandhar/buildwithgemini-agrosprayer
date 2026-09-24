import json
import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from google.protobuf.json_format import MessageToDict
from a2a.client import ClientConfig, create_client
from a2a.types import (
    Message,
    Part,
    Role,
    SendMessageRequest,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ.get("AGENT_ENGINE_RESOURCE_NAME")
if not RESOURCE:
    meta_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                RESOURCE = meta.get("remote_agent_runtime_id")
        except Exception:
            pass

if not RESOURCE:
    raise RuntimeError("AGENT_ENGINE_RESOURCE_NAME environment variable or deployment_metadata.json must be present.")

AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)

_A2UI_MIME = "application/json+a2ui"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


_contexts: dict[str, str] = {}


def _extract_parts(parts: list) -> list[dict]:
    out: list[dict] = []
    for p in parts:
        try:
            p_dict = MessageToDict(p)
        except Exception:
            p_dict = {}

        # 1. Check direct text field
        if "text" in p_dict and p_dict["text"]:
            out.append({"kind": "text", "text": p_dict["text"]})
            continue

        # 2. Check data field (dict or struct)
        data = p_dict.get("data")
        if isinstance(data, dict):
            # Check function response result (e.g. image URL returned by tool)
            res = data.get("response", {}).get("result")
            if res and isinstance(res, str):
                out.append({"kind": "text", "text": res})
                continue

            # Check A2UI payload
            meta = data.get("metadata", {})
            if meta.get("mimeType") == _A2UI_MIME or meta.get("mime_type") == _A2UI_MIME:
                a2ui_data = data.get("data") or data
                out.append({"kind": "a2ui", "data": a2ui_data})
                continue

        # 3. Fallbacks for direct attributes if object is not protobuf
        text = getattr(p, "text", None)
        if text:
            out.append({"kind": "text", "text": text})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        config = ClientConfig(httpx_client=client)
        a2a_client = await create_client(
            A2A_BASE,
            client_config=config,
            relative_card_path="/.well-known/agent-card.json",
        )

        role_user = getattr(Role, "ROLE_USER", getattr(Role, "user", "ROLE_USER"))
        msg = Message(
            message_id=str(uuid.uuid4()),
            context_id=_contexts.get(user_id) or "",
            role=role_user,
            parts=[Part(text=message)],
        )
        send_req = SendMessageRequest(message=msg)

        last_task = None
        got_artifact_update = False

        async for event in a2a_client.send_message(send_req):
            payload_type = event.WhichOneof("payload") if hasattr(event, "WhichOneof") else None

            if payload_type == "task":
                last_task = event.task
                if event.task.context_id:
                    _contexts[user_id] = event.task.context_id

            elif payload_type == "status_update":
                if event.status_update.context_id:
                    _contexts[user_id] = event.status_update.context_id

            elif payload_type == "artifact_update":
                got_artifact_update = True
                if event.artifact_update.context_id:
                    _contexts[user_id] = event.artifact_update.context_id
                parts.extend(_extract_parts(event.artifact_update.artifact.parts))

            elif payload_type == "message":
                got_artifact_update = True
                if event.message.context_id:
                    _contexts[user_id] = event.message.context_id
                parts.extend(_extract_parts(event.message.parts))

        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
