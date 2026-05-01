import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SLUG_REGEX = re.compile(r"^[A-Za-z0-9_-]{4,32}$")


class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_slug: str | None = Field(default=None, description="Optional caller-provided slug")

    @field_validator("custom_slug")
    @classmethod
    def _validate_custom_slug(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not SLUG_REGEX.match(v):
            raise ValueError("custom_slug must match ^[A-Za-z0-9_-]{4,32}$")
        return v


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    url: str
    short_url: str
    click_count: int
    disabled: bool
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
