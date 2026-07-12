import asyncio
from logging import getLogger

from ride_locally.config import config
from ride_locally.worker.run_scrape import run_scrape
from ride_locally.worker.utils.loop_utils import claim_scrape_target, release_scrape_target
from ride_locally.worker.wait import wait_or_shutdown

log = getLogger(__name__)


async def scraper(
    shutdown: asyncio.Event,
    target_ready: asyncio.Event,
    worker_id: str,
) -> None:
    # each worker is a standalone loop: claim one target, run it, release,
    # repeat. when the claim comes back empty (queue drained) we wait on
    # either a NOTIFY (new work arrived), shutdown, or the poll fallback
    # (cron-driven work that never emits a NOTIFY).
    async def worker(idx: int) -> None:
        wid = f"{worker_id}#s{idx}"
        while not shutdown.is_set():
            target = await claim_scrape_target(wid)
            if target is None:
                await wait_or_shutdown(
                    target_ready, shutdown, config.SCRAPER_POLL_FALLBACK
                )
                continue

            ok = False
            try:
                ok = await run_scrape(target)
                if not ok:
                    log.warning(f"scrape failed for target {target.id} ({target.name})")
            except Exception:
                log.exception(f"unexpected error scraping target {target.id}")
            finally:
                try:
                    await release_scrape_target(target, ok)
                except Exception:
                    log.exception(f"failed to release target {target.id}")

    workers = [
        asyncio.create_task(worker(i), name=f"scraper-{i}")
        for i in range(config.SCRAPER_WORKER_COUNT)
    ]

    await shutdown.wait()
    await asyncio.gather(*workers, return_exceptions=True)

    log.info("scraper stopped")
