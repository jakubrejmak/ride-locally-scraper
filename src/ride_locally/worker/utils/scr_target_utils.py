from collections.abc import Awaitable, Callable, Iterable
from logging import getLogger

from sqlalchemy import func, insert, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.operators import like_op

from ride_locally.db.schema import CarriersTable, ScrTargetTable
from ride_locally.db.session import session
from ride_locally.models.targets import NewScrTarget, ScrTarget
from ride_locally.worker.utils.shared import diff_model_against

log = getLogger(__name__)


async def update_scr_target(target: ScrTarget, updated: NewScrTarget) -> dict | None:
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


async def _get_similar_targets_trgm(
    session: AsyncSession, target: NewScrTarget, similarity_threshold: float
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
    await session.execute(text(f"SET LOCAL pg_trgm.similarity_threshold = {thr}"))

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
    r = await session.execute(q)
    return list(r.scalars().all())


async def _get_duplicate_targets_url(
    session: AsyncSession, target: NewScrTarget
) -> list[ScrTargetTable]:

    q = select(ScrTargetTable).where(ScrTargetTable.url == target.url)
    r = await session.execute(q)
    return list(r.scalars().all())


async def add_new_targets(
    new_targets: Iterable[NewScrTarget],
    *,
    warn_on_duplicate: bool = False,
    discard_duplicates: bool = False,
    duplicate_comp_func: Callable[[AsyncSession, NewScrTarget], Awaitable[bool]]
    | None = None,
) -> tuple[list[NewScrTarget], list[NewScrTarget]]:
    """
    Adds new scraper targets to `scr_targets`.

    params:
        warn_on_duplicate: bool - emits warning level log at each target deemed duplicated by the default comparator function.
        discard_duplicates: bool - target will be omitted if deemed duplicated by default comparator function
        duplicate_comp_func: Callable[[AsyncSession, NewScrTarget], Awaitable[bool]] - custom comparator function. Returns True if target should be inserted, False to skip target. Passing this function invalidates `warn_on_duplicate` and `discard_duplicates` parameters.
    returns:
        tuple of lists with added and failed targets, where failed targets are those whose insert threw an Exception
    """

    if not new_targets:
        return [], []

    added: list[NewScrTarget] = []
    failed: list[NewScrTarget] = []

    for t in new_targets:
        try:
            vals = t.model_dump(exclude_unset=True)

            should_append = True
            async with session() as s:
                if duplicate_comp_func is not None:
                    should_append = await duplicate_comp_func(s, t)
                else:
                    duplicates = await _get_duplicate_targets_url(s, t)
                    if len(duplicates) > 0:
                        if warn_on_duplicate:
                            log.warning(
                                f"""Target {t.name} has {len(duplicates)} possible duplicates:
                                {duplicates}"""
                            )
                        if discard_duplicates:
                            should_append = False

                if should_append:
                    await s.execute(insert(ScrTargetTable).values(**vals))
                    added.append(t)

                await s.commit()

        except Exception:
            log.error(f"failed to create target: {t}")
            failed.append(t)

    return added, failed


async def get_carrier_id_by(*, homepage: str | None = None, name: str | None = None):
    async with session() as s:
        stmt = select(CarriersTable.id)

        filters = [
            (CarriersTable.homepage, homepage),
            (CarriersTable.name, name),
        ]

        for column, value in filters:
            if not value:
                continue
            stmt = stmt.where(like_op(column, value))

        result = await s.execute(stmt)
        ids = result.scalars().all()

        if len(ids) > 1:
            raise Exception(
                f"Multiple carrier ids matched for filters {[f[1] for f in filters if f[1] is not None]}"
            )

    return ids[0]
