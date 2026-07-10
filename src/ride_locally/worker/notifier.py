import asyncio
from logging import getLogger

import asyncpg

from ride_locally.config import config
from ride_locally.worker.wait import sleep_or_shutdown

###
# LISTEN/NOTIFY bridge.
#
# one dedicated asyncpg connection (NOT from the SQLAlchemy pool - LISTEN
# requires a pinned connection). two channels, one shared asyncio.Event per
# channel; workers await those events to wake immediately on new work.
#
# reconnect loop keeps the connection alive across DB restarts. on every
# (re)connect both events are fired once so idle workers reconcile against
# anything that may have arrived during downtime.
###

log = getLogger(__name__)

# backoff between reconnect attempts after a connection loss
_RECONNECT_BACKOFF = 5.0

_TARGET_CHANNEL = "scr_target_ready"
_RUN_CHANNEL = "scr_run_ready"


def _asyncpg_dsn() -> str:
    # SQLAlchemy uses postgresql+asyncpg://...  asyncpg wants plain postgresql://
    dsn = config.DATABASE_URL
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _pulse(event: asyncio.Event) -> None:
    event.set()
    event.clear()


async def notifier(
    shutdown: asyncio.Event,
    target_ready: asyncio.Event,
    run_ready: asyncio.Event,
) -> None:
    dsn = _asyncpg_dsn()

    while not shutdown.is_set():
        # fires when the connection terminates for any reason
        conn_lost = asyncio.Event()
        conn: asyncpg.connection.Connection | None = None

        try:
            conn = await asyncpg.connect(dsn)
            assert conn is not None

            conn.add_termination_listener(lambda *_: conn_lost.set())

            await conn.add_listener(
                _TARGET_CHANNEL, lambda *_: _pulse(target_ready)
            )
            await conn.add_listener(
                _RUN_CHANNEL, lambda *_: _pulse(run_ready)
            )

            # reconcile: something may have been added while we were disconnected.
            _pulse(target_ready)
            _pulse(run_ready)

            log.info("notifier connected, listening on %s / %s", _TARGET_CHANNEL, _RUN_CHANNEL)

            # sit here until either shutdown or the connection dies.
            sd_task = asyncio.create_task(shutdown.wait())
            lost_task = asyncio.create_task(conn_lost.wait())
            try:
                await asyncio.wait(
                    {sd_task, lost_task}, return_when=asyncio.FIRST_COMPLETED
                )
            finally:
                sd_task.cancel()
                lost_task.cancel()

            if shutdown.is_set():
                return

            log.warning("notifier connection lost, reconnecting")

        except Exception:
            log.exception("notifier error")

        finally:
            if conn is not None:
                try:
                    await conn.close()
                except Exception:
                    pass

        # backoff before reconnect; interruptible by shutdown.
        if await sleep_or_shutdown(shutdown, _RECONNECT_BACKOFF):
            return

    log.info("notifier stopped")
