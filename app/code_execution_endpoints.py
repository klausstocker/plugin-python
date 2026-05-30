import hmac
import os
import re
import secrets
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse

from shared.check import checkCode
from shared.jobe_wrapper import JobeWrapper
from shared.lint import lintCode
from shared.score import scoreCode
from shared.question_examples import QuestionConfigDtoExamples

SERVICEPATH = os.getenv("SERVICEPATH", "/pluginpython").rstrip("/")
FILE_STORAGE_ROOT = Path(os.getenv("PLUGIN_FILE_STORAGE_DIR", "/opt/letto/images/pluginpython/files"))
REQUIRE_EXEC_TOKEN = os.getenv("PLUGIN_EXEC_REQUIRE_TOKEN", "true").lower() == "true"
EXEC_TOKEN = secrets.token_urlsafe(32)

router = APIRouter()


def get_exec_token() -> str:
    return EXEC_TOKEN


def _extract_exec_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return (
        request.headers.get("x-plugin-token")
        or request.query_params.get("token")
        or ""
    ).strip()


def _ensure_authorized(request: Request) -> None:
    if not REQUIRE_EXEC_TOKEN:
        return
    presented_token = _extract_exec_token(request)
    if not EXEC_TOKEN or not hmac.compare_digest(presented_token, EXEC_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid plugin execution token",
        )


def _safe_display_name(value: str) -> str:
    name = Path((value or "").strip()).name
    name = re.sub(r"[\\/]+", "_", name)
    name = re.sub(r"[\x00-\x1f\x7f]+", "", name).strip()
    return name or "uploaded-file"


