###
# main scraper service
# go through the sources tab periodically, find is_active ones,
# check its schedule_cron and delegate the target to worker
###

import asyncio
import logging
import signal
from logging import getLogger
from conf import config
from lib.get_due_targets import *
from lib.run_scrape import *

_shutdown = asyncio.Event()
_semaphore = asyncio.Semaphore(5)

logger = getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

def _handle_sig():
    logger.info("shutdown signal recieved")
    _shutdown.set()

async def scrape_loop():
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_sig)

    tasks: set[asyncio.Task] = set()

    while not _shutdown.is_set():
        try:
            targets = await get_due_targets()
            for t in targets:
                task = asyncio.create_task(run_scrape(t, semaphore=_semaphore, stop_condition=_shutdown))
                tasks.add(task)
                task.add_done_callback(tasks.discard)
        except Exception as e:
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

def main():
    asyncio.run(scrape_loop())

if __name__ == "__main__":
    main()