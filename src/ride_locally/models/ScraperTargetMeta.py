from typing import Annotated, Literal

from pydantic import Field

from ride_locally.models.MetaField import MetaEntry, MetaField


class TargetDeactivated(MetaEntry, frozen=True):
    code: Literal["deactivated"] = "deactivated"
    reason: str


ScraperTargetMetaEntry = Annotated[
    TargetDeactivated, Field(discriminator="code")]


class ScraperTargetMeta(MetaField[ScraperTargetMetaEntry]):
    pass
