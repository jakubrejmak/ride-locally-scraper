###
#   main service
#   orchestrates the loop
###

import asyncio
import logging
import signal
from logging import getLogger

from conf import config
from lib.run_scrape import run_scrape
from lib.target_utils import get_due_targets

logger = getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

_shutdown = asyncio.Event()
_semaphore = asyncio.Semaphore(5)

# queues instead of gating behind a semaphore
# scrape_queue = asyncio.Queue(maxsize=100)
# process_queue = asyncio.Queue(maxsize=100)
# import_queue = asyncio.Queue(maxsize=100)

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


async def scrape_loop():
    tasks: set[asyncio.Task] = set()

    while not _shutdown.is_set():
        try:
            targets = await get_due_targets()
            for t in targets:
                task = asyncio.create_task(
                    run_scrape(t, semaphore=_semaphore, stop_condition=_shutdown)
                )
                tasks.add(task)
                task.add_done_callback(tasks.discard)
        except Exception:
            logger.exception("scrape_loop error")
        finally:
            try:
                await asyncio.wait_for(_shutdown.wait(), config.SRC_T_POLL_INTERVAL)
            except asyncio.TimeoutError:
                pass

    if tasks:
        logger.info(f"waiting for {len(tasks)} to finish")
        await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("scrape_loop stopped")


async def process_loop():
    pass


async def main():
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_sig)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: _handle_sig())

    await asyncio.gather(
        scrape_loop(),
        process_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
