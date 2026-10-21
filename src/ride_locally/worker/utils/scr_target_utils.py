from collections.abc import Awaitable, Callable, Iterable
from logging import getLogger
from typing import TypeVar

from sqlalchemy import ColumnElement, func, insert, or_, select, text, update
from sqlalchemy.orm import DeclarativeBase

from ride_locally.db.schema import CarriersTable, ScrTargetTable
from ride_locally.db.session import session
from ride_locally.models.ScraperTarget import NewScrapeTarget, ScrapeTarget
from ride_locally.worker.utils.shared import diff_model_against

log = getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)


async def update_scr_target(target: ScrapeTarget,
                            updated: NewScrapeTarget) -> dict | None:
    current = target.model_dump(exclude_unset=True)
    diff = diff_model_against(updated, current)
    if not diff:
        return None

    async with session() as s:
        await s.execute(
            update(ScrTargetTable).where(ScrTargetTable.id == target.id).values(**diff)
        )
        await s.commit()

    return diff


async def disable_targets(targets: Iterable[ScrapeTarget], *,
                          reason: str) -> int:
    async with session() as s:
        stmt = (
            update(ScrTargetTable)
            .where(ScrTargetTable.id.in_(target.id for target in targets))
            .values(
                is_active=False,
                meta={"deactivate_reason": reason},
            )
            .returning(ScrTargetTable.id)
        )
        res = await s.execute(stmt)
        await s.commit()

    updated = res.scalars().all()

    return len(updated)


async def _get_similar_targets_trgm(
        target: NewScrapeTarget, similarity_threshold: float
) -> list[ScrTargetTable]:
    """
    Existing scr_targets whose `name` or `url` trigram-matches `target` at or
    above `similarity_threshold` (0-1), ordered most-similar first. Empty list
    means "no duplicate candidates".

    Uses pg_trgm's `%` operator so the gin_trgm_ops indexes on name/url get
    used instead of a seq scan. The threshold is scoped to the current
    transaction via SET LOCAL so we don't leak it to other queries sharing
    the pooled connection. AsyncSession opens its transaction lazily on the
    first execute(), so this SET is what starts it.
    """
    # SET does not accept bind params, hence string interpolation
    thr = float(similarity_threshold)

    q = (
        select(ScrTargetTable)
        .where(
            or_(
                ScrTargetTable.name.op("%")(target.name),
                ScrTargetTable.url.op("%")(target.url),
            )
        )
        .order_by(
            func.greatest(
                func.similarity(ScrTargetTable.name, target.name),
                func.similarity(ScrTargetTable.url, target.url),
            ).desc()
        )
    )
    async with session() as s:
        await s.execute(text(f"SET LOCAL pg_trgm.similarity_threshold = {thr}"))
        r = await s.execute(q)
        return list(r.scalars().all())


async def get_entity_by(table: type[T], *where: ColumnElement[bool]) -> list[T]:
    async with session() as s:
        r = await s.execute(select(table).where(*where))
        return list(r.scalars().all())


async def get_targets_by(
    *, name: str | None = None, url: str | None = None
) -> list[ScrTargetTable]:
    filters = [(ScrTargetTable.name, name), (ScrTargetTable.url, url)]
    return await get_entity_by(
        ScrTargetTable, *(column.like(value) for column, value in filters if value)
    )


async def add_new_targets(
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
        duplicate_comp_func: Callable[[NewScrTarget], Awaitable[bool]] - custom comparator function. Returns True if target should be inserted, False to skip target. Passing this function invalidates `warn_on_duplicate` and `discard_duplicates` parameters.
    returns:
        tuple of lists with added and failed targets, where failed targets are those whose insert threw an Exception
    """

    if not new_targets:
        return [], []

    added: list[NewScrapeTarget] = []
    failed: list[NewScrapeTarget] = []

    for t in new_targets:
        try:
            vals = t.model_dump(exclude_unset=True)

            should_append = True
            if duplicate_comp_func is not None:
                should_append = await duplicate_comp_func(t)
            else:
                duplicates = await get_entity_by(
                    ScrTargetTable, ScrTargetTable.url == t.url
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
                async with session() as s:
                    await s.execute(insert(ScrTargetTable).values(**vals))
                    await s.commit()
                added.append(t)

        except Exception:
            log.error(f"failed to create target: {t}")
            failed.append(t)

    return added, failed


async def get_carriers_by(
    *, homepage: str | None = None, name: str | None = None
) -> list[CarriersTable]:
    filters = [(CarriersTable.homepage, homepage), (CarriersTable.name, name)]
    return await get_entity_by(
        CarriersTable, *(column.like(value) for column, value in filters if value)
    )
