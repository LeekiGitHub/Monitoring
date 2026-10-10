# Entry point: wire UI and start the NiceGUI server
from nicegui import ui

from app.ui.url_check_page import build_url_check_page

# Build the page (input, button, label)
build_url_check_page()

# Start the NiceGUI server (opens the page in the browser)
ui.run()
