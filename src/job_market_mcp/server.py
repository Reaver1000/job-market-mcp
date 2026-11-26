"""MCP server exposing the daily job-market dataset as a small set of tools."""
from __future__ import annotations

import json
import sys

from mcp.server.mcpserver import MCPServer

from . import analytics, data

mcp = MCPServer(
    "job-market",
    title="Job Market Data",
    description="Query a daily snapshot of public job postings and the history behind it.",
    instructions=(
        "Use these tools for questions about the live job market, remote share, "
        "stale postings, company hiring activity, junior requirements and pay "
        "transparency. Always report the numbers with their snapshot date and "
        "mention when a figure is a share of dated postings rather than all rows."
    ),
)


@mcp.tool()
def dataset_info() -> dict:
    """Return the dataset sources, column meanings and known limitations."""
    return {
        "name": "Job Market Daily",
        "snapshot": "latest.csv",
        "history": "history.csv",
        "data_repo": "https://github.com/Reaver1000/job-market-dashboard",
        "dataset": "https://huggingface.co/datasets/Reaver1000/job-market-daily",
        "kaggle": "https://www.kaggle.com/datasets/davidbuchan1000/job-market-daily",
        "dashboard": "https://reaver1000-job-market-dashboard.static.hf.space",
        "columns": {
            "title": "posting title",
            "company": "hiring company or board slug",
            "location": "location text from the source",
            "remote": "1 when the location or title signals remote work, else 0",
            "posted": "posting date where the source provided one",
            "source": "collecting lane, such as ats_greenhouse or linkedin_de",
            "url": "original posting URL",
            "first_seen": "first sweep date in history.csv",
            "last_seen": "most recent sweep date in history.csv",
        },
        "caveats": [
            "Not a representative sample of the whole labour market. It is the view of one pipeline over public boards.",
            "The remote flag is text-based. LinkedIn's guest API ignores its remote filter, so LinkedIn lanes undercount remote roles.",
            "Some postings have no posted date. Where a date is missing the row stays blank rather than being filled.",
            "Greenhouse reports updated_at rather than first-published date, so a few dormant postings carry old dates.",
            "Deduplication is by URL. The same role can appear once per board if the boards use different URLs.",
        ],
    }


@mcp.tool()
def market_summary(as_of: str | None = None) -> dict:
    """Summarise live postings, remote share, sources, stale ads and top companies.

    Pass an ISO date such as 2026-11-25 to reconstruct that day from history.csv.
    Without a date the current latest.csv is used.
    """
    if as_of:
        rows = analytics.snapshot_as_of(data.load_history(), as_of)
        return analytics.summary(rows, as_of=as_of, source=f"history.csv reconstructed for {as_of}")
    return analytics.summary(data.load_latest(), source="latest.csv")


@mcp.tool()
def search_jobs(
    query: str,
    remote_only: bool = True,
    limit: int = 20,
    location: str | None = None,
) -> dict:
    """Search live postings by keyword across title, company and location.

    Use short phrases such as "implementation consultant" or "junior data".
    Results are newest first. Set remote_only to false to include every row.
    Pass location, for example "Germany" or "United Kingdom", to narrow the
    results without relying on the posting's remote flag alone.
    """
    jobs = analytics.search_jobs(
        data.load_latest(),
        query,
        remote_only=remote_only,
        limit=limit,
        location=location,
    )
    return {"query": query, "count": len(jobs), "jobs": jobs}


@mcp.tool()
def ghost_jobs(
    min_age_days: int = 60,
    as_of: str | None = None,
    remote_only: bool = False,
    limit: int = 20,
) -> dict:
    """Find live postings older than min_age_days, oldest first.

    This is the stale or ghost-job view. Pass an ISO as_of date to age the
    postings against a historical snapshot instead of today.
    """
    jobs = analytics.ghost_jobs(
        data.load_latest(),
        min_age_days=min_age_days,
        as_of=as_of,
        remote_only=remote_only,
        limit=limit,
    )
    return {"min_age_days": min_age_days, "count": len(jobs), "jobs": jobs}


@mcp.tool()
def company_profile(company: str) -> dict:
    """Profile a company across every posting ever observed in history.csv.

    Returns posting count, first and last seen dates, remote share, sources and
    the most common titles. The match is a case-insensitive substring.
    """
    return analytics.company_profile(data.load_history(), company)


@mcp.tool()
def top_hiring_companies(limit: int = 15, remote_only: bool = True) -> dict:
    """Rank companies by the number of live postings in latest.csv."""
    companies = analytics.top_companies(
        data.load_latest(),
        limit=limit,
        remote_only=remote_only,
    )
    return {"remote_only": remote_only, "count": len(companies), "companies": companies}


@mcp.tool()
def junior_market() -> dict:
    """Summarise the junior-titled ATS scan: experience bars, buckets and skills.

    Reads the newest junior_ads_YYYY-MM-DD.csv. The scan covers ATS boards, not
    every source in the main snapshot.
    """
    _, rows = data.latest_dated_file("junior_ads")
    return analytics.junior_summary(rows)


@mcp.tool()
def pay_transparency() -> dict:
    """Summarise salary disclosure in the newest pay_transparency scan.

    Reports the split between disclosed pay, dodge phrases and no signal, plus
    the junior and senior disclosure rates.
    """
    _, rows = data.latest_dated_file("pay_transparency")
    return analytics.pay_summary(rows)


def main() -> None:
    if "--selftest" in sys.argv:
        print(json.dumps(market_summary(), indent=2)[:4000])
        return
    mcp.run()


if __name__ == "__main__":
    main()
