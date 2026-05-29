import asyncio
from logging import getLogger

from ride_locally.config import config
from ride_locally.db.schema import ScrRunTable
from ride_locally.worker.run_process import run_process
from ride_locally.worker.target_utils import get_due_processor_targets, put_or_shutdown

log = getLogger(__name__)

# backoff (seconds) when the producer's DB fetch fails repeatedly
_ERROR_BACKOFF = 5.0
# how often consumers re-check the shutdown flag while waiting for work
_CONSUMER_POLL = 1.0


async def processor(shutdown_sig):
    # Same producer/consumer shape as scraper(), but operates on completed
    # scrape runs (ScrRunTable rows) instead of targets. Smaller queue
    # because each run is expensive (LLM calls) - we don't want a big backlog.
    queue: asyncio.Queue[ScrRunTable] = asyncio.Queue(maxsize=3)
    in_flight: set[int] = set()

    async def produce_processor_targets():
        # See scraper.produce_scrape_targets for the flow - identical pattern.
        while not shutdown_sig.is_set():
            try:
                runs = await get_due_processor_targets()
                for r in runs:
                    if r.id in in_flight:
                        continue
                    in_flight.add(r.id)
                    if not await put_or_shutdown(queue, r, shutdown_sig):
                        in_flight.discard(r.id)
                        return
            except Exception:
                log.exception("producer error in processor")
                try:
                    await asyncio.wait_for(shutdown_sig.wait(), _ERROR_BACKOFF)
                except asyncio.TimeoutError:
                    pass
                continue

            try:
                await asyncio.wait_for(
                    shutdown_sig.wait(), config.PROCESSOR_POLL_INTERVAL
                )
            except asyncio.TimeoutError:
                pass

    async def consume_processor_targets():
        # See scraper.consume_scrape_targets for the flow - identical pattern.
        while not shutdown_sig.is_set():
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
        asyncio.create_task(consume_processor_targets(), name=f"processor-consumer-{i}")
        for i in range(config.PROCESSOR_WORKER_COUNT)
    ]

    await shutdown_sig.wait()

    await asyncio.gather(producer, return_exceptions=True)
    await asyncio.gather(*consumers, return_exceptions=True)

    log.info("processor stopped")
