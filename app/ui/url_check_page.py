# asyncio: lets us wait for the network without freezing the page
# NiceGUI: builds the web UI. ui.timer repeats a function on a schedule
# This file only handles display and clicks — the real check lives in the service
import asyncio

from nicegui import ui
from nicegui.elements.timer import Timer

from app.service.url_checker import CheckCategory, check_url, normalize_and_validate_url

# How long to wait between automatic checks
CHECK_EVERY_SECONDS = 30


def _color_for_category(category: CheckCategory) -> str:
    # Map service categories to NiceGUI/Quasar text colors
    if category is CheckCategory.HEALTHY:
        return "text-positive"
    if category in (
        CheckCategory.CLIENT_ERROR,
        CheckCategory.INVALID_INPUT,
        CheckCategory.UNEXPECTED,
    ):
        # Reachable but not OK, or bad input → warning style
        return "text-orange"
    # UNREACHABLE / SERVER_ERROR → error style
    return "text-negative"


def build_url_check_page() -> None:
    # Create UI elements once, then only update them later
    url_input = ui.input(placeholder="Enter URL")
    status = ui.label("Not monitoring").classes("text-grey")
    # whitespace-pre-line: keep line breaks from the multi-line message
    result = ui.label("No check yet").classes("text-grey whitespace-pre-line")

    with ui.row():
        start_button = ui.button("Start monitoring")
        stop_button = ui.button("Stop monitoring")
    # Nothing is running yet, so Stop does nothing until we start
    stop_button.disable()

    # The one repeating timer. None = we are not looping.
    # We keep a single object so a second click cannot start a second loop.
    timer: Timer | None = None
    # Normalized URL we are watching, e.g. "https://example.com"
    watching_url: str | None = None
    # True while start_monitoring is still working (before the timer exists)
    starting = False
    # asyncio.Lock: only one HTTP check at a time, even if a tick overlaps
    check_lock = asyncio.Lock()

    def show_result(check_result) -> None:
        result.text = check_result.message
        color = _color_for_category(check_result.category)
        # replace= fully replaces the previous color classes
        result.classes(replace=f"{color} whitespace-pre-line")

    async def run_check(url: str) -> None:
        # locked() is True when another check is already inside the lock
        if check_lock.locked():
            return
        async with check_lock:
            result.text = "Checking …"
            result.classes(replace="text-grey whitespace-pre-line")
            # await: wait for the HTTP check without blocking the whole server
            check_result = await check_url(url)
            show_result(check_result)

    async def on_timer() -> None:
        # ui.timer calls this every CHECK_EVERY_SECONDS.
        # The callback is async, so NiceGUI runs it on the asyncio event loop.
        if watching_url is None:
            return
        await run_check(watching_url)

    async def start_monitoring() -> None:
        nonlocal timer, watching_url, starting

        # Already starting or already looping → do not create another timer
        if starting or timer is not None:
            return

        # Clean the URL first. A CheckResult here means the input is invalid.
        prepared = normalize_and_validate_url(url_input.value)
        if not isinstance(prepared, str):
            show_result(prepared)
            return

        # Set this before the first await, so a second click is ignored
        starting = True
        watching_url = prepared
        start_button.disable()
        stop_button.enable()
        status.text = f"Monitoring {prepared} every {CHECK_EVERY_SECONDS} seconds"

        try:
            # Check once immediately, so the user does not wait 30 seconds
            await run_check(prepared)
            # Stop may have been clicked while we were waiting for the network
            if watching_url != prepared:
                return
            # immediate=False: the first check already happened above.
            # The next one runs after 30 seconds, then again and again.
            timer = ui.timer(CHECK_EVERY_SECONDS, on_timer, immediate=False)
        finally:
            starting = False

    def stop_monitoring() -> None:
        nonlocal timer, watching_url
        # cancel() stops the NiceGUI timer loop so it will not fire again
        if timer is not None:
            timer.cancel()
            timer = None
        watching_url = None
        start_button.enable()
        stop_button.disable()
        status.text = "Monitoring stopped"

    # on_click: run these functions when the buttons are pressed
    start_button.on_click(start_monitoring)
    stop_button.on_click(stop_monitoring)
