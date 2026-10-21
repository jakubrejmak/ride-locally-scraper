from sqlalchemy import select

from ride_locally.db.schema import ScrapeStatus, ScrRunTable, ScrTargetTable
from ride_locally.db.session import session
from ride_locally.models.ScraperRun import ScraperRun
from ride_locally.models.files import FileResult
from ride_locally.worker.files import read_result


async def get_previous_run_result_by(scrape_url: str) -> ScraperRun | None:
    async with session() as s:
        q = select(ScrTargetTable.id).where(ScrTargetTable.url == scrape_url)
        target_id = (await s.execute(q)).scalar_one_or_none()
        if target_id is None:
            return None

        q = (
            select(ScrRunTable)
            .where(
                ScrRunTable.target_id == target_id,
                ScrRunTable.status == ScrapeStatus.success,
                ScrRunTable.o_filepath.is_not(None),
            )
            .order_by(ScrRunTable.finished_at.desc())
            .limit(1)
        )

        run = (await s.execute(q)).scalar_one_or_none()

        return ScraperRun.model_validate(run) if run else None


def get_file_bytes_from_scrape_run(run: ScraperRun) -> bytes | None:
    filepath = run.o_filepath

    if not filepath:
        return None

    previous = read_result(filepath, FileResult)

    if not previous or not previous.data:
        return None

    return previous.data[0].bytes
