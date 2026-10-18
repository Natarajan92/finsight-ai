"""Shared scalar constraints, without runtime adapters or benchmark labels."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Value must contain non-whitespace text")
    return value  # Never normalize financial source text at a contract boundary.


NonBlank = Annotated[str, AfterValidator(_nonblank)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PageIndex = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]
NonnegativeFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
