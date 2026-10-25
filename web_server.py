import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
@app.get("/healthz")
def healthz():
    return {"status": "ok"}
@app.get("/")
def home():
    return HTMLResponse("<!doctype html><title>Adam AI</title><h1>Adam AI</h1><p>Service online.</p>")
