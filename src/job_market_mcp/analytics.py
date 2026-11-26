"""Pure query helpers over the job-market rows.

Everything here takes a list of dicts and returns plain dictionaries, so the
functions are easy to test without a network or an MCP client.
"""
from __future__ import annotations

import html
import re
from collections import Counter
from datetime import date
from typing import Iterable

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def parse_date(value) -> date | None:
    """Accept dates, ISO strings and the 'posted: YYYY-MM-DD' form in history.csv."""
    if isinstance(value, date):
        return value
    match = DATE_RE.search(str(value or ""))
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def clean_text(value) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def is_remote(row: dict) -> bool:
    return str(row.get("remote", "")).strip().lower() in {"1", "true", "yes"}


def _flag(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _limit(value, default: int = 20, maximum: int = 100) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(number, maximum))


def _company_key(name) -> str:
    return clean_text(name).casefold()


def top_companies(rows: Iterable[dict], limit: int = 15, remote_only: bool = False) -> list[dict]:
    counts: Counter = Counter()
    display: dict[str, str] = {}
    for row in rows:
        if remote_only and not is_remote(row):
            continue
        key = _company_key(row.get("company"))
        if not key:
            continue
        counts[key] += 1
        display.setdefault(key, clean_text(row.get("company")))
    return [
        {"company": display[key], "postings": count}
        for key, count in counts.most_common(_limit(limit, 15, 100))
    ]


def _posting(row: dict) -> dict:
    posted = parse_date(row.get("posted"))
    return {
        "title": clean_text(row.get("title")),
        "company": clean_text(row.get("company")),
        "location": clean_text(row.get("location")),
        "remote": is_remote(row),
        "posted": posted.isoformat() if posted else "",
        "source": clean_text(row.get("source")),
        "url": clean_text(row.get("url")),
    }


def summary(rows: list[dict], as_of=None, source: str = "latest.csv") -> dict:
    as_of_date = parse_date(as_of) or date.today()
    total = len(rows)
    remote = sum(1 for row in rows if is_remote(row))
    posted = [day for day in (parse_date(row.get("posted")) for row in rows) if day]
    stale = sum(1 for day in posted if (as_of_date - day).days >= 60)
    sources = Counter(clean_text(row.get("source")) for row in rows if clean_text(row.get("source")))
    return {
        "as_of": as_of_date.isoformat(),
        "source": source,
        "total_postings": total,
        "remote_postings": remote,
        "remote_share_pct": round(100 * remote / total, 1) if total else 0.0,
        "sources": len(sources),
        "top_sources": [{"source": key, "postings": value} for key, value in sources.most_common(8)],
        "dated_postings": len(posted),
        "dated_coverage_pct": round(100 * len(posted) / total, 1) if total else 0.0,
        "oldest_posted": min(posted).isoformat() if posted else "",
        "newest_posted": max(posted).isoformat() if posted else "",
        "stale_60_plus": stale,
        "stale_60_plus_share_pct": round(100 * stale / len(posted), 1) if posted else 0.0,
        "top_companies": top_companies(rows, 10),
    }


def search_jobs(
    rows: list[dict],
    query: str,
    remote_only: bool = True,
    limit: int = 20,
    location: str | None = None,
) -> list[dict]:
    needle = clean_text(query).casefold()
    if not needle:
        raise ValueError("query must not be empty")
    place = clean_text(location).casefold() if location else ""
    matches = []
    for row in rows:
        if remote_only and not is_remote(row):
            continue
        if place and place not in clean_text(row.get("location")).casefold():
            continue
        haystack = " ".join(
            clean_text(row.get(key)) for key in ("title", "company", "location")
        ).casefold()
        if needle in haystack:
            matches.append(row)
    matches.sort(
        key=lambda row: (
            parse_date(row.get("posted")) or date.min,
            clean_text(row.get("title")).casefold(),
        ),
        reverse=True,
    )
    return [_posting(row) for row in matches[: _limit(limit)]]


def ghost_jobs(
    rows: list[dict],
    min_age_days: int = 60,
    as_of=None,
    remote_only: bool = False,
    limit: int = 20,
) -> list[dict]:
    as_of_date = parse_date(as_of) or date.today()
    matches = []
    for row in rows:
        if remote_only and not is_remote(row):
            continue
        posted = parse_date(row.get("posted"))
        if not posted:
            continue
        age = (as_of_date - posted).days
        if age >= int(min_age_days):
            item = _posting(row)
            item["age_days"] = age
            matches.append(item)
    matches.sort(key=lambda item: item["age_days"], reverse=True)
    return matches[: _limit(limit)]


