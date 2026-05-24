from pydantic import BaseModel


class EvalConfigDto(BaseModel):
    runAtTest: bool = True
    lintAtTest: bool = True


class QuestionConfigDto(BaseModel):
    indication: str = ""
    validation: str = ""
    files: dict[str, str] = {}
    evalConfig: EvalConfigDto = EvalConfigDto()
    linterConfig: str = ""
    linterWeight: float = 0.0
