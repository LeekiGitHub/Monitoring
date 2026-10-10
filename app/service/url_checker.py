# dataclass: a simple way to store related values in one object
# httpx: makes HTTP requests (e.g. GET to a URL)
from dataclasses import dataclass
import httpx


# Holds the result of one URL check (no UI here — only data)
@dataclass
class CheckResult:
    url: str
    ok: bool
    message: str
    # Optional: None when we never got a status code (empty input / network error)
    status_code: int | None = None


# async = function can wait for the network without blocking the caller
async def check_url(url: str) -> CheckResult:
    # .strip() removes leading/trailing whitespace
    url = url.strip()
    if not url:
        # stop here; no request needed
        return CheckResult(
            url="",
            ok=False,
            message="Please enter a URL",
        )

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
