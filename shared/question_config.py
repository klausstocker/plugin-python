from typing import Any, Literal

from pydantic import BaseModel, Field


class EvalConfigDto(BaseModel):
    runAtTest: bool = True
    lintAtTest: bool = True


class QuestionConfigDto(BaseModel):
    indication: str = ""
    validation: str = ""
    files: dict[str, Any] = Field(default_factory=dict)
    evalConfig: EvalConfigDto = Field(default_factory=EvalConfigDto)
    linterConfig: str = ""
    formatterConfig: str = ""
    linterWeight: float = 0.0
    cpuTime: int = 5
    datasetVariables: list[dict[str, Any]] = Field(default_factory=list)


class CppQuestionConfigDto(QuestionConfigDto):
    language: Literal['c', 'cpp'] = 'cpp'
    evalConfig: EvalConfigDto = Field(default_factory=EvalConfigDto)
    linterWeight: float = 0.0
    compilerFlags: str = ""
