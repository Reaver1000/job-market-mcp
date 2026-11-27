---
name: job-market-analyst
description: Query a daily snapshot of public job postings (about 20,000 live ads from 82 sources) to answer questions about remote share, stale or ghost jobs, company hiring activity, junior experience bars, and pay transparency. Use when the user asks about the job market, hiring trends, remote roles, a company's postings, or salary disclosure.
---

# Job Market Analyst

Use the `job-market` MCP server for questions that need numbers from the live
dataset. The data is published daily from my own job-discovery pipeline.

## Tools

- `market_summary` returns totals, remote share, sources, stale ads and top companies. Pass an ISO date to reconstruct that day from `history.csv`.
- `search_jobs` searches live postings by keyword across title, company and location.
- `ghost_jobs` returns postings older than a threshold, oldest first.
- `company_profile` returns a company's posting history, first and last seen dates, remote share and common titles.
- `top_hiring_companies` ranks companies by live postings.
- `junior_market` summarises the junior-titled ATS scan, including experience bars and named skills.
- `pay_transparency` summarises salary disclosure and the junior versus senior gap.
- `dataset_info` returns sources, column meanings and caveats.

## Rules

1. State the snapshot date with every headline number.
2. The `remote` flag is text-based. LinkedIn's guest API ignores its remote filter, so LinkedIn lanes undercount remote roles. Say so when the answer depends on remote share.
3. Some postings have no posted date. Percentages of dated postings are not percentages of all rows.
4. This is not a representative sample of the whole labour market. It is one pipeline's view of public boards.
5. The query pack changed on 27 November 2026 to focus on mid-level and junior operations, implementation, solutions, support and data roles. Counts before and after that date are not directly comparable.
6. Quote the original posting URL when naming a specific role.
7. Prefer `search_jobs` over guessing. If a query returns nothing, say so and suggest a broader keyword.

## Good questions

- How many live postings are there, and what share is remote?
- Which companies are hiring the most right now?
- Find junior data roles that actually say remote.
- Show me the oldest live postings.
- What experience bar do junior-titled ads actually state?
- How often is pay disclosed for junior versus senior roles?
- What has this company posted over the last month?

## Setup

The server needs either network access to the public GitHub dataset or a local
checkout. Set `JOB_MARKET_DATA_DIR` to the `data/` folder of
`job-market-dashboard` to read local files. See `README.md` for the client
configuration.
