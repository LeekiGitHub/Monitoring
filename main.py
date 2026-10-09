# NiceGUI: builds the web UI
# httpx: makes HTTP requests (e.g. GET to a URL)
from nicegui import ui
import httpx

# Create UI elements once, then only update them later
url_input = ui.input(placeholder='Enter URL')
# .classes(...) sets CSS classes (here: grey text)
result = ui.label('Noch kein Check').classes('text-grey')


# async = function can wait for the network without blocking the UI
async def check_url():
    # .strip() removes leading/trailing whitespace
    url = url_input.value.strip()
    if not url:
        result.text = 'Bitte eine URL eingeben'
        # replace= fully replaces the previous color classes
        result.classes(replace='text-orange')
        return  # stop here; no request needed

    result.text = 'Prüfe …'
    result.classes(replace='text-grey')

    try:
        # AsyncClient: HTTP client for async code
        # follow_redirects: follow e.g. http → https
        # timeout: give up after 5 seconds
        async with httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client:
            # await: wait for the server response
            r = await client.get(url)
        # Status < 500: server responded (even 404 counts as "reachable")
        ok = r.status_code < 500
        result.text = f'{url}: {r.status_code}'
        result.classes(replace='text-positive' if ok else 'text-negative')
    except httpx.RequestError as e:
        # e.g. DNS failure, timeout, no connection
        result.text = f'Nicht erreichbar: {e}'
        result.classes(replace='text-negative')


# on_click: run check_url when the button is pressed
ui.button('Check URL', on_click=check_url)

# start the NiceGUI server (opens the page in the browser)
ui.run()
