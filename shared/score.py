from shared.check import checkCode
from shared.compiler import (
    compiler_warning_score,
    count_compiler_warnings,
    parse_compiler_config,
)
from shared.jobe_wrapper import LANGUAGE_C, LANGUAGE_CPP, JobeWrapper
from shared.lint import lintCode
from shared.score_result import ScoreResult


class ScoreBehaviour:
    """Language-specific scoring extension combined with unit-test scoring."""

    score_label = "Linter"
    weight_label = "Linter"

    def __init__(self, server: str, language: str, config: str, weight: float, cputime=None):
        self.server = server
        self.language = language
        self.config = config
        self.weight = weight
        self.cputime = cputime

    def check(self, code: str, testcode: str, files=None):
        return checkCode(
            self.server,
            code,
            testcode,
            files=files,
            language=self.language,
            cputime=self.cputime,
        )

    def quality_score(self, code: str) -> float:
        return 0.0

    def result(self, check_result, code: str) -> ScoreResult:
        score = self.quality_score(code) if self.weight != 0.0 else 0.0
        return ScoreResult(
            check_result,
            score,
            self.weight,
            score_label=self.score_label,
            weight_label=self.weight_label,
        )


class PythonScoreBehaviour(ScoreBehaviour):
    score_label = "Linter"
    weight_label = "Linter"

    def quality_score(self, code: str) -> float:
        linter_score, _ = lintCode(code, self.config)
        return linter_score / 10.0


class CompiledScoreBehaviour(ScoreBehaviour):
    score_label = "Warning"
    weight_label = "Warning"

    def check(self, code: str, testcode: str, files=None):
        return checkCode(
            self.server,
            code,
            testcode,
            files=files,
            language=self.language,
            cputime=self.cputime,
            compiler_config=self.config,
        )

    def quality_score(self, code: str) -> float:
        compileargs = parse_compiler_config(self.config)
        jobe = JobeWrapper(self.server)
        result = jobe.compile_c_or_cpp(
            self.language,
            code,
            compileargs=compileargs,
            cputime=self.cputime,
        )
        compiler_output = "\n".join(
            output for output in (result.cmpinfo, result.stderr) if output
        )
        return compiler_warning_score(count_compiler_warnings(compiler_output))


def _score_behaviour(server: str, language: str, config: str, weight: float, cputime=None) -> ScoreBehaviour:
    if language in (LANGUAGE_C, LANGUAGE_CPP):
        return CompiledScoreBehaviour(server, language, config, weight, cputime=cputime)
    return PythonScoreBehaviour(server, language, config, weight, cputime=cputime)


def scoreCode(
    server: str,
    code: str,
    testcode: str,
    linter_config: str = "",
    linter_weight: float = 0.0,
    files=None,
    language='python',
    cputime=None,
):
    behaviour = _score_behaviour(server, language, linter_config, linter_weight, cputime=cputime)
    check_result = behaviour.check(code, testcode, files=files)
    score_result = behaviour.result(check_result, code)
    return score_result.total_score(), score_result
