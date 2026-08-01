# Run-health report

Generated 2026-08-01 22:37 from git log, `data/seen_papers.json`, and `outputs/` report files.

## Cadence: 15 report days from 2026-07-10 to 2026-07-31

| Date | Commits | Papers seen (dedup store) | Report file |
|---|---|---|---|
| 2026-07-10 | 1 | 9 | yes |
| 2026-07-11 | 2 | 11 | yes |
| 2026-07-13 | 1 | 18 | yes |
| 2026-07-14 | 1 | 10 | yes |
| 2026-07-15 | 1 | 0 | NO FILE |
| 2026-07-16 | 1 | 21 | yes |
| 2026-07-17 | 1 | 9 | yes |
| 2026-07-18 | 1 | 11 | yes |
| 2026-07-19 | 1 | 12 | yes |
| 2026-07-20 | 1 | 0 | NO FILE |
| 2026-07-22 | 1 | 11 | yes |
| 2026-07-23 | 8 | 12 | yes |
| 2026-07-25 | 1 | 6 | yes |
| 2026-07-27 | 1 | 6 | yes |
| 2026-07-31 | 1 | 7 | yes |

## Gaps between report days (>4 days)
- none

## Same-day multiple runs
- **2026-07-11**: 2 commits
  - Daily report: 2026-07-11
  - Daily report: 2026-07-10
- **2026-07-23**: 8 commits
  - Daily report: 2026-07-23 (Run #25 — no new papers)
  - Daily report: 2026-07-23 (Run #24 — no new papers)
  - Daily report: 2026-07-23 (Run #23 — no new papers)
  - Daily report: 2026-07-23 (Run #22 — no new papers)
  - Daily report: 2026-07-23 (Run #21, merged +1 Science CA3 dendrite)
  - Daily report: 2026-07-23 (merged hourly re-run, 11 papers)
  - Daily report: 2026-07-23
  - Daily report: 2026-07-22

> Interpretation: repeated same-day runs usually mean the daily agent retried (search failures, push conflicts) or the harness double-fired. The 2026-07-23 cluster (Run #21-25) ended with a merged +1 paper, so the final state is consistent; retries wasted tokens but did not corrupt the store. If this repeats, add a lock/last-run marker to the daily prompt.

## Dedup-store dates without a report commit
- 2026-07-04: 7 paper(s) marked seen, but no report commit that day
- 2026-07-08: 9 paper(s) marked seen, but no report commit that day
- 2026-07-09: 7 paper(s) marked seen, but no report commit that day
- 2026-07-21: 11 paper(s) marked seen, but no report commit that day

## Dedup store health
- entries: 177
- arXiv DOIs: 112 | bioRxiv (10.1101): 4 | bioRxiv (10.64898): 14 | title slugs: 2
- potential near-duplicate title slugs: 0
