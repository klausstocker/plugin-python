from urllib.error import HTTPError
import json
import http.client
import base64
import uuid

RESOURCE_BASE = '/jobe/index.php/restapi'

# Language ids are the ids exposed by Jobe's REST API.  Keep this mapping here
# rather than scattering ids and file extensions throughout the endpoints that
# call Jobe.
LANGUAGE_PYTHON = 'python3'
LANGUAGE_C = 'c'
LANGUAGE_CPP = 'cpp'
SOURCE_FILENAMES = {
    LANGUAGE_PYTHON: 'main.py',
    LANGUAGE_C: 'main.c',
    LANGUAGE_CPP: 'main.cpp',
}
CATCH2_TEST_FILENAME = 'catch2_tests.cpp'
CATCH2_SOLUTION_FILENAMES = {
    LANGUAGE_C: 'answer.c',
    LANGUAGE_CPP: 'answer.cpp',
}

PYTHON_CODE = """
MESSAGE = 'Hello Jobe!'

def sillyFunc(message):
    '''Pointless function that prints the given message'''
    print("Message is", message)

sillyFunc(MESSAGE)
"""

# =============================================================

class RunResult():
    outcomes = {
        0:  'Successful run',
        11: 'Compile error',
        12: 'Runtime error',
        13: 'Time limit exceeded',
        15: 'Successful run',
        17: 'Memory limit exceeded',
        19: 'Illegal system call',
        20: 'Internal error, please report',
        21: 'Server overload',
        99: 'file error'}

    def outcome(self):
        if self._outcome in RunResult.outcomes:
            return self._outcome, RunResult.outcomes[self._outcome]
        return 2, 'unknown error while running code'
    
    def success(self) -> bool:
        return self._outcome in [0, 15]
    
    def __init__(self, ro: dict):
        if not isinstance(ro, dict) or 'outcome' not in ro:
            print("Bad result object", ro)
            self._outcome = 1
            return
        self._outcome = ro['outcome']
        self.cmpinfo = ro['cmpinfo'] if 'cmpinfo' in ro else None
        self.stdout =  ro['stdout'] if 'stdout' in ro else None
        self.stderr =  ro['stderr'] if 'stderr' in ro else None

    def __repr__(self):
        out = self.outcome()
        ret = ''
        if self.success():
            ret += (self.stdout+'\n') if self.stdout else ''
        else:
            ret = f'Error while running code: {out[1]}\n'
            ret += f'Compiler output: {self.cmpinfo}\n' if self.cmpinfo else ''
        ret += f'stderr: {self.stderr}\n' if self.stderr else ''
        return ret


def trim(s):
    '''Return the string s limited to 10k chars'''
    MAX_LEN = 10000
    if len(s) > MAX_LEN:
        return s[:MAX_LEN] + '... [etc]'
    else:
        return s


