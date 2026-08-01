#!/usr/bin/env python3
"""Run-health diagnostic for the daily paper tracker.

Analyzes the git commit history, dedup store, and report files to detect
reliability issues that masquerade as coverage problems:
  - days without a report despite seen_papers activity
  - unusually long gaps between reports
  - repeated same-day runs (e.g. the 2026-07-23 'no new papers' cluster)

Writes outputs/run-health.md.
"""
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "outputs", "run-health.md")


def git_log():
    out = subprocess.run(
        ["git", "log", "--date=short", "--format=%ad|%s"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    return [line.split("|", 1) for line in out]


def main():
    log = git_log()
    report_days = defaultdict(list)
    for date, msg in log:
        if "Daily report" in msg or "paper-tracker" in msg:
            report_days[date].append(msg)

    seen = {}
    with open(os.path.join(REPO, "data", "seen_papers.json"), encoding="utf-8") as f:
        seen = json.load(f)
    seen_days = Counter(seen.values())

    lines = ["# Run-health report", "",
             f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} from git log, "
             "`data/seen_papers.json`, and `outputs/` report files.", ""]

    # report cadence
    dates = sorted(report_days)
    lines.append(f"## Cadence: {len(dates)} report days from {dates[0] if dates else '-'} to {dates[-1] if dates else '-'}")
    lines.append("")
    lines.append("| Date | Commits | Papers seen (dedup store) | Report file |")
    lines.append("|---|---|---|---|")
    import glob
    for d in dates:
        files = glob.glob(os.path.join(REPO, "outputs", f"{d}-paper-tracker.html"))
        n_files = len(files)
        lines.append(f"| {d} | {len(report_days[d])} | {seen_days.get(d, 0)} | {'yes' if n_files else 'NO FILE'} |")

    # gaps > 4 days
    lines.append("\n## Gaps between report days (>4 days)")
    gaps = []
    for a, b in zip(dates, dates[1:]):
        da, db = datetime.strptime(a, "%Y-%m-%d"), datetime.strptime(b, "%Y-%m-%d")
        gap = (db - da).days
        if gap > 4:
            gaps.append((a, b, gap))
            lines.append(f"- {a} -> {b}: **{gap} days**")
    if not gaps:
        lines.append("- none")

    # same-day multiple runs
    lines.append("\n## Same-day multiple runs")
    multi = {d: msgs for d, msgs in report_days.items() if len(msgs) > 1}
    if multi:
        for d, msgs in sorted(multi.items()):
            lines.append(f"- **{d}**: {len(msgs)} commits")
            for m in msgs[:8]:
                lines.append(f"  - {m}")
        lines.append("\n> Interpretation: repeated same-day runs usually mean the daily agent retried "
                     "(search failures, push conflicts) or the harness double-fired. The 2026-07-23 "
                     "cluster (Run #21-25) ended with a merged +1 paper, so the final state is consistent; "
                     "retries wasted tokens but did not corrupt the store. If this repeats, add a lock/"
                     "last-run marker to the daily prompt.")
    else:
        lines.append("- none")

    # seen_papers entries dated on days with NO report commit
    lines.append("\n## Dedup-store dates without a report commit")
    no_report = [(d, c) for d, c in sorted(seen_days.items()) if d not in report_days]
    if no_report:
        for d, c in no_report[:10]:
            lines.append(f"- {d}: {c} paper(s) marked seen, but no report commit that day")
    else:
        lines.append("- none")

    # store health
    lines.append("\n## Dedup store health")
    lines.append(f"- entries: {len(seen)}")
    lines.append(f"- arXiv DOIs: {sum(1 for k in seen if 'arXiv' in k)} | bioRxiv (10.1101): "
                 f"{sum(1 for k in seen if k.startswith('10.1101'))} | bioRxiv (10.64898): "
                 f"{sum(1 for k in seen if k.startswith('10.64898'))} | title slugs: "
                 f"{sum(1 for k in seen if '10.' not in k)}")
    # near-duplicate slugs
    slugs = [k for k in seen if "10." not in k]
    dupes = []
    seen_l = set()
    for s in slugs:
        key = re.sub(r"[^a-z0-9]", "", s)[:40]
        if key in seen_l:
            dupes.append(s)
        seen_l.add(key)
    lines.append(f"- potential near-duplicate title slugs: {len(dupes)}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"run-health report -> {OUT}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
