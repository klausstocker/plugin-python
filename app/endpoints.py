import os
import re
import shutil
import sys
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


def _ensure_shared_import_path() -> None:
    """Ensure the repository root (containing ./shared) is importable."""
    current_dir = Path(__file__).resolve().parent
    candidate_roots = [
        current_dir.parent,
        current_dir.parent.parent,
        Path.cwd(),
        Path.cwd().parent,
    ]
    for root in candidate_roots:
        shared_dir = root / "shared"
        if shared_dir.is_dir():
            root_str = str(root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
            break


_ensure_shared_import_path()

from shared.check import *
from shared.jobe_wrapper import *
from shared.lint import *
from shared.question_config import EvalConfigDto, QuestionConfigDto

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Only allow alphanumeric characters, underscores, and hyphens in names.
# This prevents any path traversal since no dots, slashes, or special chars are permitted.
SAFE_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$')

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
static_files = StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"))


def _get_session_dir(request: Request) -> Path:
    """Get or create a session-specific upload directory."""
    session_id = request.session.get('session_id')
    if not session_id or not SAFE_NAME_RE.match(session_id):
        session_id = uuid.uuid4().hex
        request.session['session_id'] = session_id
    session_dir = UPLOAD_DIR / session_id
    real_dir = os.path.realpath(str(session_dir))
    real_upload = os.path.realpath(str(UPLOAD_DIR))
    if real_dir == real_upload or not real_dir.startswith(real_upload + os.sep):
        session_id = uuid.uuid4().hex
        request.session['session_id'] = session_id
        session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _safe_path(session_dir: Path, filename: str):
    """Return a safe file path within session_dir, or None if invalid."""
    safe_name = os.path.basename(filename)
    if not safe_name or not SAFE_NAME_RE.match(safe_name):
        return None
    candidate = os.path.join(str(session_dir), safe_name)
    real_candidate = os.path.realpath(candidate)
    real_session = os.path.realpath(str(session_dir))
    if real_candidate == real_session or not real_candidate.startswith(real_session + os.sep):
        return None
    return Path(real_candidate)


@router.post('/run')
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


@router.post('/lint')
async def lint_code(request: Request):
    body = await request.json()
    code = body['code']
    score, messages = lintCode(code)
    messagesText = f'Your code has been rated: {score:.2f}/10.0'
    for m in messages:
        messagesText += f'\nline: {m.line}: {m.msg_id}: {m.msg}, {m.category}'
    return JSONResponse({'output': messagesText})


@router.post('/check')
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


@router.post('/upload')
async def upload(request: Request, file: UploadFile = File(None)):
    try:
        if file is None or file.filename is None or file.filename == '':
            msg = 'No file part in the form'
            return JSONResponse({'status': 1, 'msg': msg})

        raw_name = file.filename.split('.')[0] if '.' in file.filename else file.filename
        session_dir = _get_session_dir(request)
        filepath = _safe_path(session_dir, raw_name)
        if filepath is None:
            return JSONResponse({'status': 3, 'msg': 'invalid filename'})
        overwrite = filepath.exists()
        data = await file.read()
        filepath.write_bytes(data)
    except Exception:
        return JSONResponse({'status': 3, 'msg': 'exception uploading file'})
    if overwrite:
        return JSONResponse({'status': 1, 'msg': 'file exists, overwrite'})
    return JSONResponse({'status': 0, 'msg': 'success'})


@router.get('/download/{upload_id}')
async def download(request: Request, upload_id: str):
    session_dir = _get_session_dir(request)
    filepath = _safe_path(session_dir, upload_id)
    if filepath is not None and filepath.exists() and filepath.is_file():
        return StreamingResponse(
            BytesIO(filepath.read_bytes()),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filepath.name}"'}
        )
    return PlainTextResponse("File not found", status_code=404)


@router.get('/remove/{upload_id}')
async def remove(request: Request, upload_id: str):
    session_dir = _get_session_dir(request)
    filepath = _safe_path(session_dir, upload_id)
    if filepath is not None and filepath.exists() and filepath.is_file():
        filepath.unlink()
        return PlainTextResponse("Success", status_code=200)
    return PlainTextResponse("File not found", status_code=404)
