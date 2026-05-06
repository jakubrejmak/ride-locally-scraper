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

logger = getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

_shutdown = asyncio.Event()


def _handle_sig():
    logger.info("shutdown signal received")
    _shutdown.set()


###
#   scrape loop gathers resources with static algorythims,
#   while process loop is mostly llm domain
#
#   some targets are discovery targets — listing pages where the script
#   finds N links (e.g. tender documents). since the processor handles
#   one input at a time, the script registers each link as its own target
#   so they get scraped individually and each produces one clean processor input.
#   targets that are a single page with one document skip this and return a
#   result directly without spawning new targets.
###


async def scraper():
    queue: asyncio.Queue[ttScrTargetTable] = asyncio.Queue(maxsize=50)

    async def producer():
        while not _shutdown.is_set():
            try:
                targets = await get_due_scraper_targets()
                for t in targets:
                    await queue.put(t)
                await asyncio.wait_for(_shutdown.wait(), config.SCRAPER_POLL_INTERVAL)
            except asyncio.TimeoutError:
                pass
            except Exception:
                logger.exception("scraper error")

    async def consumer():
        while not _shutdown.is_set():
            try:
                t = await asyncio.wait_for(queue.get(), timeout=1.0)
                await run_scrape(t)  # writes results to db
                queue.task_done()
            except asyncio.TimeoutError:
                pass
            except Exception:
                logger.exception("worker error")

    await asyncio.gather(
        producer(), *[consumer() for _ in range(config.SCRAPER_WORKER_COUNT)]
    )

    logger.info("scraper stopped")


async def processor():
    queue: asyncio.Queue[ttScrRunTable] = asyncio.Queue(maxsize=3)

    async def producer():
        while not _shutdown.is_set():
            try:
                targets = await get_due_processor_targets()
                for t in targets:
                    await queue.put(t)
                await asyncio.wait_for(_shutdown.wait(), config.PROCESSOR_POLL_INTERVAL)
            except asyncio.TimeoutError:
                pass
            except Exception:
                logger.exception("processor error")

    async def consumer():
        while not _shutdown.is_set():
            try:
                t = await asyncio.wait_for(queue.get(), timeout=1.0)
                await run_process(t)  # writes results to db
                queue.task_done()
            except asyncio.TimeoutError:
                pass
            except Exception:
                logger.exception("worker error")

    await asyncio.gather(
        producer(), *[consumer() for _ in range(config.PROCESSOR_WORKER_COUNT)]
    )

    logger.info("processor stopped")


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
