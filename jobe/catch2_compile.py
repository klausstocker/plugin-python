"""Compile inside Jobe's sandbox; emit phase timings on stdout, diagnostics on stderr."""
import json
import hashlib
from pathlib import Path
import resource
import shlex
import subprocess
import sys
import time

TEST_FLAGS = ['-std=c++17', '-Wall', '-Werror', '-DLETTO_UNIT_TEST=1', '-I/opt/catch2/include']


def test_cache_key(source, test_flags=None):
    """Ask the compiler for actual includes; also hash all auxiliary inputs."""
    test_flags = TEST_FLAGS if test_flags is None else test_flags
    dependency_run = subprocess.run(
        ['g++', *test_flags, '-MM', '-MT', 'cache', source],
        capture_output=True, text=True)
    if dependency_run.returncode:
        return None  # Let normal compilation report diagnostics.
    dependencies = shlex.split(dependency_run.stdout.replace('\\\n', ' ').split(':', 1)[1])
    workspace = Path.cwd().resolve()
    inputs = {Path(source)}
    # Include every auxiliary upload, even when currently excluded by #if or
    # __has_include. Answer contents matter only when tests include the answer.
    generated = {'answer.c', 'answer.cpp', 'answer.o', 'catch2-tests.o',
                 'prog.out', 'prog.err', 'prog.cmd', 'prog.in'}
    inputs.update(path for path in Path('.').iterdir() if path.is_file() and path.name not in generated)
    for name in dependencies:
        path = Path(name)
        resolved = path.resolve()
        if resolved.is_relative_to(workspace):
            inputs.add(path)
        elif not (resolved.is_relative_to('/opt/catch2') or resolved.is_relative_to('/usr')):
            return None  # Unknown external dependency: prefer recompilation.
    # Presence matters for __has_include even if a file is never #included.
    names = sorted(path.name for path in Path('.').iterdir()
                   if path.is_file() and (path.name not in generated or path.name in {'answer.c', 'answer.cpp'}))
    digest = hashlib.sha256(json.dumps([source, test_flags, names]).encode())
    for path in sorted(inputs, key=lambda item: str(item)):
        contents = path.read_bytes()
        if any(token in contents for token in (b'__TIME__', b'__DATE__', b'__TIMESTAMP__')):
            return None
        digest.update(json.dumps([str(path), len(contents)]).encode())
        digest.update(contents)
    return digest.hexdigest()


def main():
    language, source, executable, mode, *options = sys.argv[1:]
    extra_flags = []
    if 'flags' in options:
        index = options.index('flags')
        extra_flags = json.loads(options[index + 1])
        options = options[:index]
        if not isinstance(extra_flags, list) or not all(isinstance(flag, str) for flag in extra_flags):
            raise ValueError('Compiler flags must be a list of strings')
    # C standard overrides apply only to the answer; the harness remains C++.
    test_flags = TEST_FLAGS + [flag for flag in extra_flags
                              if language != 'c' or not flag.startswith('-std=')]
    compiler = 'gcc' if language == 'c' else 'g++'
    standard = '-std=c17' if language == 'c' else '-std=c++17'
    answer = 'answer.c' if language == 'c' else 'answer.cpp'
    commands = [
        ('answer_compile', [compiler, standard, '-Wall', '-Werror', '-DLETTO_UNIT_TEST=1',
                            *extra_flags,
                            '-c', answer, '-o', 'answer.o']),
    ] if mode == 'prepare' else [
        ('test_compile', ['g++', *test_flags, '-c', source, '-o', 'catch2-tests.o']),
        ('link', ['g++', 'catch2-tests.o', 'answer.o', '/opt/catch2/lib/letto-catch2-runner.o',
                  '/opt/catch2/lib/libCatch2.a', '-pthread', '-o', executable]),
    ]
    if mode == 'finish' and options == ['hit']:
        commands = commands[1:]
    timings = {}
    if mode == 'finish':
        timings['test_compile_wall_seconds'] = 0.0
        timings['test_compile_cpu_seconds'] = 0.0
    status = 0
    try:
        for phase, command in commands:
            cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
            started = time.perf_counter()
            completed = subprocess.run(command, stdout=sys.stderr, stderr=sys.stderr)
            timings[phase + '_wall_seconds'] = time.perf_counter() - started
            cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
            timings[phase + '_cpu_seconds'] = (
                cpu_after.ru_utime + cpu_after.ru_stime - cpu_before.ru_utime - cpu_before.ru_stime)
            status = completed.returncode
            if status:
                break
        if mode == 'prepare' and status == 0:
            started = time.perf_counter()
            try:
                timings['test_cache_key'] = test_cache_key(source, test_flags)
            except (OSError, ValueError, IndexError):
                timings['test_cache_key'] = None
            timings['test_cache_key_wall_seconds'] = time.perf_counter() - started
    finally:
        print(json.dumps(timings), flush=True)
    return status


if __name__ == '__main__':
    sys.exit(main())
