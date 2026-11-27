# Job Market MCP

![tests](https://github.com/Reaver1000/job-market-mcp/actions/workflows/ci.yml/badge.svg)

A Claude skill and MCP server over my daily snapshot of public job postings.
On 27 November 2026 the snapshot held **20,067 live postings from 69 sources**.
The same data powers my [dashboard](https://reaver1000-job-market-dashboard.static.hf.space),
the [Hugging Face dataset](https://huggingface.co/datasets/Reaver1000/job-market-daily)
and the [Remote, Not America](https://remotenotamerica.substack.com) newsletter.

Most job-market answers are anecdotes. This gives Claude the rows, the history
and the caveats, so it can answer with counts instead of vibes.

## What it can answer

- How many live postings are there, and what share is remote?
- Which companies have the most live postings?
- Find implementation, solutions or support roles in a given location.
- Which live ads are more than 60 days old?
- What experience bar do junior-titled ads actually state?
- How often is pay disclosed for junior versus senior roles?
- Reconstruct the market as it looked on a previous sweep date.

## Tools

| Tool | Returns |
|---|---|
| `dataset_info` | Sources, column meanings and known limitations |
| `market_summary` | Totals, remote share, sources, stale ads and top companies. Accepts an optional ISO date for a historical snapshot |
| `search_jobs` | Keyword search over title, company and location, newest first |
| `ghost_jobs` | Live postings older than a threshold, oldest first |
| `company_profile` | Posting history, first and last seen dates, remote share and common titles |
| `top_hiring_companies` | Companies ranked by live postings |
| `junior_market` | Experience bars, buckets and named skills from the junior ATS scan |
| `pay_transparency` | Salary disclosure split, plus the junior and senior gap |

## Quick start

```bash
git clone https://github.com/Reaver1000/job-market-mcp.git
cd job-market-mcp
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS and Linux
pip install -e ".[dev]"
job-market-mcp --selftest
```

`--selftest` downloads the current snapshot and prints a market summary. Set
`JOB_MARKET_DATA_DIR` to a local `job-market-dashboard/data` folder to avoid the
download:

```powershell
$env:JOB_MARKET_DATA_DIR="C:\Users\you\source\repos\job-market-dashboard\data"
job-market-mcp --selftest
```

## Connect it to Claude

For Claude Desktop, copy `claude_desktop_config.example.json` into your Claude
Desktop configuration and adjust the paths. The short version:

```json
{
  "mcpServers": {
    "job-market": {
      "command": "job-market-mcp",
      "env": {
        "JOB_MARKET_DATA_DIR": "C:/Users/you/source/repos/job-market-dashboard/data"
      }
    }
  }
}
```

For Claude Code, copy `.mcp.json.example` to `.mcp.json` in the project where you
want the server available.

To use it as a Claude skill, put this folder where your client loads skills. In
Claude Code that is `~/.claude/skills/job-market-analyst/`. The `SKILL.md` file
tells Claude when to use the server and which caveats to repeat.

## Example

Prompt:

> How many live postings are there, and how many are older than 60 days?

`market_summary` at the 27 November 2026 snapshot returned:

```json
{
  "as_of": "2026-11-27",
  "total_postings": 20067,
  "remote_postings": 3272,
  "remote_share_pct": 16.3,
  "sources": 69,
  "dated_coverage_pct": 100.0,
  "stale_60_plus": 4457,
  "stale_60_plus_share_pct": 22.2
}
```

Prompt:

> Which skills show up most often in junior-titled ads?

`junior_market` returned Python in 28 of 124 ads, Excel in 27, Linux in 23, and
106 of the 124 ads stated no experience bar at all.

## Data

The data lives in
[Reaver1000/job-market-dashboard](https://github.com/Reaver1000/job-market-dashboard):

- `data/latest.csv` is the current snapshot, one row per posting, deduplicated by URL.
- `data/history.csv` is every posting ever observed, with `first_seen` and `last_seen` sweep dates.
- `data/junior_ads_YYYY-MM-DD.csv` is the junior-titled ATS scan with parsed experience bars and skills.
- `data/pay_transparency_YYYY-MM-DD.csv` is the salary disclosure scan.

Known limitations, also returned by `dataset_info`:

- This is not a representative sample of the whole labour market. It is one pipeline's view of public boards.
- The sweep query pack changed on 27 November 2026 to focus on mid-level and junior operations, implementation, solutions, support and data roles. Counts before and after that date are not directly comparable.
- The `remote` flag is text-based. LinkedIn's guest API ignores its remote filter, so LinkedIn lanes undercount remote roles.
- Some postings have no posted date. Where a date is missing the row stays blank rather than being filled.
- Greenhouse reports `updated_at` rather than first-published date, so a few dormant postings carry old dates.
- Deduplication is by URL. The same role can appear once per board if the boards use different URLs.

The server downloads `latest.csv` and `history.csv` from GitHub and caches them
for an hour. `JOB_MARKET_CACHE_DIR` changes the cache location and
`JOB_MARKET_CACHE_TTL` changes the lifetime in seconds.

## Tests

```bash
pytest
python scripts/smoke_mcp.py
```

The pytest suite covers the analytics functions and the local data loader. It
does not need a network connection. The smoke script spawns the server over
stdio and calls two tools through the real MCP protocol, which does download
the current snapshot unless `JOB_MARKET_DATA_DIR` is set.

## License

MIT. See `LICENSE`.
