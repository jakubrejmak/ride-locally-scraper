import asyncio

###
# small waiting primitives shared by the worker loops, notifier, and reaper.
# every long await in this codebase should be interruptible by shutdown -
# these helpers make that the default without repeating the wait_for/except
# pattern at every call site.
###


async def sleep_or_shutdown(shutdown: asyncio.Event, seconds: float) -> bool:
    """Sleep up to `seconds`, or until shutdown fires. Returns True if shutdown
    fired, False on timeout."""
    try:
        await asyncio.wait_for(shutdown.wait(), timeout=seconds)
        return True
    except asyncio.TimeoutError:
        return False


async def wait_or_shutdown(
    event: asyncio.Event, shutdown: asyncio.Event, timeout: float
) -> str:
    """Wait for `event`, `shutdown`, or `timeout`, whichever fires first.
    Returns 'event' / 'shutdown' / 'timeout'.

    Used by idle worker loops: wake immediately on a NOTIFY, wake on shutdown,
    or fall back to the poll interval if both are quiet.
    """
    if shutdown.is_set():
        return "shutdown"
    if event.is_set():
        return "event"

    ev_task = asyncio.create_task(event.wait())
    sd_task = asyncio.create_task(shutdown.wait())
    try:
        done, _ = await asyncio.wait(
            {ev_task, sd_task},
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if sd_task in done:
            return "shutdown"
        if ev_task in done:
            return "event"
        return "timeout"
    finally:
        ev_task.cancel()
        sd_task.cancel()
