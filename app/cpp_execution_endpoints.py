"""C/C++ execution endpoints, separate from the existing Python endpoints."""
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

from app import code_execution_endpoints as common
from shared.check_catch2 import check_catch2
from shared.cpp_examples import cpp_examples
from shared.jobe_wrapper import JobeWrapper
from shared.question_config import CppQuestionConfigDto
from shared.compiler_flags import parse_compiler_flags
from app.formatting_endpoints import format_request

CPP_SERVICEPATH = os.getenv('CPP_SERVICEPATH', '/plugincpp').rstrip('/')
JOBE_SERVER = os.getenv('JOBE_SERVER', 'jobe:80')
router = APIRouter(prefix=CPP_SERVICEPATH)


class CppRequest(BaseModel):
    code: str
    testcode: str = ''
    questionConfigDto: CppQuestionConfigDto = Field(default_factory=CppQuestionConfigDto)


@router.post('/format')
async def format_code(request: Request):
    return await format_request(request, cpp=True)


@router.post('/run')
@router.post('/compile')
@router.post('/check')
@router.post('/scorePlugin')
async def execute(request: Request):
    operation = request.url.path.rsplit('/', 1)[-1]
    denied = common._authorize_or_response(request, '/cpp/' + operation)
    if denied is not None:
        return denied
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError('Request must be a JSON object')
        data = CppRequest.model_validate(body)
        config = data.questionConfigDto
        compiler_flags = parse_compiler_flags(config.compilerFlags)
        files = common._jobe_files_from_body(body, include_dataset=False)
        if operation in ('run', 'compile'):
            standard = '-std=c17' if config.language == 'c' else '-std=c++17'
            filename = 'answer.c' if config.language == 'c' else 'answer.cpp'
            files = [spec for spec in files if spec[1] != filename]
            result = JobeWrapper(JOBE_SERVER).run_test(
                ('compile' + config.language) if operation == 'compile' else config.language,
                data.code, filename, files=files,
                cputime=common._cputime_from_question_config(config.model_dump()),
                parameters={'compileargs': [standard, '-Wall', '-Werror', *compiler_flags]})
            if operation == 'compile':
                compiler_output = result.cmpinfo or ''
                summary = 'Compilation successful.' if result.success() else f'Compilation failed: {result.outcome()[1]}.'
                output = summary + '\nCompiler output:\n' + (compiler_output or '(no compiler diagnostics)')
                if result.stderr:
                    output += '\nstderr:\n' + result.stderr
                return JSONResponse({'output': output, 'compilerOutput': compiler_output,
                                     'success': result.success(), 'timings': result.timings})
            return JSONResponse({'output': repr(result), 'timings': result.timings})
        if not data.testcode.strip():
            return JSONResponse({'output': 'Catch2 test code is required.', 'score': 0.0}, status_code=400)
        result = check_catch2(JOBE_SERVER, data.code, data.testcode, language=config.language,
                              files=files, cputime=common._cputime_from_question_config(config.model_dump()),
                              compiler_flags=config.compilerFlags)
        return JSONResponse({'output': repr(result), 'score': result.score(), 'status': result.status()})
    except (ValidationError, ValueError, TypeError) as error:
        return JSONResponse({'output': f'Invalid C/C++ request: {error}', 'score': 0.0}, status_code=400)
    except Exception as error:
        common.logger.exception('C/C++ execution failed')
        return JSONResponse({'output': f'Error running C/C++ code: {error}', 'score': 0.0}, status_code=502)


@router.post('/example')
async def example(request: Request):
    denied = common._authorize_or_response(request, '/cpp/example')
    if denied is not None:
        return denied
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError('Request must be a JSON object')
        config = CppQuestionConfigDto.model_validate(body.get('questionConfigDto') or {})
        entries = cpp_examples(config.language)
        index = body.get('index', 0)
        if type(index) is not int or not 0 <= index < len(entries):
            raise ValueError('Invalid example index')
        return JSONResponse({'count': len(entries), 'names': [entry['title'] for entry in entries], 'output': entries[index]})
    except (ValueError, TypeError) as error:
        return JSONResponse({'count': 0, 'output': None, 'error': str(error)}, status_code=400)


@router.get('/help')
async def help_page():
    return FileResponse(os.path.join(os.getenv('RESOURCE_DIR', '/app/resources'), 'help/Cpp.html'), media_type='text/html')


# Share upload storage and authentication while exposing distinct Cpp URLs.
router.add_api_route('/exectoken', common.execution_token, methods=['GET'])
router.add_api_route('/buildhash', common.get_buildhash, methods=['GET'])
router.add_api_route('/files/upload', common.upload_file, methods=['POST'])
router.add_api_route('/files/delete', common.delete_file, methods=['POST'])
router.add_api_route('/files/download/{stored_name}', common.download_file, methods=['GET'])
