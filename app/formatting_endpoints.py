"""Shared request handling for the two authenticated formatting endpoints."""
import subprocess
from time import perf_counter
from typing import Literal

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from shared.formatting import FormatterUnavailable, format_source
from shared.question_config import QuestionConfigDto, CppQuestionConfigDto


class FormatRequest(BaseModel):
    code: str = Field(max_length=131072)
    filename: Literal['main.py', 'main.c', 'main.cpp'] = 'main.py'
    questionConfigDto: QuestionConfigDto = Field(default_factory=QuestionConfigDto)


class CppFormatRequest(FormatRequest):
    filename: Literal['main.c', 'main.cpp'] | None = None
    questionConfigDto: CppQuestionConfigDto = Field(default_factory=CppQuestionConfigDto)


async def format_request(request: Request, cpp: bool = False):
    from app.code_execution_endpoints import _authorize_or_response
    denied = _authorize_or_response(request, '/cpp/format' if cpp else '/format')
    if denied is not None:
        return denied
    try:
        data = (CppFormatRequest if cpp else FormatRequest).model_validate(await request.json())
        config = data.questionConfigDto.formatterConfig
        if len(config) > 16384:
            raise ValueError('Formatter configuration must be at most 16384 characters')
        language = 'python'
        if cpp:
            language = data.questionConfigDto.language
            if data.filename:
                language = 'c' if data.filename == 'main.c' else 'cpp'
        started = perf_counter()
        code = await run_in_threadpool(format_source, data.code, language, config)
        return JSONResponse({'code': code, 'output': 'Code formatted.',
                             'timings': {'format_seconds': perf_counter() - started}})
    except (ValidationError, ValueError, TypeError) as error:
        return JSONResponse({'output': str(error)}, status_code=400)
    except FormatterUnavailable as error:
        return JSONResponse({'output': str(error)}, status_code=503)
    except subprocess.TimeoutExpired:
        return JSONResponse({'output': 'Formatting timed out.'}, status_code=504)
