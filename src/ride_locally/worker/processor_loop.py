import asyncio
from logging import getLogger

from ride_locally.config import config
from ride_locally.worker.run_process import run_process
from ride_locally.worker.utils.loop_utils import claim_processor_run, release_processor_run
from ride_locally.worker.wait import wait_or_shutdown

log = getLogger(__name__)


async def processor(
    shutdown: asyncio.Event,
    run_ready: asyncio.Event,
    worker_id: str,
) -> None:
    # same shape as scraper(): claim one pending run, process it, release.
    # runs are only inserted with should_process=True when the scrape produced
    # a diff, so the claim query never returns work we'd want to skip.
    async def worker(idx: int) -> None:
        wid = f"{worker_id}#p{idx}"
        while not shutdown.is_set():
            run = await claim_processor_run(wid)
            if run is None:
                await wait_or_shutdown(
                    run_ready, shutdown, config.PROCESSOR_POLL_FALLBACK
                )
                continue

            try:
                ok = await run_process(run)
                if not ok:
                    log.warning(f"process failed for run {run.id}")
            except Exception:
                log.exception(f"unexpected error processing run {run.id}")
            finally:
                try:
                    await release_processor_run(run.id)
                except Exception:
                    log.exception(f"failed to release run {run.id}")

    workers = [
        asyncio.create_task(worker(i), name=f"processor-{i}")
        for i in range(config.PROCESSOR_WORKER_COUNT)
    ]

    await shutdown.wait()
    await asyncio.gather(*workers, return_exceptions=True)

    log.info("processor stopped")
