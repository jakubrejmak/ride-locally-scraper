import asyncio
from logging import getLogger

from ride_locally.config import config
from ride_locally.worker.target_utils import reap_stale_claims
from ride_locally.worker.wait import sleep_or_shutdown

log = getLogger(__name__)


async def reaper(shutdown: asyncio.Event) -> None:
    # clears claimed_at on rows whose worker died mid-job
    # (see reap_stale_claims for the per-status rules). does nothing in the
    # normal case - workers release their own rows in finally blocks.
    while not shutdown.is_set():
        if await sleep_or_shutdown(shutdown, config.WORKER_REAPER_INTERVAL):
            return
        try:
            reaped = await reap_stale_claims(config.WORKER_STALE_CLAIM_SECONDS)
            log.info(f"reaped {reaped} tasks")
        except Exception:
            log.exception("reaper failed")

    log.info("reaper stopped")
