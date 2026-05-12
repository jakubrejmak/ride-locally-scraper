###
#   main service
#   orchestrates the loop
###

import asyncio
import logging
import signal
from logging import getLogger

from conf import config
from db.schema import ttScrRunTable, ttScrTargetTable
from lib.run_process import run_process
from lib.run_scrape import run_scrape
from lib.target_utils import get_due_processor_targets, get_due_scraper_targets

log = getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

_shutdown = asyncio.Event()

# backoff (seconds) when the producer's DB fetch fails repeatedly
_ERROR_BACKOFF = 5.0
# how often consumers re-check the shutdown flag while waiting for work
_CONSUMER_POLL = 1.0


def _handle_sig():
    log.info("shutdown signal received")
    _shutdown.set()


async def _put_or_shutdown(queue: asyncio.Queue, item) -> bool:
    """Put `item` into `queue`, but bail out if shutdown is signaled while waiting.

    Returns True if the item was enqueued, False if shutdown won the race.
    """
    put_task = asyncio.create_task(queue.put(item))
    shutdown_task = asyncio.create_task(_shutdown.wait())
    try:
        done, _ = await asyncio.wait(
            {put_task, shutdown_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if put_task in done:
            return True
        put_task.cancel()
        return False
    finally:
        shutdown_task.cancel()


async def scraper():
    queue: asyncio.Queue[ttScrTargetTable] = asyncio.Queue(maxsize=50)
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
        while not _shutdown.is_set():
            try:
                targets = await get_due_scraper_targets()
                for t in targets:
                    if t.id in in_flight:
                        continue
                    # Mark before put: if shutdown wins the race in
                    # _put_or_shutdown we must roll the mark back.
                    in_flight.add(t.id)
                    if not await _put_or_shutdown(queue, t):
                        in_flight.discard(t.id)
                        return
            except Exception:
                log.exception("producer error in scraper")
                try:
                    await asyncio.wait_for(_shutdown.wait(), _ERROR_BACKOFF)
                except asyncio.TimeoutError:
                    pass
                continue

            # Sleep until either the poll interval elapses or shutdown is set.
            try:
                await asyncio.wait_for(_shutdown.wait(), config.SCRAPER_POLL_INTERVAL)
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
        while not _shutdown.is_set():
            try:
                target = await asyncio.wait_for(queue.get(), timeout=_CONSUMER_POLL)
            except asyncio.TimeoutError:
                continue

            try:
                ok = await run_scrape(target)
                if not ok:
                    log.warning(
                        f"Scrape failed for target {target.id} ({target.name})"
                    )
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

    await _shutdown.wait()

    await asyncio.gather(producer, return_exceptions=True)
    await asyncio.gather(*consumers, return_exceptions=True)

    log.info("scraper stopped")


async def processor():
    # Same producer/consumer shape as scraper(), but operates on completed
    # scrape runs (ttScrRunTable rows) instead of targets. Smaller queue
    # because each run is expensive (LLM calls) - we don't want a big backlog.
    queue: asyncio.Queue[ttScrRunTable] = asyncio.Queue(maxsize=3)
    in_flight: set[int] = set()

    async def produce_processor_targets():
        # See scraper.produce_scrape_targets for the flow - identical pattern.
        while not _shutdown.is_set():
            try:
                runs = await get_due_processor_targets()
                for r in runs:
                    if r.id in in_flight:
                        continue
                    in_flight.add(r.id)
                    if not await _put_or_shutdown(queue, r):
                        in_flight.discard(r.id)
                        return
            except Exception:
                log.exception("producer error in processor")
                try:
                    await asyncio.wait_for(_shutdown.wait(), _ERROR_BACKOFF)
                except asyncio.TimeoutError:
                    pass
                continue

            try:
                await asyncio.wait_for(
                    _shutdown.wait(), config.PROCESSOR_POLL_INTERVAL
                )
            except asyncio.TimeoutError:
                pass

    async def consume_processor_targets():
        # See scraper.consume_scrape_targets for the flow - identical pattern.
        while not _shutdown.is_set():
            try:
                run = await asyncio.wait_for(queue.get(), timeout=_CONSUMER_POLL)
            except asyncio.TimeoutError:
                continue

            try:
                ok = await run_process(run)
                if not ok:
                    log.warning(f"Process failed for run {run.id}")
            except Exception:
                log.exception(f"unexpected error processing run {run.id}")
            finally:
                in_flight.discard(run.id)
                queue.task_done()

    producer = asyncio.create_task(
        produce_processor_targets(), name="processor-producer"
    )
    consumers = [
        asyncio.create_task(
            consume_processor_targets(), name=f"processor-consumer-{i}"
        )
        for i in range(config.PROCESSOR_WORKER_COUNT)
    ]

    await _shutdown.wait()

    await asyncio.gather(producer, return_exceptions=True)
    await asyncio.gather(*consumers, return_exceptions=True)

    log.info("processor stopped")


async def main():
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_sig)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: _handle_sig())

    await asyncio.gather(
        scraper(),
        processor(),
    )


if __name__ == "__main__":
    asyncio.run(main())
