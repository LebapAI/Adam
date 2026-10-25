"""Dependency-light owner-authenticated web interface for Railway."""
import asyncio
import base64
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from audit_log import AuditLogError, write_audit_event
from authorization import confirmation_granted
from main import AdamAgent
from owner_auth import verify_owner_password
from safety import screen_remote_text

adam = AdamAgent()
PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Adam AI</title><h1>Adam AI</h1><p>Never send passwords or API keys.</p><p id=s>Loading status…</p><textarea id=q maxlength=12000 placeholder='Your question' style='width:100%;height:140px'></textarea><p>Type SEND to approve sending this question to the external model.</p><input id=c placeholder=SEND><button id=b>Send</button><p id=m></p><pre id=a style='white-space:pre-wrap'></pre><script>const s=document.getElementById('s'),m=document.getElementById('m'),a=document.getElementById('a');fetch('/api/status').then(r=>r.json()).then(x=>s.textContent='LLM '+(x.llm_configured?'configured':'not configured')+'; MCP tools disabled');document.getElementById('b').onclick=async()=>{a.textContent='';if(document.getElementById('c').value!=='SEND'){m.textContent='Type SEND exactly.';return}m.textContent='Sending…';try{let r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:document.getElementById('q').value,confirmation:document.getElementById('c').value})}),d=await r.json();if(!r.ok)throw Error(d.detail||'Request failed');a.textContent=d.answer;m.textContent='Response received.'}catch(e){m.textContent=e.message}}</script>"""

class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, data):
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        expected = os.getenv("ADAM_OWNER_PASSWORD", "")
        try:
            scheme, token = self.headers.get("Authorization", "").split(" ", 1)
            user, password = base64.b64decode(token, validate=True).decode().split(":", 1)
        except (ValueError, UnicodeError):
            user, password, scheme = "", "", ""
        valid = (scheme.lower() == "basic" and hmac.compare_digest(user.encode(), b"owner")
                 and verify_owner_password(expected, password) and len(expected) >= 16)
        if not valid:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Adam AI"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
        return valid

    def do_GET(self):
        if self.path == "/healthz":
            return self.send_json(200, {"status": "ok"})
        if not self.authorized():
            return
        if self.path == "/":
            raw = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/status":
            return self.send_json(200, {"agent": "Adam", "llm_configured": adam.llm_configured,
                                        "mcp_tool_execution_enabled": False})
        else:
            return self.send_json(404, {"detail": "Not found"})

    def do_POST(self):
        if not self.authorized():
            return
        if self.path != "/api/ask":
            return self.send_json(404, {"detail": "Not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 15000:
                return self.send_json(413, {"detail": "Request too large"})
            body = json.loads(self.rfile.read(length))
            prompt = body.get("prompt", "").strip()
            confirmation = body.get("confirmation", "")
        except (ValueError, TypeError, AttributeError):
            return self.send_json(400, {"detail": "Invalid request"})
        if not prompt or len(prompt) > 12000 or screen_remote_text(prompt) != prompt:
            return self.send_json(400, {"detail": "Empty question, too long, or text resembles a secret"})
        if not confirmation_granted("send_to_llm", confirmation):
            return self.send_json(400, {"detail": "Type SEND exactly to approve"})
        if not adam.llm_configured:
            return self.send_json(503, {"detail": "Set LLM_API_KEY and LLM_MODEL in Railway Variables"})
        try:
            write_audit_event("external_llm_request", "approved", "owner_approved")
        except (AuditLogError, OSError, ValueError):
            return self.send_json(503, {"detail": "Audit log unavailable; request was not sent"})
        try:
            answer = asyncio.run(adam.ask_model(prompt))
        except (httpx.HTTPError, OSError, ValueError, RuntimeError, TimeoutError):
            try:
                write_audit_event("external_llm_request", "failure", "request_error")
            except (AuditLogError, OSError, ValueError):
                pass
            return self.send_json(502, {"detail": "Model request failed; check API settings and network"})
        try:
            write_audit_event("external_llm_request", "success", "request_completed")
        except (AuditLogError, OSError, ValueError):
            pass
        return self.send_json(200, {"answer": answer})

if __name__ == "__main__":
    # Keep the service alive even if credentials need configuration; protected routes
    # reject authentication until a valid owner password (16+ characters) is set.
    port = int(os.getenv("PORT", "8000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
