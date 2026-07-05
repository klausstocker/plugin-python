import hmac
import logging
import os
import re
import secrets
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse

from app.dataset_helper import dataset_file_from_payload
from shared.check import checkCode
from shared.jobe_wrapper import JobeWrapper
from shared.lint import lintCode
from shared.score import scoreCode
from shared.question_examples import QuestionConfigDtoExamples

SERVICEPATH = os.getenv("SERVICEPATH", "/pluginpython").rstrip("/")
FILE_STORAGE_ROOT = Path(os.getenv("PLUGIN_FILE_STORAGE_DIR", "/opt/letto/images/pluginpython/files"))
REQUIRE_EXEC_TOKEN = os.getenv("PLUGIN_EXEC_REQUIRE_TOKEN", "true").lower() == "true"
EXEC_TOKEN = secrets.token_urlsafe(32)

TRACE_LOG_LEVEL = 5
logging.addLevelName(TRACE_LOG_LEVEL, "TRACE")

router = APIRouter()
logger = logging.getLogger("plugin-python.endpoints")
logger.info("Created plugin execution token: %s", EXEC_TOKEN)


def _dataset_variable_summary(value: Any) -> dict[str, Any]:
    if value is None:
        return {"present": False}
    if isinstance(value, dict):
        calc_result = value.get("calcErgebnisDto")
        if isinstance(calc_result, dict):
            return {
                "present": True,
                "calcErgebnisDto": {
                    "type": calc_result.get("type"),
                    "string": calc_result.get("string"),
                    "json": calc_result.get("json"),
                },
                "ze": value.get("ze"),
                "hasCalcParams": value.get("cp") is not None,
            }
        return {"present": True, "type": "dict", "keys": list(value.keys()), "repr": repr(value)[:200]}
    return {"present": True, "type": type(value).__name__, "repr": repr(value)[:200]}


def _dataset_field_summary(value: Any) -> dict[str, Any]:
    if value is None:
        return {"present": False}
    if isinstance(value, str):
        return {"present": True, "type": "str", "length": len(value), "preview": value[:200]}
    if isinstance(value, list):
        return {
            "present": True,
            "type": "list",
            "count": len(value),
            "variables": value,
        }
    if isinstance(value, dict):
        vars_map = value.get("vars") if isinstance(value.get("vars"), dict) else value
        return {
            "present": True,
            "type": "dict",
            "keys": list(value.keys()),
            "variableNames": list(vars_map.keys()) if isinstance(vars_map, dict) else [],
            "variables": {
                name: _dataset_variable_summary(var_value)
                for name, var_value in vars_map.items()
            } if isinstance(vars_map, dict) else {},
        }
    return {"present": True, "type": type(value).__name__, "repr": repr(value)[:200]}


def _dataset_transfer_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"type": type(value).__name__, "present": value is not None}

    summary: dict[str, Any] = {
        "topLevelKeys": list(value.keys()),
        "datasetFields": {},
    }
    for field in (
        "vars",
        "cvars",
        "varsMaxima",
        "mvars",
        "varsQuestion",
        "datasetVariables",
    ):
        if field in value:
            summary["datasetFields"][field] = _dataset_field_summary(value.get(field))

    for nested in ("q", "params", "pluginDto", "questionConfigDto"):
        nested_value = value.get(nested)
        if isinstance(nested_value, dict):
            summary[nested] = _dataset_transfer_summary(nested_value)

    return summary


def _debug_dataset_transfer(label: str, value: Any) -> None:
    logger.log(
        TRACE_LOG_LEVEL,
        "[pluginpython dataset] %s: %s",
        label,
        _dataset_transfer_summary(value),
    )

def get_exec_token() -> str:
    return EXEC_TOKEN


def get_commit_hash() -> str:
    return os.getenv("PLUGIN_BUILD_HASH", "").strip() or "unknown"


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
    token_matches = bool(EXEC_TOKEN) and hmac.compare_digest(presented_token, EXEC_TOKEN)
    logger.info(
        "Compared plugin execution token: presented=%r expected=%r matches=%s",
        presented_token,
        EXEC_TOKEN,
        token_matches,
    )
    if not token_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid plugin execution token",
        )


