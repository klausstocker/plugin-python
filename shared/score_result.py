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
        return (base_score + self.linter_weight * (self.linter_score / 10.0)) / (1.0 + self.linter_weight)

    def __repr__(self, grade: float = 1.0):
        if self.linter_weight == 0.0:
            return self.check_result.__repr__(grade)

        base_score = self.check_result.score()
        total_score = self.total_score()
        ret = self.check_result.__repr__(grade)
        ret += f'Check score: {base_score * grade}\n'
        ret += f'Linter weight: {self.linter_weight}\n'
        ret += f'Linter score: {self.linter_score}/10.0\n'
        ret += f'Overall score: {total_score * grade}\n'
        return ret
