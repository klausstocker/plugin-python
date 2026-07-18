from typing import Any

from pydantic import BaseModel, Field


class EvalConfigDto(BaseModel):
    runAtTest: bool = True
    lintAtTest: bool = True


class QuestionConfigDto(BaseModel):
    programmingLanguage: str = "python"
    indication: str = ""
    validation: str = ""
    files: dict[str, Any] = Field(default_factory=dict)
    evalConfig: EvalConfigDto = Field(default_factory=EvalConfigDto)
    linterConfig: str = ""
    linterWeight: float = 0.0
    datasetVariables: list[dict[str, Any]] = Field(default_factory=list)