def _safe_stored_name(value: str) -> str:
    stored_name = Path((value or "").strip()).name
    if not re.fullmatch(r"[A-Fa-f0-9]{32}(?:_[A-Za-z0-9._-]+)?", stored_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stored file name")
    return stored_name


def _stored_file_path(stored_name: str) -> Path:
    return FILE_STORAGE_ROOT / _safe_stored_name(stored_name)


def _file_specs_from_config(files_config: Any) -> dict[str, bytes]:
    file_data: dict[str, bytes] = {}
    if not isinstance(files_config, dict):
        return file_data

    for display_name, file_info in files_config.items():
        safe_name = _safe_display_name(str(display_name))
        if isinstance(file_info, str):
            file_data[safe_name] = file_info.encode("utf-8")
            continue
        if not isinstance(file_info, dict):
            continue

        stored_name = file_info.get("storedName") or file_info.get("stored_name")
        if not stored_name:
            content = file_info.get("content")
            if isinstance(content, str):
                file_data[safe_name] = content.encode("utf-8")
            continue

        file_path = _stored_file_path(str(stored_name))
        if file_path.is_file():
            file_data[safe_name] = file_path.read_bytes()
    return file_data


def _debug_file_config_entries(source: str, files_config: Any) -> None:
    if not isinstance(files_config, dict):
        print(f"[pluginpython files] {source}: no file mapping", flush=True)
        return

    entries = []
    for display_name, file_info in files_config.items():
        if isinstance(file_info, dict):
            stored_name = file_info.get("storedName") or file_info.get("stored_name") or "<inline>"
            size = file_info.get("size")
        elif isinstance(file_info, str):
            stored_name = "<inline>"
            size = len(file_info.encode("utf-8"))
        else:
            stored_name = "<unsupported>"
            size = "<unknown>"
        entries.append(f"filename={display_name!r}, storedName={stored_name!r}, size={size}")

    print(f"[pluginpython files] {source}: gathered {len(entries)} file(s): {entries}", flush=True)


def _file_specs_from_body(body: dict) -> dict[str, bytes]:
    question_config = body.get('questionConfigDto') or {}
    question_files = question_config.get('files') if isinstance(question_config, dict) else None

    _debug_file_config_entries('questionConfigDto.files', question_files)
    file_data = _file_specs_from_config(question_files or {}) if isinstance(question_config, dict) else {}

    gathered = [f"filename={name!r}, size={len(content)}" for name, content in file_data.items()]
    print(f"[pluginpython files] _file_specs_from_body final filenames: {gathered}", flush=True)
    return file_data


def _jobe_files_from_body(body: dict):
    return JobeWrapper.createFiles(_file_specs_from_body(body))


def _debug_run_file_metadata(body: dict) -> None:
    question_config = body.get('questionConfigDto') or {}
    files_config = question_config.get('files') if isinstance(question_config, dict) else None
    if not isinstance(files_config, dict):
        return

    for display_name, file_info in files_config.items():
        if isinstance(file_info, dict):
            stored_name = file_info.get("storedName") or file_info.get("stored_name") or "<inline>"
            size = file_info.get("size")
        elif isinstance(file_info, str):
            stored_name = "<inline>"
            size = len(file_info.encode("utf-8"))
        else:
            stored_name = "<unsupported>"
            size = "<unknown>"
        print(
            f"[pluginpython /run] questionConfigDto.files: filename={display_name!r}, "
            f"storedName={stored_name!r}, size={size}",
            flush=True,
        )


@router.post(f"{SERVICEPATH}/files/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    _ensure_authorized(request)
    FILE_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    display_name = _safe_display_name(file.filename or "uploaded-file")
    extension = Path(display_name).suffix
    safe_suffix = re.sub(r"[^A-Za-z0-9._-]+", "_", display_name)[:80]
    stored_name = f"{uuid.uuid4().hex}_{safe_suffix or 'file'}"
    if extension and not stored_name.endswith(extension):
        stored_name += extension
    file_path = FILE_STORAGE_ROOT / stored_name
    content = await file.read()
    file_path.write_bytes(content)
    return JSONResponse({
        "displayName": display_name,
        "storedName": stored_name,
        "size": len(content),
    })


@router.post(f"{SERVICEPATH}/files/delete")
async def delete_file(request: Request):
    _ensure_authorized(request)
    body = await request.json()
    stored_name = body.get("storedName") if isinstance(body, dict) else None
    if not stored_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing storedName")
    file_path = _stored_file_path(str(stored_name))
    if file_path.exists():
        file_path.unlink()
    return JSONResponse({"deleted": True})


@router.get(f"{SERVICEPATH}/files/download/{{stored_name}}")
async def download_file(request: Request, stored_name: str, name: str = ""):
    _ensure_authorized(request)
    file_path = _stored_file_path(stored_name)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(file_path, filename=_safe_display_name(name or stored_name))


@router.post(f"{SERVICEPATH}/run")
async def run_code(request: Request):
    _ensure_authorized(request)
    body = await request.json()
    code = body['code']
    try:
        _debug_run_file_metadata(body)
        files = _jobe_files_from_body(body)
        for file_id, filename, content in files:
            print(
                f"[pluginpython /run] uploading to Jobe: filename={filename!r}, "
                f"jobeFileId={file_id!r}, size={len(content)}",
                flush=True,
            )
        jobe = JobeWrapper('jobe:80')
        result = jobe.run_test('python3', code, 'test.py', files)
        return JSONResponse({'output': result.__repr__()})
    except Exception as e:
        return JSONResponse({'output': f'Error running code: {e}'})


@router.post(f"{SERVICEPATH}/lint")
async def lint_code(request: Request):
    _ensure_authorized(request)
    body = await request.json()
    code = body['code']
    question_config = body.get('questionConfigDto') or {}
    linter_config = question_config.get('linterConfig', '') if isinstance(question_config, dict) else ''
    score, messages = lintCode(code, linter_config)
    messagesText = f'Your code has been rated: {score:.2f}/10.0'
    for m in messages:
        messagesText += f'\nline: {m.line}: {m.msg_id}: {m.msg}, {m.category}'
    return JSONResponse({'output': messagesText})


@router.post(f"{SERVICEPATH}/check")
async def check_code(request: Request):
    _ensure_authorized(request)
    body = await request.json()
    code = body['code']
    testcode = body['testcode']
    try:
        result = checkCode('jobe:80', code, testcode, files=_jobe_files_from_body(body))
        return JSONResponse({'output': result.__repr__()})
    except Exception as e:
        return JSONResponse({'output': f'Error checking code: {e}'})


@router.post(f"{SERVICEPATH}/scorePlugin")
async def score_plugin(request: Request):
    _ensure_authorized(request)
    body = await request.json()
    code = body['code']
    testcode = body['testcode']

    question_config = body.get('questionConfigDto') or {}
    linter_config = question_config.get('linterConfig', '') if isinstance(question_config, dict) else ''
    linter_weight_raw = question_config.get('linterWeight', 0.0) if isinstance(question_config, dict) else 0.0
    try:
        linter_weight = float(linter_weight_raw)
    except (TypeError, ValueError):
        linter_weight = 0.0

    try:
        score, result = scoreCode('jobe:80', code, testcode, linter_config, linter_weight, files=_jobe_files_from_body(body))
        return JSONResponse({'output': result.__repr__(), 'score': score})
    except Exception as e:
        return JSONResponse({'output': f'Error scoring code: {e}', 'score': 0.0})


@router.post(f"{SERVICEPATH}/example")
async def get_example(request: Request):
    _ensure_authorized(request)
    body = await request.json()
    index = body.get("index", 0)

    examples = QuestionConfigDtoExamples()
    count = len(examples)

    if count == 0:
        return JSONResponse({'count': 0, 'output': None})

    if not isinstance(index, int) or index < 0 or index >= count:
        return JSONResponse({'count': count, 'output': None, 'error': 'Invalid example index'})

    return JSONResponse({'count': count, 'output': examples[index].model_dump()})
