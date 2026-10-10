# dataclass: a simple way to store related values in one object
# urlparse: splits a URL into parts (scheme, host, path, …)
# httpx: makes HTTP requests (e.g. GET to a URL)
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


# Holds the result of one URL check (no UI here — only data)
@dataclass
class CheckResult:
    url: str
    ok: bool
    message: str
    # Optional: None when we never got a status code (empty input / network error)
    status_code: int | None = None


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
            ok=False,
            message="Please enter a URL",
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
            ok=False,
            message="Please enter a valid http(s) URL",
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

    try:
        # AsyncClient: HTTP client for async code
        # follow_redirects: follow e.g. http → https
        # timeout: give up after 5 seconds
        async with httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client:
            # await: wait for the server response
            response = await client.get(url)

        # Status < 500: server responded (even 404 counts as "reachable")
        ok = response.status_code < 500
        return CheckResult(
            url=url,
            ok=ok,
            message=f"{url}: {response.status_code}",
            status_code=response.status_code,
        )
    except httpx.RequestError as e:
        # e.g. DNS failure, timeout, no connection
        return CheckResult(
            url=url,
            ok=False,
            message=f"Unreachable: {e}",
        )
