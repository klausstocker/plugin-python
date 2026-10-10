"""Catch2 checks using sandboxed C17/C++17 compilation in Jobe."""

import xml.etree.ElementTree as ET

from shared.check_result import CheckResult
from shared.jobe_wrapper import JobeWrapper
from shared.compiler_flags import parse_compiler_flags

REPORT_MARKER = '__catch2_report__\n'


def parse_catch2_report(stdout):
    try:
        if not stdout or REPORT_MARKER not in stdout:
            raise ValueError('Missing Catch2 report')
        root = ET.fromstring(stdout.rsplit(REPORT_MARKER, 1)[1])
        totals = root.find('OverallResultsCases')
        if root.tag != 'Catch2TestRun' or totals is None:
            raise ValueError('Missing Catch2 test case totals')
        successful = int(totals.attrib['successes'])
        failed = int(totals.attrib['failures'])
        if successful < 0 or failed < 0 or successful + failed == 0:
            raise ValueError('Catch2 did not run any test cases')
        failures = []
        for case in root.iter('TestCase'):
            result = case.find('OverallResult')
            if result is not None and result.get('success') == 'false':
                failures.append(case.get('name', 'Failed Catch2 test case'))
        return CheckResult({
            'count': successful + failed,
            'failure_count': failed,
            'failures': failures,
        })
    except (ET.ParseError, ValueError, KeyError, TypeError) as error:
        return CheckResult({'count': 0, 'errors': [f'Could not read Catch2 result: {error}']})


def check_catch2(server, code, test_code, language='cpp', files=None, cputime=None, compiler_flags=''):
    if language not in {'c', 'cpp'}:
        raise ValueError('Catch2 answer language must be c or cpp')
    answer_name = 'answer.c' if language == 'c' else 'answer.cpp'
    reserved = {'answer.c', 'answer.cpp', 'answer.o', 'test.cpp', 'test.cpp.exe',
                'catch2-tests.o', 'catch2-results.xml'}
    auxiliary_files = [spec for spec in files or [] if spec[1] not in reserved]
    answer_files = JobeWrapper.createFiles({answer_name: code.encode('utf-8')})
    result = JobeWrapper(server).run_test(
        'catch2' + language, test_code, 'test.cpp',
        files=answer_files + auxiliary_files, cputime=cputime,
        parameters={'compileargs': parse_compiler_flags(compiler_flags)})
    if not result.success():
        return CheckResult({'count': 0, 'errors': [
            f'Error running Jobe Catch2 tests. {repr(result).strip()}',
        ]})
    return parse_catch2_report(result.stdout)
