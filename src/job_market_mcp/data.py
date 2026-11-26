"""Read the published job-market CSVs from GitHub or a local data directory.

The dataset lives at https://github.com/Reaver1000/job-market-dashboard. Set
JOB_MARKET_DATA_DIR to point at a checkout's data/ folder and the server will
read local files instead of downloading. Downloaded files are cached for an
hour by default (JOB_MARKET_CACHE_TTL seconds).
"""
from __future__ import annotations

import csv
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/Reaver1000/job-market-dashboard/main/data"
CONTENTS_API = "https://api.github.com/repos/Reaver1000/job-market-dashboard/contents/data"
USER_AGENT = "job-market-mcp/0.1 (+https://github.com/Reaver1000/job-market-mcp)"


class DataUnavailable(RuntimeError):
    """Raised when the dataset cannot be read from disk or GitHub."""


def _data_dir(data_dir: str | Path | None = None) -> Path | None:
    value = data_dir or os.environ.get("JOB_MARKET_DATA_DIR")
    return Path(value).expanduser() if value else None


def _cache_dir() -> Path:
    value = os.environ.get("JOB_MARKET_CACHE_DIR")
    path = Path(value).expanduser() if value else Path.home() / ".cache" / "job-market-mcp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ttl_seconds() -> int:
    try:
        return int(os.environ.get("JOB_MARKET_CACHE_TTL", "3600"))
    except ValueError:
        return 3600


def _download(url: str, filename: str) -> Path:
    path = _cache_dir() / filename
    if path.exists() and time.time() - path.stat().st_mtime < _ttl_seconds():
        return path
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv, application/json"},
    )
    last_error = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
            path.write_bytes(payload)
            return path
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500 and exc.code != 429:
                raise DataUnavailable(
                    f"GitHub returned HTTP {exc.code} for {url}. "
                    "Set JOB_MARKET_DATA_DIR to a local job-market-dashboard/data folder."
                ) from exc
            last_error = exc
        except OSError as exc:
            last_error = exc
        time.sleep(2 * (attempt + 1))
    raise DataUnavailable(
        f"Could not download {url} after 4 attempts: {last_error}. "
        "Set JOB_MARKET_DATA_DIR to a local job-market-dashboard/data folder."
    )


def _read_csv(path: Path) -> list[dict]:
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        raise DataUnavailable(f"Could not read {path}: {exc}") from exc


_API_CACHE: dict = {"fetched": 0.0, "files": []}


def _contents() -> list[dict]:
    now = time.time()
    if _API_CACHE["files"] and now - _API_CACHE["fetched"] < 600:
        return _API_CACHE["files"]
    request = urllib.request.Request(
        CONTENTS_API,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
    else:
        raise DataUnavailable(
            "Could not list the dataset folder on GitHub. "
            "Set JOB_MARKET_DATA_DIR to a local job-market-dashboard/data folder."
        ) from last_error
    files = [
        {"name": item["name"], "download_url": item.get("download_url")}
        for item in payload
        if isinstance(item, dict) and item.get("name", "").endswith(".csv")
    ]
    _API_CACHE.update({"fetched": now, "files": files})
    return files


def load_latest(data_dir: str | Path | None = None) -> list[dict]:
    """Return the current live snapshot (latest.csv)."""
    local = _data_dir(data_dir)
    if local:
        path = local / "latest.csv"
        if not path.exists():
            raise DataUnavailable(f"Missing {path}")
        return _read_csv(path)
    return _read_csv(_download(f"{RAW_BASE}/latest.csv", "latest.csv"))


def load_history(data_dir: str | Path | None = None) -> list[dict]:
    """Return every posting ever observed, with first_seen and last_seen."""
    local = _data_dir(data_dir)
    if local:
        path = local / "history.csv"
        if not path.exists():
            raise DataUnavailable(f"Missing {path}")
        return _read_csv(path)
    return _read_csv(_download(f"{RAW_BASE}/history.csv", "history.csv"))


def latest_dated_file(prefix: str, data_dir: str | Path | None = None) -> tuple[str, list[dict]]:
    """Return the newest dated CSV whose name starts with prefix.

    Used for the junior and pay scans, which are written as
    junior_ads_YYYY-MM-DD.csv and pay_transparency_YYYY-MM-DD.csv.
    """
    local = _data_dir(data_dir)
    if local:
        files = sorted(local.glob(f"{prefix}_*.csv"))
        if not files:
            raise DataUnavailable(f"No {prefix}_*.csv files in {local}")
        path = files[-1]
        return path.name, _read_csv(path)

    matches = [
        item for item in _contents()
        if item["name"].startswith(f"{prefix}_") and item["name"].endswith(".csv")
    ]
    if not matches:
        raise DataUnavailable(f"No published files matching {prefix}_*.csv")
    item = sorted(matches, key=lambda entry: entry["name"])[-1]
    url = item.get("download_url") or f"{RAW_BASE}/{item['name']}"
    return item["name"], _read_csv(_download(url, item["name"]))


def clear_cache() -> None:
    """Delete downloaded CSVs. The next call will fetch fresh copies."""
    for path in _cache_dir().glob("*.csv"):
        path.unlink(missing_ok=True)
    _API_CACHE.update({"fetched": 0.0, "files": []})
