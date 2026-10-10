# NiceGUI: builds the web UI
# This file only handles display and clicks — the real check lives in the service
from nicegui import ui

from app.service.url_checker import check_url


def _color_for_category(category: str) -> str:
    # Map service categories to NiceGUI/Quasar text colors
    if category == "healthy":
        return "text-positive"
    if category in ("client_error", "invalid_input", "unexpected"):
        # Reachable but not OK, or bad input → warning style
        return "text-orange"
    # unreachable / server_error → error style
    return "text-negative"


def build_url_check_page() -> None:
    # Create UI elements once, then only update them later
    url_input = ui.input(placeholder="Enter URL")
    # whitespace-pre-line: keep line breaks from the multi-line message
    result = ui.label("No check yet").classes("text-grey whitespace-pre-line")

    async def on_check() -> None:
        # Show a "loading" state while we wait for the network
        result.text = "Checking …"
        result.classes(replace="text-grey whitespace-pre-line")

        # Call the service (no HTTP logic in the UI)
        check_result = await check_url(url_input.value)

        # Show the detailed message; color depends on category
        result.text = check_result.message
        color = _color_for_category(check_result.category)
        # replace= fully replaces the previous color classes
        result.classes(replace=f"{color} whitespace-pre-line")

    # on_click: run on_check when the button is pressed
    ui.button("Check URL", on_click=on_check)
