"""Parse additional question compiler flags before passing them to Jobe."""
import re
import shlex


def parse_compiler_flags(value: str = '') -> list[str]:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('Compiler flags must be a string of at most 2048 characters')
    flags = shlex.split(value)
    if len(flags) > 32:
        raise ValueError('At most 32 additional compiler flags are supported')
    for flag in flags:
        # Jobe's C/Cpp tasks join arguments into a shell command. Accept only
        # common compiler options without shell syntax or external tool loading.
        allowed = (
            re.fullmatch(r'-std=(?:c|gnu)(?:89|90|99|11|17|18|23|2x)', flag)
            or re.fullmatch(r'-std=(?:c|gnu)\+\+(?:98|03|11|14|17|20|23|26|2a|2b|2c)', flag)
            or re.fullmatch(r'-O(?:[0-3]|s|g|fast)', flag)
            or re.fullmatch(r'-g[0-3]?', flag)
            or re.fullmatch(r'-W[A-Za-z0-9_=+.-]+', flag)
            or re.fullmatch(r'-[DU][A-Za-z_][A-Za-z0-9_]*(?:=[A-Za-z0-9_+.,/-]+)?', flag)
            or flag in {'-pedantic', '-pedantic-errors', '-pthread', '-pipe',
                        '-fno-exceptions', '-fno-rtti', '-fwrapv', '-fno-strict-aliasing',
                        '-fsigned-char', '-funsigned-char'}
            or (re.fullmatch(r'-I[A-Za-z0-9_./-]+', flag)
                and not flag[2:].startswith('/') and '..' not in flag[2:].split('/'))
        )
        if not allowed:
            raise ValueError(f'Unsupported compiler flag: {flag}')
    return flags
