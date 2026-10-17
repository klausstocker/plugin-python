"""SQLite exercises run through Jobe's Python sandbox."""
import os
from time import perf_counter

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

from app import code_execution_endpoints as common
from app.dataset_helper import dataset_file_from_payload
from shared.check_sql import check_sql, sql_program
from shared.jobe_wrapper import JobeWrapper
from shared.question_config import SqlQuestionConfigDto
from shared.sql_examples import EXAMPLE_NAMES, sql_example

SQL_SERVICEPATH = os.getenv('SQL_SERVICEPATH', '/pluginsql').rstrip('/')
router = APIRouter(prefix=SQL_SERVICEPATH)


class SqlRequest(BaseModel):
    code: str
    testcode: str = ''
    questionConfigDto: SqlQuestionConfigDto = Field(default_factory=SqlQuestionConfigDto)


@router.post('/run')
@router.post('/check')
@router.post('/scorePlugin')
async def execute(request: Request):
    operation = request.url.path.rsplit('/', 1)[-1]
    denied = common._authorize_or_response(request, '/sql/' + operation)
    if denied is not None:
        return denied
    started_at = perf_counter()
    try:
        body = await request.json()
        data = SqlRequest.model_validate(body)
        config = data.questionConfigDto
        files = JobeWrapper.createFiles(dataset_file_from_payload(config.model_dump()))
        server = os.getenv('JOBE_SERVER', 'jobe:80')
        if operation == 'run':
            source = sql_program(data.code, config.preparation)
            result = JobeWrapper(server).run_test('python3', source, 'answer.py', files=files,
                                                 cputime=config.cpuTime)
            return JSONResponse({'output': repr(result), 'success': result.success(), 'timings': result.timings})
        tests = data.testcode or config.validation
        if not tests.strip():
            return JSONResponse({'output': 'Python Checker unit tests are required.', 'score': 0.0}, status_code=400)
        result = check_sql(server, data.code, tests, config.preparation,
                           files=files, cputime=config.cpuTime)
        return JSONResponse({'output': repr(result), 'score': result.score(), 'status': result.status(),
                             'elapsedSeconds': perf_counter() - started_at})
    except (ValidationError, ValueError, TypeError) as error:
        return JSONResponse({'output': f'Invalid SQL request: {error}', 'score': 0.0}, status_code=400)
    except Exception as error:
        common.logger.exception('SQL execution failed')
        return JSONResponse({'output': f'Error running SQL: {error}', 'score': 0.0,
                             'elapsedSeconds': perf_counter() - started_at}, status_code=502)


@router.post('/example')
async def example(request: Request):
    denied = common._authorize_or_response(request, '/sql/example')
    if denied is not None:
        return denied
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError('Request must be a JSON object')
        entry = sql_example(body.get('index', 0))
        return JSONResponse({'count': len(EXAMPLE_NAMES), 'names': list(EXAMPLE_NAMES),
                             'output': entry.model_dump()})
    except (ValueError, TypeError) as error:
        return JSONResponse({'count': 0, 'output': None, 'error': str(error)}, status_code=400)


@router.get('/help')
async def help_page():
    return FileResponse(os.path.join(os.getenv('RESOURCE_DIR', '/app/resources'), 'help/SQL.html'), media_type='text/html')


router.add_api_route('/exectoken', common.execution_token, methods=['GET'])
router.add_api_route('/buildhash', common.get_buildhash, methods=['GET'])
