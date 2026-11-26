from datetime import date

from job_market_mcp import analytics


LATEST = [
    {
        "title": "Implementation Consultant",
        "company": "Acme",
        "location": "Remote - Germany",
        "remote": "1",
        "posted": "2026-11-25",
        "source": "ats_ashby",
        "url": "https://example.com/1",
    },
    {
        "title": "Junior Data Analyst",
        "company": "Beta",
        "location": "Remote - UK",
        "remote": "1",
        "posted": "2026-09-01",
        "source": "linkedin_uk",
        "url": "https://example.com/2",
    },
    {
        "title": "Warehouse Operative",
        "company": "Gamma",
        "location": "Erfurt",
        "remote": "0",
        "posted": "2026-11-20",
        "source": "ba",
        "url": "https://example.com/3",
    },
    {
        "title": "Support Engineer",
        "company": "Acme",
        "location": "Remote - Europe",
        "remote": "1",
        "posted": "",
        "source": "freehire",
        "url": "https://example.com/4",
    },
]

HISTORY = [
    {
        "title": "Implementation Consultant",
        "company": "Acme",
        "location": "Remote - Germany",
        "remote": "1",
        "posted": "posted: 2026-11-25",
        "source": "ats_ashby",
        "url": "https://example.com/1",
        "first_seen": "2026-11-25",
        "last_seen": "2026-11-26",
    },
    {
        "title": "Support Engineer",
        "company": "Acme",
        "location": "Remote - Europe",
        "remote": "1",
        "posted": "",
        "source": "freehire",
        "url": "https://example.com/4",
        "first_seen": "2026-11-20",
        "last_seen": "2026-11-22",
    },
    {
        "title": "Junior Data Analyst",
        "company": "Beta",
        "location": "Remote - UK",
        "remote": "1",
        "posted": "posted: 2026-09-01",
        "source": "linkedin_uk",
        "url": "https://example.com/2",
        "first_seen": "2026-11-21",
        "last_seen": "2026-11-26",
    },
]


def test_parse_date_accepts_prefixed_values():
    assert analytics.parse_date("posted: 2026-11-10") == date(2026, 11, 10)
    assert analytics.parse_date("") is None


def test_summary_counts_and_shares():
    result = analytics.summary(LATEST, as_of="2026-11-26")
    assert result["total_postings"] == 4
    assert result["remote_postings"] == 3
    assert result["dated_postings"] == 3
    assert result["dated_coverage_pct"] == 75.0
    assert result["stale_60_plus"] == 1
    assert result["top_companies"][0]["company"] == "Acme"


def test_search_is_newest_first_and_respects_remote_flag():
    results = analytics.search_jobs(LATEST, "data", remote_only=True)
    assert [row["title"] for row in results] == ["Junior Data Analyst"]
    all_results = analytics.search_jobs(LATEST, "acme", remote_only=False)
    assert len(all_results) == 2
    germany = analytics.search_jobs(LATEST, "consultant", location="Germany")
    assert [row["title"] for row in germany] == ["Implementation Consultant"]


def test_ghost_jobs_returns_age():
    results = analytics.ghost_jobs(LATEST, min_age_days=60, as_of="2026-11-26")
    assert len(results) == 1
    assert results[0]["company"] == "Beta"
    assert results[0]["age_days"] > 60


def test_company_profile_uses_history():
    result = analytics.company_profile(HISTORY, "acme")
    assert result["found"] is True
    assert result["postings"] == 2
    assert result["unique_titles"] == 2
    assert result["first_seen"] == "2026-11-20"
    assert result["last_seen"] == "2026-11-26"


def test_snapshot_as_of_uses_first_and_last_seen():
    rows = analytics.snapshot_as_of(HISTORY, "2026-11-21")
    assert len(rows) == 2
    rows = analytics.snapshot_as_of(HISTORY, "2026-11-23")
    assert len(rows) == 1


def test_junior_summary_counts_buckets_and_skills():
    rows = [
        {"title": "Junior Analyst", "bucket": "actually junior (0-2y)", "years_required": "2", "skills": "python|excel"},
        {"title": "Junior Support", "bucket": "no stated bar", "years_required": "", "skills": "python"},
    ]
    result = analytics.junior_summary(rows)
    assert result["total_ads"] == 2
    assert result["top_skills"][0] == {"skill": "python", "ads": 2}
    assert any(item["bucket"] == "no stated bar" for item in result["buckets"])


def test_pay_summary_compares_junior_and_senior_disclosure():
    rows = [
        {"title": "Junior", "bucket": "no pay signal", "junior": "1", "senior": "0"},
        {"title": "Junior 2", "bucket": "dodge only", "junior": "1", "senior": "0"},
        {"title": "Senior", "bucket": "pay disclosed", "junior": "0", "senior": "1", "structured_pay": "EUR 80,000"},
    ]
    result = analytics.pay_summary(rows)
    assert result["disclosed_share_pct"] == 33.3
    assert result["junior_disclosed_share_pct"] == 0.0
    assert result["senior_disclosed_share_pct"] == 100.0
