"""Native stdin formatting, independent of Jobe and code execution."""
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib

CPP_DEFAULT_STYLE = '''BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
SortIncludes: Never
AllowShortFunctionsOnASingleLine: None
'''


class FormatterUnavailable(RuntimeError):
    pass


def format_source(code: str, language: str, config: str = '') -> str:
    if language not in {'python', 'c', 'cpp'}:
        raise ValueError('Unsupported formatting language')
    if language == 'python':
        if config.strip():
            settings = tomllib.loads(config)
            allowed = {'line-length', 'indent-width', 'target-version', 'preview', 'format'}
            if set(settings) - allowed:
                raise ValueError('Ruff configuration supports line-length, indent-width, target-version, preview, and [format]')
        command = [os.getenv('RUFF_BIN', 'ruff'), 'format', '--isolated', '--no-cache',
                   '--stdin-filename', 'main.py']
        if config.strip():
            command += ['--config', config]
        return _run_formatter(command + ['-'], code)
    style = config.strip() or CPP_DEFAULT_STYLE
    if 'inheritparentconfig' in style.lower():
        raise ValueError('clang-format configuration must be self-contained')
    with tempfile.TemporaryDirectory(prefix='letto-format-') as directory:
        path = Path(directory) / '.clang-format'
        path.write_text(style, encoding='utf-8')
        return _run_formatter([
            os.getenv('CLANG_FORMAT_BIN', 'clang-format'), '--style=file:' + str(path),
            '--assume-filename=main.' + ('c' if language == 'c' else 'cpp'),
            '--fail-on-incomplete-format',
        ], code)


def _run_formatter(command: list[str], code: str) -> str:
    try:
        result = subprocess.run(command, input=code, capture_output=True, text=True,
                                encoding='utf-8', timeout=5, check=False)
    except FileNotFoundError as error:
        raise FormatterUnavailable('Formatter is not installed in the plugin service') from error
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'Source could not be formatted')
    return result.stdout
