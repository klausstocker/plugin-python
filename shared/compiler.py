import re
import shlex

WARNING_PATTERN = re.compile(r"(^|[:\s])warning[:\s]", re.IGNORECASE | re.MULTILINE)


def parse_compiler_config(compiler_config: str = "") -> list[str]:
    """Return shell-style compiler arguments for Jobe's compileargs parameter."""
    if not compiler_config:
        return []
    return shlex.split(compiler_config)


def count_compiler_warnings(compiler_output: str | None) -> int:
    """Count compiler warning diagnostics in Jobe compile output."""
    if not compiler_output:
        return 0
    return sum(1 for line in compiler_output.splitlines() if WARNING_PATTERN.search(line))


def compiler_warning_score(warning_count: int) -> float:
    """Map 0 warnings to 1.0 and 10 or more warnings to 0.0."""
    return max(0.0, min(1.0, 1.0 - (max(0, warning_count) / 10.0)))
