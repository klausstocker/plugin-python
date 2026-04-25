import os
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shared.check import checkCode
from shared.jobe_wrapper import JobeWrapper
from shared.lint import lintCode

SERVICEPATH = os.getenv("SERVICEPATH", "/pluginpython").rstrip("/")
UPLOAD_ROOT = Path(os.getenv("PLUGIN_STUB_UPLOAD_DIR", "/tmp/pluginpython_uploads"))

router = APIRouter()


def _safe_session_name(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip())
    return token or "default"


def _get_session_dir(request: Request) -> Path:
    session_id = (
        request.headers.get("x-session-id")
        or request.query_params.get("session_id")
        or (request.client.host if request.client else "default")
    )
    session_dir = UPLOAD_ROOT / _safe_session_name(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


@router.post(f"{SERVICEPATH}/run")
async def run_code(request: Request):
    body = await request.json()
    code = body['code']
    try:
        session_dir = _get_session_dir(request)
        file_data = {}
        for filepath in session_dir.iterdir():
            if filepath.is_file():
                file_data[filepath.name] = filepath.read_bytes()
        files = JobeWrapper.createFiles(file_data)
        jobe = JobeWrapper('jobe:80')
        result = jobe.run_test('python3', code, 'test.py', files)
        return JSONResponse({'output': result.__repr__()})
    except Exception:
        return JSONResponse({'output': 'Error running code'})

@router.post(f"{SERVICEPATH}/lint")
async def lint_code(request: Request):
    body = await request.json()
    code = body['code']
    score, messages = lintCode(code)
    messagesText = f'Your code has been rated: {score:.2f}/10.0'
    for m in messages:
        messagesText += f'\nline: {m.line}: {m.msg_id}: {m.msg}, {m.category}'
    return JSONResponse({'output': messagesText})


@router.post(f"{SERVICEPATH}/check")
async def check_code(request: Request):
    body = await request.json()
    code = body['code']
    score, messages = lintCode(code)
    messagesText = f'Your code has been rated: {score:.2f}/10.0'
    testcode = body['testcode']
    try:
        result = checkCode('jobe:80', code, testcode)
        return JSONResponse({'output': result.__repr__()})
    except Exception:
        return JSONResponse({'output': 'Error checking code'})
