import asyncio
from logging import getLogger

from ride_locally.config import config
from ride_locally.db.schema import ScrTargetTable
from ride_locally.worker.run_scrape import run_scrape
from ride_locally.worker.target_utils import get_due_scraper_targets, put_or_shutdown

log = getLogger(__name__)

# backoff (seconds) when the producer's DB fetch fails repeatedly
_ERROR_BACKOFF = 5.0
# how often consumers re-check the shutdown flag while waiting for work
_CONSUMER_POLL = 1.0


async def scraper(shutdown_sig):
    queue: asyncio.Queue[ScrTargetTable] = asyncio.Queue(maxsize=50)
    # In-memory dedup: target ids currently queued or being scraped.
    in_flight: set[int] = set()

    async def produce_scrape_targets():
        # Producer flow:
        #   1. Poll the DB for due targets.
        #   2. Enqueue each new one (skipping anything already in flight).
        #   3. Sleep for SCRAPER_POLL_INTERVAL, then repeat.
        # Any blocking await observes _shutdown so the loop can exit promptly.
        # Exception in the DB call -> short backoff so we don't hot-loop on a
        # broken DB while still allowing shutdown to interrupt the wait.
        while not shutdown_sig.is_set():
            try:
                targets = await get_due_scraper_targets()
                for t in targets:
                    if t.id in in_flight:
                        continue
                    # Mark before put: if shutdown wins the race in
                    # _put_orshutdown_sig we must roll the mark back.
                    in_flight.add(t.id)
                    if not await put_or_shutdown(queue, t, shutdown_sig):
                        in_flight.discard(t.id)
                        return
            except Exception:
                log.exception("producer error in scraper")
                try:
                    await asyncio.wait_for(shutdown_sig.wait(), _ERROR_BACKOFF)
                except asyncio.TimeoutError:
                    pass
                continue

            # Sleep until either the poll interval elapses or shutdown is set.
            try:
                await asyncio.wait_for(
                    shutdown_sig.wait(), config.SCRAPER_POLL_INTERVAL
                )
            except asyncio.TimeoutError:
                pass

    async def consume_scrape_targets():
        # Consumer flow:
        #   1. Pull a target off the queue (short timeout so we periodically
        #      re-check the shutdown flag while idle).
        #   2. Run the scrape; log + swallow any error so the worker survives.
        #   3. Always clear in_flight + task_done in finally.
        # On shutdown the worker finishes its current task and then exits on
        # the next loop check - in-flight scrapes are NOT interrupted.
        while not shutdown_sig.is_set():
            try:
                target = await asyncio.wait_for(queue.get(), timeout=_CONSUMER_POLL)
            except asyncio.TimeoutError:
                continue

            try:
                ok = await run_scrape(target)
                if not ok:
                    log.warning(f"Scrape failed for target {target.id} ({target.name})")
            except Exception:
                log.exception(f"unexpected error scraping target {target.id}")
            finally:
                in_flight.discard(target.id)
                queue.task_done()

    # Spawn producer + N consumers, then block here until shutdown.
    # Shutdown order: wait for signal -> wait for producer to exit naturally
    # -> wait for consumers to drain their current task and exit.
    producer = asyncio.create_task(produce_scrape_targets(), name="scraper-producer")
    consumers = [
        asyncio.create_task(consume_scrape_targets(), name=f"scraper-consumer-{i}")
        for i in range(config.SCRAPER_WORKER_COUNT)
    ]

    await shutdown_sig.wait()

    await asyncio.gather(producer, return_exceptions=True)
    await asyncio.gather(*consumers, return_exceptions=True)

    log.info("scraper stopped")
