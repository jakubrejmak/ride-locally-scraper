###
#   main service
#   orchestrates the loop
###

import asyncio
import logging
import signal
from logging import getLogger
from logging.handlers import RotatingFileHandler

from ride_locally.worker.processor_loop import processor
from ride_locally.worker.scraper_loop import scraper

log = getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers= [
        logging.StreamHandler(),
        RotatingFileHandler("worker.log", mode="a", maxBytes=10_000_000, backupCount=5)
    ]
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

    await asyncio.gather(
        scraper(_shutdown),
        processor(_shutdown),
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
