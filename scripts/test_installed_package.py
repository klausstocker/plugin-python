"""Run regression tests outside the checkout against a normally installed wheel.

Install requirements.txt and the wheel first, then run this script with that
environment's Python. Optional arguments select unittest modules or test cases.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


DEFAULT_TESTS = [
    'tests.test_shared_package',
    'tests.test_endpoints',
    'tests.test_dev_ui',
    'tests.test_dataset',
    'tests.test_cpp_dataset.TestCppDataset',
    'tests.test_cpp_plugin.TestCppPlugin',
    'tests.test_check_catch2.TestCatch2Reports',
    'tests.test_check_catch2.TestCatch2Submissions',
    'tests.test_question_examples',
    'tests.test_formatting.TestFormattingEndpoints',
    'tests.test_sql_plugin.TestSqlRuntime',
    'tests.test_sql_plugin.TestSqlPlugin',
    'tests.test_sql_formatting',
    'tests.test_score',
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='letto-installed-') as directory:
        work = Path(directory)
        # Deliberately omit shared/. Tests may add this staged root to sys.path.
        for name in ('app', 'tests', 'resources', 'examples', 'scripts'):
            shutil.copytree(root / name, work / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        environment = os.environ.copy()
        environment.pop('PYTHONPATH', None)
        environment.update(
            PLUGIN_REGISTER_ON_READY='false',
            PLUGIN_EXEC_TOKEN='installed-package-test-token',
            RESOURCE_DIR=str(work / 'resources'),
            PLUGIN_FILE_STORAGE_DIR=str(work / 'files'),
        )
        # -I prevents the checkout and user site-packages from masking the wheel.
        probe = '''
from pathlib import Path
import importlib.metadata
import shared
package = Path(shared.__file__).resolve().parent
assert package.parent.name in ('site-packages', 'dist-packages'), package
assert (package / '_data/examples/Python').is_dir(), package
from shared.cpp_dataset import cpp_dataset_files
assert cpp_dataset_files([])['helpers.h']
print('Testing installed', importlib.metadata.version('letto-pluginpython-shared'),
      'from', package, flush=True)
'''
        subprocess.run([sys.executable, '-I', '-c', probe], cwd=work,
                       env=environment, check=True)
        return subprocess.call(
            [sys.executable, '-m', 'unittest', *(sys.argv[1:] or DEFAULT_TESTS)],
            cwd=work, env=environment)


if __name__ == '__main__':
    raise SystemExit(main())
