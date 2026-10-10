# dataclass: a simple way to store related values in one object
# HTTPStatus: turns 404 into the text "Not Found"
# time.perf_counter: precise stopwatch for measuring duration
# urlparse: splits a URL into parts (scheme, host, path, …)
# httpx: makes HTTP requests (e.g. GET to a URL)
from dataclasses import dataclass
from http import HTTPStatus
import time
from urllib.parse import urlparse

import httpx


# Holds the result of one URL check (no UI here — only data)
#
# Two different ideas (important for monitoring):
#   reachable = the server answered at all (any HTTP status, even 404 or 500)
#   healthy   = the site works as expected (status 2xx, e.g. 200 OK)
#
# category helps the UI pick a color / summary:
#   invalid_input | unreachable | healthy | client_error | server_error | unexpected
@dataclass
class CheckResult:
    url: str
    reachable: bool
    healthy: bool
    category: str
    message: str
    # Optional details — None when we never got a real HTTP response
    status_code: int | None = None
    status_text: str | None = None
    response_time_ms: float | None = None
    final_url: str | None = None


def _status_text(status_code: int) -> str:
    # Convert 404 → "Not Found", 200 → "OK", …
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        # Rare / unknown codes have no official name
        return "Unknown"


def _explain_status(status_code: int) -> tuple[bool, bool, str, str]:
    """Turn a status code into reachable/healthy/category/short explanation.

    Returns: (reachable, healthy, category, explanation)
    """
    # We received an HTTP response → the server (or something in front) is reachable
    reachable = True

    if 200 <= status_code < 300:
        return (
            reachable,
            True,
            "healthy",
            "Site works as expected (success response).",
        )
    if 300 <= status_code < 400:
        # Unusual here because we follow redirects; leftover 3xx is unexpected
        return (
            reachable,
            False,
            "unexpected",
            "Got a redirect status even though redirects are followed.",
        )
    if 400 <= status_code < 500:
        return (
            reachable,
            False,
            "client_error",
            "Server is reachable, but the page/request failed (e.g. 404 Not Found).",
        )
    if 500 <= status_code < 600:
        return (
            reachable,
            False,
            "server_error",
            "Server is reachable, but it reported an internal error.",
        )

    return (
        reachable,
        False,
        "unexpected",
        "Got an unusual HTTP status code.",
    )


def _format_details(
    url: str,
    reachable: bool,
    healthy: bool,
    explanation: str,
    status_code: int | None = None,
    status_text: str | None = None,
    response_time_ms: float | None = None,
    final_url: str | None = None,
) -> str:
    # Build a multi-line summary for the UI (one place for all wording)
    yes_no = {True: "yes", False: "no"}
    lines = [
        f"URL: {url}" if url else "URL: (empty)",
        f"Reachable: {yes_no[reachable]}",
        f"Healthy: {yes_no[healthy]}",
        f"Detail: {explanation}",
    ]

    if status_code is not None:
        # e.g. "Status: 404 Not Found"
        label = status_text or _status_text(status_code)
        lines.append(f"Status: {status_code} {label}")

    if response_time_ms is not None:
        # :.0f = round to whole milliseconds
        lines.append(f"Response time: {response_time_ms:.0f} ms")

    # Show final URL only when redirects changed it
    if final_url and final_url.rstrip("/") != url.rstrip("/"):
        lines.append(f"Final URL (after redirects): {final_url}")

    # "\n".join = put each line under the previous one
    return "\n".join(lines)


def normalize_and_validate_url(url: str) -> str | CheckResult:
    """Prepare the URL before we check it.

    Returns:
      - a string = the cleaned URL is ready to request
      - a CheckResult = something is wrong; stop and show that message
    """
    # .strip() removes leading/trailing whitespace
    url = url.strip()
    if not url:
        # stop here; no request needed
        return CheckResult(
            url="",
            reachable=False,
            healthy=False,
            category="invalid_input",
            message=_format_details(
                url="",
                reachable=False,
                healthy=False,
                explanation="Please enter a URL.",
            ),
        )

    # Users often type "example.com" without http/https — add https:// for them
    if "://" not in url:
        url = "https://" + url

    # Break the URL into parts so we can check scheme and host
    # Example: https://example.com/path → scheme="https", netloc="example.com"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return CheckResult(
            url=url,
            reachable=False,
            healthy=False,
            category="invalid_input",
            message=_format_details(
                url=url,
                reachable=False,
                healthy=False,
                explanation="Please enter a valid http(s) URL.",
            ),
        )

    # All good — return the normalized URL string
    return url


# async = function can wait for the network without blocking the caller
async def check_url(url: str) -> CheckResult:
    # First: clean + validate (no network yet)
    prepared = normalize_and_validate_url(url)
    # isinstance: "is prepared a CheckResult?" → validation already failed
    if isinstance(prepared, CheckResult):
        return prepared
    url = prepared

    # Start our own stopwatch (also works when the request fails)
    started = time.perf_counter()

    try:
        # AsyncClient: HTTP client for async code
        # follow_redirects: follow e.g. http → https
        # timeout: give up after 5 seconds
        async with httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client:
            # await: wait for the server response
            response = await client.get(url)

        # How many milliseconds since "started"?
        response_time_ms = (time.perf_counter() - started) * 1000

        status_code = response.status_code
        status_text = _status_text(status_code)
        # After redirects, response.url may differ from the URL we typed
        final_url = str(response.url)

        reachable, healthy, category, explanation = _explain_status(status_code)

        return CheckResult(
            url=url,
            reachable=reachable,
            healthy=healthy,
            category=category,
            message=_format_details(
                url=url,
                reachable=reachable,
                healthy=healthy,
                explanation=explanation,
                status_code=status_code,
                status_text=status_text,
                response_time_ms=response_time_ms,
                final_url=final_url,
            ),
            status_code=status_code,
            status_text=status_text,
            response_time_ms=response_time_ms,
            final_url=final_url,
        )
    except httpx.RequestError as e:
        # e.g. DNS failure, timeout, no connection — no HTTP status at all
        # Still record how long we waited before giving up
        response_time_ms = (time.perf_counter() - started) * 1000
        return CheckResult(
            url=url,
            reachable=False,
            healthy=False,
            category="unreachable",
            message=_format_details(
                url=url,
                reachable=False,
                healthy=False,
                explanation=f"Could not reach the server: {e}",
                response_time_ms=response_time_ms,
            ),
            response_time_ms=response_time_ms,
        )
