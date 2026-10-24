from collections.abc import Awaitable, Callable, Iterable, Mapping
from logging import getLogger
from typing import Any, TypeVar

from sqlalchemy import ColumnElement, func, insert, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute

from ride_locally.db.schema import CarriersTable, ScrTargetTable
from ride_locally.models.Carrier import Carrier
from ride_locally.models.ScraperTarget import NewScrapeTarget, ScrapeTarget
from ride_locally.models.ScraperTargetMeta import TargetDeactivated
from ride_locally.worker.utils.shared import diff_model_against

log = getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)


async def update_scr_target(s: AsyncSession, target_id: int,
                            updated: NewScrapeTarget) -> bool:
    row = await s.get(ScrTargetTable, target_id, with_for_update=True,
                      populate_existing=True)
    if row is None:
        return False
    target = ScrapeTarget.model_validate(row)

    diff = diff_model_against(updated, target)
    if not diff:
        return False
    if "config" in diff:
        diff["config"] = updated.config.model_dump(mode="json")
    if "meta" in diff:
        target.meta.update(updated.meta)
        diff["meta"] = target.meta.model_dump(mode="json")

    await s.execute(
        update(ScrTargetTable).where(ScrTargetTable.id == target_id).values(
            **diff)
    )
    return True


async def disable_targets(s: AsyncSession, target_ids: Iterable[int], *,
                          reason: str) -> int:
    r = await s.execute(
        select(ScrTargetTable)
        .where(ScrTargetTable.id.in_(target_ids))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    targets = [ScrapeTarget.model_validate(row) for row in r.scalars().all()]
    for target in targets:
        target.meta.add(TargetDeactivated(reason=reason))
        await s.execute(
            update(ScrTargetTable)
            .where(ScrTargetTable.id == target.id)
            .values(
                is_active=False,
                meta=target.meta.model_dump(mode="json"),
            )
        )

    return len(targets)


DEFAULT_TRGM_SIMILARITY_THRESHOLD = 0.3


async def _get_similar_entities(
        s: AsyncSession,
        table: type[T],
        values: Mapping[InstrumentedAttribute[Any], str | None],
        similarity_threshold: float = DEFAULT_TRGM_SIMILARITY_THRESHOLD,
) -> list[tuple[T, float]]:
    """
    Rows of `table` where any column in `values` trigram-matches its value at
    or above `similarity_threshold` (0-1), paired with their best similarity
    and ordered most-similar first. None values are skipped. Empty list means
    "no candidates".

    Uses pg_trgm's `%` operator so the gin_trgm_ops indexes on the columns get
    used instead of a seq scan. The threshold is set with SET LOCAL, so it
    stays in effect for the rest of the caller's transaction but doesn't leak
    to other queries sharing the pooled connection.
    """
    matches = {column: value for column, value in values.items() if value}
    if not matches:
        return []

    # SET does not accept bind params, hence string interpolation
    thr = float(similarity_threshold)

    score = func.greatest(
        *(func.similarity(column, value) for column, value in matches.items())
    )
    q = (
        select(table, score)
        .where(
            or_(*(column.op("%")(value) for column, value in matches.items())))
        .order_by(score.desc())
    )
    await s.execute(text(f"SET LOCAL pg_trgm.similarity_threshold = {thr}"))
    r = await s.execute(q)
    return [(row, float(similarity)) for row, similarity in r.tuples().all()]


async def get_similar_targets_by(
        s: AsyncSession,
        *,
        name: str | None = None,
        url: str | None = None,
        similarity_threshold: float = DEFAULT_TRGM_SIMILARITY_THRESHOLD,
) -> list[tuple[ScrapeTarget, float]]:
    rows = await _get_similar_entities(
        s,
        ScrTargetTable,
        {ScrTargetTable.name: name, ScrTargetTable.url: url},
        similarity_threshold,
    )
    return [(ScrapeTarget.model_validate(row), score) for row, score in rows]


async def _get_entity_by(s: AsyncSession, table: type[T],
                         *where: ColumnElement[bool]) -> list[T]:
    if not where:
        return []
    r = await s.execute(select(table).where(*where))
    return list(r.scalars().all())


async def get_targets_by(
        s: AsyncSession, *, name: str | None = None, url: str | None = None
) -> list[ScrapeTarget]:
    filters = [(ScrTargetTable.name, name), (ScrTargetTable.url, url)]
    rows = await _get_entity_by(
        s, ScrTargetTable,
        *(column.like(value) for column, value in filters if value)
    )
    return [ScrapeTarget.model_validate(row) for row in rows]


async def add_new_targets(
        s: AsyncSession,
        new_targets: Iterable[NewScrapeTarget],
    *,
    warn_on_duplicate: bool = False,
    discard_duplicates: bool = False,
        duplicate_comp_func: Callable[[NewScrapeTarget], Awaitable[
            bool]] | None = None,
) -> tuple[list[NewScrapeTarget], list[NewScrapeTarget]]:
    """
    Adds new scraper targets to `scr_targets`.

    params:
        warn_on_duplicate: bool - emits warning level log at each target deemed duplicated by the default comparator function.
        discard_duplicates: bool - target will be omitted if deemed duplicated by default comparator function
        duplicate_comp_func: Callable[[NewScrapeTarget], Awaitable[bool]] - custom comparator function. Returns True if target should be inserted, False to skip target. Passing this function invalidates `warn_on_duplicate` and `discard_duplicates` parameters.
    returns:
        tuple of lists with added and failed targets, where failed targets are those skipped as duplicates or whose insert threw an Exception
    """

    added: list[NewScrapeTarget] = []
    failed: list[NewScrapeTarget] = []

    for t in new_targets:
        try:
            vals = t.model_dump(include=t.model_fields_set)
            vals["config"] = t.config.model_dump(mode="json")
            if "meta" in vals:
                vals["meta"] = t.meta.model_dump(mode="json")

            should_append = True
            if duplicate_comp_func is not None:
                should_append = await duplicate_comp_func(t)
            elif warn_on_duplicate or discard_duplicates:
                duplicates = await _get_entity_by(
                    s, ScrTargetTable, ScrTargetTable.url == t.url
                )
                if len(duplicates) > 0:
                    if warn_on_duplicate:
                        log.warning(
                            f"""Target {t.name} has {len(duplicates)} possible duplicates:
                            {duplicates}"""
                        )
                    if discard_duplicates:
                        should_append = False

            if should_append:
                async with s.begin_nested():
                    await s.execute(insert(ScrTargetTable).values(**vals))
                added.append(t)
            else:
                failed.append(t)

        except Exception:
            log.exception(f"failed to create target: {t}")
            failed.append(t)

    return added, failed


async def get_carriers_by(
        s: AsyncSession, *, homepage: str | None = None, name: str | None = None
) -> list[Carrier]:
    filters = [(CarriersTable.homepage, homepage), (CarriersTable.name, name)]
    rows = await _get_entity_by(
        s, CarriersTable,
        *(column.like(value) for column, value in filters if value)
    )
    return [Carrier.model_validate(row) for row in rows]


async def get_similar_carriers_by(
        s: AsyncSession,
        *,
        homepage: str | None = None,
        name: str | None = None,
        similarity_threshold: float = DEFAULT_TRGM_SIMILARITY_THRESHOLD,
) -> list[tuple[Carrier, float]]:
    rows = await _get_similar_entities(
        s,
        CarriersTable,
        {CarriersTable.homepage: homepage, CarriersTable.name: name},
        similarity_threshold,
    )
    return [(Carrier.model_validate(row), score) for row, score in rows]