class JobeWrapper():
    def __init__(self, server):
        self.server = server

    @staticmethod
    def createFiles(files: dict):
        """Create Jobe file specs while preserving the in-sandbox filename.

        Jobe receives files as (opaque_file_id, sandbox_filename, bytes).  The
        file id is used only for the REST upload endpoint and should not contain
        the user filename.  The second tuple element is the original/display name
        that Jobe exposes to the Python code.
        """
        commonId = uuid.uuid4().hex
        filesWithId = []
        for index, (name, content) in enumerate(files.items()):
            fileId = f'{commonId}{index:04x}'
            filesWithId.append((fileId, name, content))
        return filesWithId

    def http_request(self, method, resource, data=None, headers=None):
        '''Send a request to Jobe with given HTTP method to given resource on
        the currently configured Jobe server and given data and headers.
        Return the connection object. '''
        connect = http.client.HTTPConnection(self.server)
        connect.request(method, resource, data, headers or {})
        return connect

    def run_test(self, language, code, sourceFilename, files=None):
        '''Execute the given code in the given language.
        Return the result object.'''
        runspec = {
            'language_id': language,
            'sourcefilename': sourceFilename,
            'sourcecode': code,
            'file_list': []
        }
        
        for fileId, name, content in files or []:
            if self.put_file(fileId, content):
                return RunResult({'outcome': 99, 'stderr': f'could not upload file {name}'})
            exists = self.check_file(fileId)
            if not exists:
                return RunResult({'outcome': 99, 'stderr': f'could not verify file {name}'})
            runspec['file_list'].append((fileId, name))

        resource = f'{RESOURCE_BASE}/runs'
        data = json.dumps({ 'run_spec' : runspec }, separators=(',', ':'))
        headers = {"Content-type": "application/json; charset=utf-8",
                "Accept": "application/json"}
        result = self.do_http('POST', resource, headers, data)
        return RunResult(result)

    def run_c(self, code, files=None, source_filename=None):
        """Compile and run a standard C program with Jobe."""
        return self.run_test(
            LANGUAGE_C, code, source_filename or SOURCE_FILENAMES[LANGUAGE_C], files)

    def run_cpp(self, code, files=None, source_filename=None):
        """Compile and run a C++ program with Jobe."""
        return self.run_test(
            LANGUAGE_CPP, code, source_filename or SOURCE_FILENAMES[LANGUAGE_CPP], files)

    @staticmethod
    def build_catch2_test_program(solution_language, solution_filename, test_code):
        """Return the C++ test runner used to execute Catch2 tests.

        Catch2 is a C++ framework, so both C and C++ submissions are compiled
        by Jobe as C++.  A C submission is included in an ``extern \"C\"`` block
        to preserve C linkage for functions declared by the submission.
        """
        if solution_language not in CATCH2_SOLUTION_FILENAMES:
            raise ValueError(
                f'Catch2 supports only {LANGUAGE_C!r} and {LANGUAGE_CPP!r}, '
                f'not {solution_language!r}')

        include_solution = f'#include "{solution_filename}"'
        if solution_language == LANGUAGE_C:
            include_solution = f'extern "C" {{\n{include_solution}\n}}'

        return (
            '#define CATCH_CONFIG_MAIN\n'
            '#include <catch2/catch.hpp>\n\n'
            f'{include_solution}\n\n'
            f'{test_code.rstrip()}\n'
        )

    def run_catch2_tests(self, solution_language, solution_code, test_code, files=None):
        """Run Catch2 tests against a C or C++ submission.

        The student submission is uploaded as ``answer.c`` or ``answer.cpp``.
        The generated C++ source includes it together with the teacher's Catch2
        test cases, allowing Jobe to compile one self-contained test executable.
        """
        if solution_language not in CATCH2_SOLUTION_FILENAMES:
            raise ValueError(
                f'Catch2 supports only {LANGUAGE_C!r} and {LANGUAGE_CPP!r}, '
                f'not {solution_language!r}')

        solution_filename = CATCH2_SOLUTION_FILENAMES[solution_language]
        solution_file = (uuid.uuid4().hex, solution_filename, solution_code.encode('utf-8'))
        auxiliary_files = [
            file_spec for file_spec in (files or [])
            if file_spec[1] != solution_filename
        ]
        program = self.build_catch2_test_program(
            solution_language, solution_filename, test_code)
        return self.run_cpp(program, [solution_file, *auxiliary_files], CATCH2_TEST_FILENAME)


    def do_http(self, method, resource, headers=None, data=None):
        """Send the given HTTP request to Jobe, return json-decoded result as
        a dictionary (or the empty dictionary if a 204 response is given).
        """
        result = {}
        response = None
        content = None

        try:
            connect = self.http_request(method, resource, data, headers)
            response = connect.getresponse()
            if response.status not in [200, 204]:
                print(f"do_http({method}, {resource}) returned status of {response.status}")
                print(f"content = '{response.read().decode('utf8')}'")
            elif response.status == 200:
                content = response.read().decode('utf8')
                if content:
                    result = json.loads(content)
            connect.close()

        except (HTTPError, ValueError) as e:
            print("\n***************** HTTP ERROR ******************\n")
            if response:
                print(' Response:', response.status, response.reason, content)
            else:
                print(e)
        return result

    def languages(self):
        resource = f'{RESOURCE_BASE}/languages'
        lang_versions = self.do_http('GET', resource)
        ret = {lang: version for lang, version in lang_versions}
        return ret
    
    def put_file(self, file_id: str, contents: bytes):
        ret = None
        contentsb64 = base64.b64encode(contents).decode()
        data = json.dumps({ 'file_contents' : contentsb64 })
        resource = f'{RESOURCE_BASE}/files/{file_id}'
        headers = {"Content-type": "application/text",
                "Accept": "text/plain"}
        connect = self.http_request('PUT', resource, data, headers)
        response = connect.getresponse()
        if response.status != 204:
            ret = f"{response.status} {response.reason}"
            print(f"Response to putting {file_id}: {ret}")
        connect.close()
        return ret

    def check_file(self, file_id):
        '''Checks if the given fileid exists on the server.
        Returns status: 204 denotes file exists, 404 denotes file not found.
        '''

        resource = f'{RESOURCE_BASE}/files/{file_id}'
        headers = {"Accept": "text/plain"}
        try:
            connect = self.http_request('HEAD', resource, '', headers)
            response = connect.getresponse()

            if response.status != 204:
                content =  response.read(4096)
                print(f"{response.status} {response.reason} {content}")

            connect.close()
            return response.status == 204
        except HTTPError:
            pass
        return False

        

def main():
    '''Demo or get languages, a run of Python3 then C++ then Java'''
    jobe = JobeWrapper('localhost:4000')
    print("Supported languages:")
    for lang, version in jobe.languages().items():
        print("    {}: {}".format(lang, version))
    print("Running python...")
    result_obj = jobe.run_test('python3', PYTHON_CODE, 'test.py')
    print(result_obj)

if __name__ == '__main__':
    main()
