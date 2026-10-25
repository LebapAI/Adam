import hmac
import os
from typing import Annotated
import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from audit_log import AuditLogError, write_audit_event
from authorization import confirmation_granted
from main import AdamAgent
from owner_auth import verify_owner_password
from safety import screen_remote_text

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
auth = HTTPBasic(auto_error=False)
adam = AdamAgent()

def owner(c: Annotated[HTTPBasicCredentials | None, Depends(auth)]):
    p = os.getenv("ADAM_OWNER_PASSWORD", "")
    ok = c is not None and hmac.compare_digest(c.username.encode(), b"owner") and verify_owner_password(p, c.password)
    if len(p) < 16 or not ok:
        raise HTTPException(401, "Owner authentication required", headers={"WWW-Authenticate": 'Basic realm="Adam AI"'})
    return c.username

class Ask(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    confirmation: str = Field(min_length=1, max_length=16)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/api/status")
async def get_status(_: Annotated[str, Depends(owner)]):
    s = await adam.status()
    return {"agent": s["agent"], "llm_configured": s["llm_configured"], "mcp_tool_execution_enabled": False}

@app.post("/api/ask")
async def ask(body: Ask, _: Annotated[str, Depends(owner)]):
    prompt = body.prompt.strip()
    if not prompt or screen_remote_text(prompt) != prompt:
        raise HTTPException(400, "Empty question or text resembles a secret.")
    if not confirmation_granted("send_to_llm", body.confirmation):
        raise HTTPException(400, "Type SEND exactly to approve.")
    if not adam.llm_configured:
        raise HTTPException(503, "Set LLM_API_KEY and LLM_MODEL in Railway Variables.")
    try:
        write_audit_event("external_llm_request", "approved", "owner_approved")
    except (AuditLogError, OSError, ValueError):
        raise HTTPException(503, "Audit log unavailable; request was not sent.") from None
    try:
        answer = await adam.ask_model(prompt)
    except (httpx.HTTPError, OSError, ValueError, RuntimeError, TimeoutError):
        try:
            write_audit_event("external_llm_request", "failure", "request_error")
        except (AuditLogError, OSError, ValueError):
            pass
        raise HTTPException(502, "Model request failed; check API settings and network.") from None
    try:
        write_audit_event("external_llm_request", "success", "request_completed")
    except (AuditLogError, OSError, ValueError):
        pass
    return {"answer": answer}

@app.get("/", response_class=HTMLResponse)
async def home(_: Annotated[str, Depends(owner)]):
    return HTMLResponse("<!doctype html><html><meta charset=utf-8><title>Adam AI</title><body><h1>Adam AI</h1><p>Owner authentication succeeded. API status: <a href='/api/status'>/api/status</a></p><p>Send POST /api/ask with JSON fields prompt and confirmation='SEND'. Never send secrets.</p></body></html>")

@app.middleware("http")
async def secure_headers(request, call_next):
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Cache-Control"] = "no-store"
    return r
