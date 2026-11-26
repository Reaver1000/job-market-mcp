import csv

from job_market_mcp import data


def write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_local_latest_and_history(tmp_path, monkeypatch):
    write_csv(
        tmp_path / "latest.csv",
        ["title", "company", "location", "remote", "posted", "source", "url"],
        [{"title": "Analyst", "company": "Acme", "location": "Remote", "remote": "1",
          "posted": "2026-11-26", "source": "ats", "url": "https://example.com/1"}],
    )
    write_csv(
        tmp_path / "history.csv",
        ["title", "company", "location", "remote", "posted", "source", "url", "first_seen", "last_seen"],
        [{"title": "Analyst", "company": "Acme", "location": "Remote", "remote": "1",
          "posted": "2026-11-26", "source": "ats", "url": "https://example.com/1",
          "first_seen": "2026-11-26", "last_seen": "2026-11-26"}],
    )
    monkeypatch.setenv("JOB_MARKET_DATA_DIR", str(tmp_path))
    assert data.load_latest()[0]["company"] == "Acme"
    assert data.load_history()[0]["first_seen"] == "2026-11-26"


def test_latest_dated_file_uses_newest_name(tmp_path, monkeypatch):
    for day in ("2026-11-25", "2026-11-26"):
        write_csv(
            tmp_path / f"junior_ads_{day}.csv",
            ["title", "bucket", "years_required", "skills"],
            [{"title": day, "bucket": "no stated bar", "years_required": "", "skills": "python"}],
        )
    monkeypatch.setenv("JOB_MARKET_DATA_DIR", str(tmp_path))
    name, rows = data.latest_dated_file("junior_ads")
    assert name == "junior_ads_2026-11-26.csv"
    assert rows[0]["title"] == "2026-11-26"
