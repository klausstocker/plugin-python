from shared.check import checkCode
from shared.lint import lintCode


def scoreCode(server: str, code: str, testcode: str, linter_config: str = "", linter_weight: float = 0.0):
    result = checkCode(server, code, testcode)
    base_score = result.score()
    total_score = base_score

    if linter_weight != 0.0:
        linter_score, _ = lintCode(code, linter_config)
        total_score = (base_score + linter_weight * (linter_score / 10.0)) / (1.0 + linter_weight)

    return total_score, result
