###
#   main service
#   orchestrates the loop
###

import asyncio
import logging
import signal
from logging import getLogger

from lib.processor_loop import processor
from lib.scraper_loop import scraper

log = getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

_shutdown = asyncio.Event()


def _handle_sig():
    log.info("shutdown signal received")
    _shutdown.set()


async def main():
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


if __name__ == "__main__":
    asyncio.run(main())
