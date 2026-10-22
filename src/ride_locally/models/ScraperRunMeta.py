from typing import Annotated, Literal

from pydantic import Field

from ride_locally.models.Carrier import Carrier
from ride_locally.models.MetaField import MetaEntry, MetaField


class AmbiguousCarrier(MetaEntry, frozen=True):
    code: Literal["ambiguous_carrier"] = "ambiguous_carrier"
    carrier_candidates: list[tuple[Carrier, float]]


ScraperRunMetaEntry = Annotated[AmbiguousCarrier, Field(discriminator="code")]


class ScraperRunMeta(MetaField[ScraperRunMetaEntry]):
    pass
