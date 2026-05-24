from shared.check_result import CheckResult


class ScoreResult:
    def __init__(self, check_result: CheckResult, linter_score: float = 0.0, linter_weight: float = 0.0):
        self.check_result = check_result
        self.linter_score = float(linter_score)
        self.linter_weight = float(linter_weight)

    def total_score(self) -> float:
        base_score = self.check_result.score()
        if self.linter_weight == 0.0:
            return base_score
        return (base_score + self.linter_weight * self.linter_score) / (1.0 + self.linter_weight)

    def __repr__(self):
        if self.linter_weight == 0.0:
            return self.check_result.__repr__()

        ret = self.check_result.__repr__()
        ret += f'Check score: {(self.check_result.score() * 100.):.2f} %\n'
        ret += f'Linter weight: {self.linter_weight:.4f}\n'
        ret += f'Linter score: {(self.linter_score * 100.):.2f} %\n'
        ret += f'Overall score: {(self.total_score() * 100.):.2f} %\n'
        return ret