def company_profile(history: list[dict], company: str) -> dict:
    needle = clean_text(company).casefold()
    if not needle:
        raise ValueError("company must not be empty")
    rows = [row for row in history if needle in clean_text(row.get("company")).casefold()]
    if not rows:
        return {"company": company, "found": False, "postings": 0}
    titles = Counter(clean_text(row.get("title")) for row in rows if clean_text(row.get("title")))
    sources = Counter(clean_text(row.get("source")) for row in rows if clean_text(row.get("source")))
    first_seen = [day for day in (parse_date(row.get("first_seen")) for row in rows) if day]
    last_seen = [day for day in (parse_date(row.get("last_seen")) for row in rows) if day]
    remote = sum(1 for row in rows if is_remote(row))
    return {
        "company": clean_text(rows[0].get("company")),
        "found": True,
        "postings": len(rows),
        "unique_titles": len(titles),
        "first_seen": min(first_seen).isoformat() if first_seen else "",
        "last_seen": max(last_seen).isoformat() if last_seen else "",
        "remote_share_pct": round(100 * remote / len(rows), 1),
        "sources": [{"source": key, "postings": value} for key, value in sources.most_common(6)],
        "top_titles": [{"title": key, "postings": value} for key, value in titles.most_common(10)],
    }


def junior_summary(rows: list[dict]) -> dict:
    total = len(rows)
    buckets = Counter(clean_text(row.get("bucket")) or "unknown" for row in rows)
    years = Counter(clean_text(row.get("years_required")) or "not stated" for row in rows)
    skills: Counter = Counter()
    for row in rows:
        for skill in clean_text(row.get("skills")).split("|"):
            skill = skill.strip().casefold()
            if skill:
                skills[skill] += 1
    samples = []
    for row in rows[:10]:
        item = _posting(row)
        item["years_required"] = clean_text(row.get("years_required")) or "not stated"
        item["bucket"] = clean_text(row.get("bucket"))
        samples.append(item)
    return {
        "total_ads": total,
        "buckets": [{"bucket": key, "ads": value} for key, value in buckets.most_common()],
        "years_required": [{"years": key, "ads": value} for key, value in years.most_common()],
        "top_skills": [{"skill": key, "ads": value} for key, value in skills.most_common(12)],
        "sample": samples,
    }


def pay_summary(rows: list[dict]) -> dict:
    total = len(rows)
    buckets = Counter(clean_text(row.get("bucket")) or "unknown" for row in rows)
    disclosed = buckets.get("pay disclosed", 0)
    junior = [row for row in rows if _flag(row.get("junior"))]
    senior = [row for row in rows if _flag(row.get("senior"))]
    junior_disclosed = sum(1 for row in junior if clean_text(row.get("bucket")) == "pay disclosed")
    senior_disclosed = sum(1 for row in senior if clean_text(row.get("bucket")) == "pay disclosed")
    samples = []
    for row in rows:
        if clean_text(row.get("bucket")) != "pay disclosed":
            continue
        item = _posting(row)
        item["pay"] = clean_text(row.get("structured_pay")) or clean_text(row.get("pay_texts"))
        samples.append(item)
        if len(samples) >= 10:
            break
    return {
        "total_ads": total,
        "buckets": [{"bucket": key, "ads": value} for key, value in buckets.most_common()],
        "disclosed": disclosed,
        "disclosed_share_pct": round(100 * disclosed / total, 1) if total else 0.0,
        "junior_ads": len(junior),
        "junior_disclosed_share_pct": round(100 * junior_disclosed / len(junior), 1) if junior else 0.0,
        "senior_ads": len(senior),
        "senior_disclosed_share_pct": round(100 * senior_disclosed / len(senior), 1) if senior else 0.0,
        "sample_disclosed": samples,
    }


def snapshot_as_of(history: list[dict], as_of) -> list[dict]:
    """Reconstruct a live snapshot from history.csv for a given date."""
    target = parse_date(as_of)
    if not target:
        raise ValueError("as_of must contain an ISO date")
    rows = []
    for row in history:
        first = parse_date(row.get("first_seen"))
        last = parse_date(row.get("last_seen"))
        if first and last and first <= target <= last:
            rows.append(row)
    return rows
