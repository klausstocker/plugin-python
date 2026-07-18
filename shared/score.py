from shared.check import checkCode
from shared.lint import lintCode
from shared.score_result import ScoreResult


def scoreCode(server: str, code: str, testcode: str, linter_config: str = "", linter_weight: float = 0.0, files=None, language='python', cputime=None):
    check_result = checkCode(server, code, testcode, files=files, language=language, cputime=cputime)
    linter_score = 0.0

    if linter_weight != 0.0:
        linter_score, _ = lintCode(code, linter_config)

    score_result = ScoreResult(check_result, linter_score / 10., linter_weight)
    return score_result.total_score(), score_result
