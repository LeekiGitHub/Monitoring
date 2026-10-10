# NiceGUI: builds the web UI
# This file only handles display and clicks — the real check lives in the service
from nicegui import ui

from app.service.url_checker import check_url


def build_url_check_page() -> None:
    # Create UI elements once, then only update them later
    url_input = ui.input(placeholder="Enter URL")
    # .classes(...) sets CSS classes (here: grey text)
    result = ui.label("No check yet").classes("text-grey")

    async def on_check() -> None:
        # Show a "loading" state while we wait for the network
        result.text = "Checking …"
        result.classes(replace="text-grey")

        # Call the service (no HTTP logic in the UI)
        check_result = await check_url(url_input.value)

        # Map the service result to text and color
        result.text = check_result.message
        if not check_result.url:
            # Empty input → warning style
            result.classes(replace="text-orange")
        elif check_result.ok:
            # replace= fully replaces the previous color classes
            result.classes(replace="text-positive")
        else:
            result.classes(replace="text-negative")

    # on_click: run on_check when the button is pressed
    ui.button("Check URL", on_click=on_check)
