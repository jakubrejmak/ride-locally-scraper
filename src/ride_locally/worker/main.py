###
#   main service
#   orchestrates the loop
###

import asyncio
import logging
import os
import signal
import socket
from logging import getLogger

from ride_locally.config import config
from ride_locally.worker.notifier import notifier
from ride_locally.worker.processor_loop import processor
from ride_locally.worker.reaper import reaper
from ride_locally.worker.scraper_loop import scraper

log = getLogger(__name__)
LOG_LVL_MAP = {
    "INFO": logging.INFO,
    "WARNING": logging.WARN,
    "ERROR": logging.ERROR,
}

logging.basicConfig(
    level=LOG_LVL_MAP[config.LOG_LVL],
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

_shutdown = asyncio.Event()


def _handle_sig() -> None:
    log.info("shutdown signal received")
    _shutdown.set()


async def run() -> None:
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_sig)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: _handle_sig())

    worker_id = config.WORKER_ID or f"{socket.gethostname()}:{os.getpid()}"

    # NOTIFY channels -> shared events. workers await their event; notifier
    # sets it on every LISTEN wakeup. one event per channel so scraper and
    # processor don't wake each other spuriously.
    target_ready = asyncio.Event()
    run_ready = asyncio.Event()

    await asyncio.gather(
        notifier(_shutdown, target_ready, run_ready),
        reaper(_shutdown),
        scraper(_shutdown, target_ready, worker_id),
        processor(_shutdown, run_ready, worker_id),
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
