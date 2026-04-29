from pydantic import BaseModel


class EvalConfigDto(BaseModel):
    runAtTest: bool = True
    unitTestAtTest: bool = False
    lintAtTest: bool = True


class QuestionConfigDto(BaseModel):
    indication: str = ""
    validation: str = ""
    files: dict[str, str] = {}
    evalConfig: EvalConfigDto = EvalConfigDto()