def _authorize_or_response(request: Request, endpoint: str) -> JSONResponse | None:
    try:
        _ensure_authorized(request)
    except HTTPException as exc:
        logger.warning("Authorization failed for %s: %s", endpoint, exc.detail)
        return JSONResponse(
            {"detail": exc.detail},
            status_code=exc.status_code,
            headers=exc.headers,
        )
    except Exception as exc:
        logger.exception("Unexpected authorization error for %s", endpoint)
        return JSONResponse(
            {"detail": f"Authorization failed: {exc}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return None


def _to_float(value: Any) -> float:
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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
        logger.debug("[pluginpython files] %s: no file mapping", source)
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

    logger.debug("[pluginpython files] %s: gathered %s file(s): %s", source, len(entries), entries)


def _file_specs_from_body(body: dict, include_dataset: bool = True) -> dict[str, bytes]:
    question_config = body.get('questionConfigDto') or {}
    question_files = question_config.get('files') if isinstance(question_config, dict) else None

    _debug_file_config_entries('questionConfigDto.files', question_files)
    file_data = (
        _file_specs_from_config(question_files or {})
        if isinstance(question_config, dict)
        else {}
    )
    if include_dataset and isinstance(question_config, dict):
        file_data.update(dataset_file_from_payload(question_config))

    gathered = [
        f"filename={name!r}, size={len(content)}"
        for name, content in file_data.items()
    ]
    logger.debug("[pluginpython files] _file_specs_from_body final filenames: %s", gathered)
    return file_data


def _jobe_files_from_body(body: dict, include_dataset: bool = True):
    return JobeWrapper.createFiles(
        _file_specs_from_body(body, include_dataset=include_dataset)
    )


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
        logger.debug(
            "[pluginpython /run] questionConfigDto.files: filename=%r, storedName=%r, size=%s",
            display_name,
            stored_name,
            size,
        )


@router.get(f"{SERVICEPATH}/buildhash")
async def get_buildhash(request: Request):
    commit_hash = get_commit_hash()
    logger.info("Build hash requested: %s", commit_hash)
    return JSONResponse({"commitHash": commit_hash})


@router.post(f"{SERVICEPATH}/files/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    auth_error = _authorize_or_response(request, "/files/upload")
    if auth_error is not None:
        return auth_error
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
    logger.info("Uploaded file: displayName=%r storedName=%r size=%s", display_name, stored_name, len(content))
    return JSONResponse({
        "displayName": display_name,
        "storedName": stored_name,
        "size": len(content),
    })


@router.post(f"{SERVICEPATH}/files/delete")
async def delete_file(request: Request):
    auth_error = _authorize_or_response(request, "/files/delete")
    if auth_error is not None:
        return auth_error
    body = await request.json()
    stored_name = body.get("storedName") if isinstance(body, dict) else None
    if not stored_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing storedName")
    file_path = _stored_file_path(str(stored_name))
    deleted = False
    if file_path.exists():
        file_path.unlink()
        deleted = True
    logger.info("Delete file requested: storedName=%r deleted=%s", stored_name, deleted)
    return JSONResponse({"deleted": True})


@router.get(f"{SERVICEPATH}/files/download/{{stored_name}}")
async def download_file(request: Request, stored_name: str, name: str = ""):
    auth_error = _authorize_or_response(request, "/files/download")
    if auth_error is not None:
        return auth_error
    file_path = _stored_file_path(stored_name)
    if not file_path.is_file():
        logger.warning("Download requested for missing file: storedName=%r", stored_name)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    logger.info("Download file requested: storedName=%r as name=%r", stored_name, name or stored_name)
    return FileResponse(file_path, filename=_safe_display_name(name or stored_name))


@router.post(f"{SERVICEPATH}/run")
async def run_code(request: Request):
    auth_error = _authorize_or_response(request, "/run")
    if auth_error is not None:
        return auth_error
    try:
        body = await request.json()
        _debug_dataset_transfer("/run request body", body)
        code = body['code']
    except Exception as e:
        logger.exception("Invalid /run request")
        return JSONResponse({'output': f'Invalid run request: {e}'}, status_code=status.HTTP_400_BAD_REQUEST)
    try:
        _debug_run_file_metadata(body)
        files = _jobe_files_from_body(body, include_dataset=False)
        for file_id, filename, content in files:
            logger.debug(
                "[pluginpython /run] uploading to Jobe: filename=%r, jobeFileId=%r, size=%s",
                filename,
                file_id,
                len(content),
            )
        jobe = JobeWrapper('jobe:80')
        result = jobe.run_test('python3', code, 'test.py', files)
        return JSONResponse({'output': result.__repr__()})
    except Exception as e:
        logger.exception("Error running code via Jobe")
        return JSONResponse({'output': f'Error running code: {e}'})


@router.post(f"{SERVICEPATH}/lint")
async def lint_code(request: Request):
    auth_error = _authorize_or_response(request, "/lint")
    if auth_error is not None:
        return auth_error
    try:
        body = await request.json()
        _debug_dataset_transfer("/lint request body", body)
        code = body['code']
    except Exception as e:
        logger.exception("Invalid /lint request")
        return JSONResponse({'output': f'Invalid lint request: {e}'}, status_code=status.HTTP_400_BAD_REQUEST)
    question_config = body.get('questionConfigDto') or {}
    linter_config = question_config.get('linterConfig', '') if isinstance(question_config, dict) else ''
    logger.info("Lint request received: codeLength=%s linterConfigLength=%s", len(code), len(linter_config))
    try:
        score, messages = lintCode(code, linter_config)
    except Exception as e:
        logger.exception("Error linting code")
        return JSONResponse({'output': f'Error linting code: {e}'})

    messagesText = f'Your code has been rated: {score:.2f}/10.0'
    for m in messages:
        messagesText += f'\nline: {m.line}: {m.msg_id}: {m.msg}, {m.category}'
    return JSONResponse({'output': messagesText})


@router.post(f"{SERVICEPATH}/check")
async def check_code(request: Request):
    auth_error = _authorize_or_response(request, "/check")
    if auth_error is not None:
        return auth_error
    try:
        body = await request.json()
        _debug_dataset_transfer("/check request body", body)
        code = body['code']
        testcode = body['testcode']
    except Exception as e:
        logger.exception("Invalid /check request")
        return JSONResponse({'output': f'Invalid check request: {e}'}, status_code=status.HTTP_400_BAD_REQUEST)
    try:
        result = checkCode('jobe:80', code, testcode, files=_jobe_files_from_body(body))
        return JSONResponse({'output': result.__repr__()})
    except Exception as e:
        logger.exception("Error checking code via Jobe")
        return JSONResponse({'output': f'Error checking code: {e}'})


@router.post(f"{SERVICEPATH}/scorePlugin")
async def score_plugin(request: Request):
    auth_error = _authorize_or_response(request, "/scorePlugin")
    if auth_error is not None:
        return auth_error
    try:
        body = await request.json()
        _debug_dataset_transfer("/scorePlugin request body", body)
        code = body['code']
        testcode = body['testcode']
    except Exception as e:
        logger.exception("Invalid /scorePlugin request")
        return JSONResponse({'output': f'Invalid score request: {e}', 'score': 0.0}, status_code=status.HTTP_400_BAD_REQUEST)

    question_config = body.get('questionConfigDto') or {}
    linter_config = question_config.get('linterConfig', '') if isinstance(question_config, dict) else ''
    linter_weight_raw = question_config.get('linterWeight', 0.0) if isinstance(question_config, dict) else 0.0
    linter_weight = _to_float(linter_weight_raw)

    try:
        score, result = scoreCode('jobe:80', code, testcode, linter_config, linter_weight, files=_jobe_files_from_body(body))
        return JSONResponse({'output': result.__repr__(), 'score': score})
    except Exception as e:
        logger.exception("Error scoring code via Jobe")
        return JSONResponse({'output': f'Error scoring code: {e}', 'score': 0.0})


@router.post(f"{SERVICEPATH}/example")
async def get_example(request: Request):
    auth_error = _authorize_or_response(request, "/example")
    if auth_error is not None:
        return auth_error
    try:
        body = await request.json()
    except Exception as e:
        logger.exception("Invalid /example request")
        return JSONResponse({'count': 0, 'output': None, 'error': f'Invalid example request: {e}'}, status_code=status.HTTP_400_BAD_REQUEST)
    index = body.get("index", 0)

    examples = QuestionConfigDtoExamples()
    count = len(examples)

    if count == 0:
        return JSONResponse({'count': 0, 'output': None})

    if not isinstance(index, int) or index < 0 or index >= count:
        return JSONResponse({'count': count, 'output': None, 'error': 'Invalid example index'})

    return JSONResponse({'count': count, 'output': examples[index].model_dump()})
