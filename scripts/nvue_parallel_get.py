#!/usr/bin/env python3
import asyncio
import aiohttp
import base64
import json
import random
import ssl
from typing import Dict, Any, List, Tuple

# ---- CONFIG ----
USERNAME = "cumulus"
PASSWORD = "Lab123"

API_PATH = "/nvue_v1/evpn/vni/100/mac"
PORT = 8765

# Concurrency tuning:
CONCURRENCY = 300          # start 100-300; increase carefully
REQUEST_TIMEOUT = 10       # seconds
CONNECT_TIMEOUT = 5        # seconds
TOTAL_TIMEOUT = 15         # seconds
RETRIES = 3                # retry transient failures
BACKOFF_BASE = 0.5         # seconds

# If you're using self-signed certs (verify=False equivalent)
VERIFY_TLS = False         # set True if you have valid certs

# Example device list; for 1000s, load from file (see below)
DEVICES = ["leaf1", "leaf2", "leaf3", "leaf4"]
# ----------------

def auth_header(username: str, password: str) -> Dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}

def backoff(attempt: int) -> float:
    # exponential backoff + jitter
    return BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 0.25)

def build_ssl_context(verify: bool) -> ssl.SSLContext:
    if verify:
        return ssl.create_default_context()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

async def fetch_mac_table(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    device: str
) -> Tuple[str, Dict[str, Any]]:
    url = f"https://{device}:{PORT}{API_PATH}"

    async with semaphore:
        for attempt in range(RETRIES + 1):
            try:
                async with session.get(url) as resp:
                    text = await resp.text()

                    # Treat 429/5xx as retryable
                    if resp.status == 429 or 500 <= resp.status <= 599:
                        raise aiohttp.ClientResponseError(
                            request_info=resp.request_info,
                            history=resp.history,
                            status=resp.status,
                            message=text[:200],
                            headers=resp.headers
                        )

                    # Try JSON decode; keep raw text on failure
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        data = {"_raw": text}

                    return device, {
                        "ok": True,
                        "status": resp.status,
                        "url": url,
                        "data": data,
                    }

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == RETRIES:
                    return device, {
                        "ok": False,
                        "url": url,
                        "error": str(e),
                    }
                await asyncio.sleep(backoff(attempt))

async def run(devices: List[str]) -> Dict[str, Dict[str, Any]]:
    semaphore = asyncio.Semaphore(CONCURRENCY)

    timeout = aiohttp.ClientTimeout(
        total=TOTAL_TIMEOUT,
        connect=CONNECT_TIMEOUT,
        sock_read=REQUEST_TIMEOUT
    )

    ssl_ctx = build_ssl_context(VERIFY_TLS)

    headers = {
        "Accept": "application/json",
        **auth_header(USERNAME, PASSWORD),
    }

    # Connection pooling: tune limit_per_host if you hit per-device constraints
    connector = aiohttp.TCPConnector(
        ssl=ssl_ctx,
        limit=0,               # unlimited overall; semaphore controls concurrency
        ttl_dns_cache=300,
        enable_cleanup_closed=True
    )

    results: Dict[str, Dict[str, Any]] = {}

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers=headers
    ) as session:
        tasks = [fetch_mac_table(session, semaphore, d) for d in devices]
        for coro in asyncio.as_completed(tasks):
            device, result = await coro
            results[device] = result

    return results

def load_devices_from_file(path: str) -> List[str]:
    # One hostname/IP per line; supports comments and blanks
    out = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.append(line)
    return out

def summarize(results: Dict[str, Dict[str, Any]]):
    ok = [d for d, r in results.items() if r.get("ok")]
    bad = [d for d, r in results.items() if not r.get("ok")]

    print(f"Total: {len(results)} | OK: {len(ok)} | Failed: {len(bad)}")

    # Mimic your original output: "leaf1 has MACs <keys>"
    for d in ok:
        data = results[d].get("data", {})
        # Your r.json() seemed to produce a dict whose keys are MACs
        if isinstance(data, dict):
            print(f"{d} has MACs {list(data.keys())[:10]}{'...' if len(data) > 10 else ''}")
        else:
            print(f"{d} returned non-dict data")

    if bad:
        print("\nFailures:")
        for d in bad[:20]:
            print(f" - {d}: {results[d].get('error')}")
        if len(bad) > 20:
            print(f" ... and {len(bad) - 20} more")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parallel NVUE GET across many nodes")
    parser.add_argument("--devices-file", help="Path to device list (one per line)")
    parser.add_argument("--jsonl", default="results.jsonl", help="Write results as JSON lines")
    args = parser.parse_args()

    devices = load_devices_from_file(args.devices_file) if args.devices_file else DEVICES

    results = asyncio.run(run(devices))

    # Write JSONL for easy ingest/grep/ELK
    with open(args.jsonl, "w") as f:
        for device, result in results.items():
            f.write(json.dumps({"device": device, **result}) + "\n")

    summarize(results)