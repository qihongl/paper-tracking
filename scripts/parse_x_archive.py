#!/usr/bin/env python3
"""
Parse an X (Twitter) data archive export and extract paper-related tweets/retweets
for a computational cognitive neuroscience researcher.

Usage:
    python scripts/parse_x_archive.py [--input PATH] [--out DIR]

PATH may be:
  - the ZIP export,
  - the unzipped archive folder (searched recursively for tweets.js / tweets.csv),
  - or a single tweets.js / tweets.csv file.
Defaults: --input x-archive  --out outputs

Outputs (written to --out):
  - x-paper-posts.html      documented list of paper-related posts (mirrors bsky-paper-posts.html)
  - x-paper-posts.md        same content as markdown (easy reading)
  - x-wordcloud.png         word cloud of paper-post text
  - x-keywords-bar.png      top-N keyword frequency bar chart
  - x-keyword-suggestions.md  new tokens not already in the keyword matrix, grouped

The script also prints suggested additions to the keyword matrix (categories A-F).
"""

import argparse
import glob
import json
import os
import re
import shutil
import tempfile
import zipfile
from collections import Counter
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from wordcloud import WordCloud
    HAVE_WORDCLOUD = True
except Exception:
    HAVE_WORDCLOUD = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYWORD_MATRIX = os.path.join(PROJECT_ROOT, "prompts", "daily-paper-tracker.md")

# ---- science-oriented stopwords (extends the cleaned Bluesky set) ----
STOPWORDS = set("""
a about above after again against all am an and any are aren as at be because been before
being below between both but by can cannot could did do does doing down during each few for from
further had has have having he her here hers herself him his himself how i if in into is it its
itself just me more most my myself no nor not of off on once only or other ours ourselves out
over own same she should so some such than that the their theirs them themselves then there these
they this those through to too under until up very was we were what when where which while who whom
why with would you your yours yourself also new paper papers preprint preprints study studies research
article articles show shows shown showing find finds found result results using use used via based
approach approaches method methods model models modelling data analysis analyses https http www com
org net co rt t amp et al etc one two three first last fig figure figures table tables appendix e.g
i.e eg ie vs per see within between among both either neither whether while although because since
due given provide provides provided available support supports supported however therefore thus whether
tweet tweets retweet retweets thread threads via http https co t.co link links click read reading
today yesterday day days year years time times people work working think thought really great nice
good alert paperalert thanks thank please hello hi hey wow congrats congratulations excited happy
join zoom recording video slides talk talks poster present presentation invited keynote symposia
conference workshop seminar lab group team project collaborator friends friend colleague phd postdoc
prof professor university department school institute center centre cfa apply hiring position open
available job jobs hiring phdposition postdocposition faculty student students researchgate google
scholar pubmed pubmedcentral doi arxiv biorxiv psyarxiv pdf html github gitlab drive docs survey
review editorial commentary perspective opinion news note notes update updates out now live free open
access peer reviewed published publish publishing accept accepted reject rejected submission submit
""".split())

# Academic URL patterns = strong "this is a paper" signal
ACADEMIC_RE = re.compile(
    r"(arxiv\.org/(abs|pdf)|doi\.org|pubmed\.ncbi\.nlm\.nih\.gov|"
    r"biorxiv\.org|psyarxiv\.com|"
    r"(nature\.com|science\.org|cell\.com|pnas\.org|plos\.org|frontiersin\.org|"
    r"mdpi\.com|springer\.com|wiley\.com|sciencedirect\.com|link\.springer\.com|"
    r"tandfonline\.com|cambridge\.org|oxfordjournals\.org|annualreviews\.org|"
    r"sagepub\.com|ncbi\.nlm\.nih\.gov|neuroscience|jneurosci\.org|"
    r"sciencedirect|onlinelibrary|researchsquare|chemrxiv|osf\.io))",
    re.IGNORECASE,
)

PAPER_PHRASE_RE = re.compile(
    r"(new paper|our paper|preprint|just (published|out)|paper (on|about|finds|shows)|"
    r"study (shows|finds|reveals)|we found|out now|new study|new results|"
    r"https?://(arxiv|doi)|led by|with (my|our) (lab|group|coauthors))",
    re.IGNORECASE,
)

RT_RE = re.compile(r"^\s*RT\s+@\w+", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def find_tweet_files(input_path):
    """Return (list_of_js_files, list_of_csv_files) given a path."""
    js, csv = [], []
    if os.path.isfile(input_path):
        if input_path.endswith(".zip"):
            tmp = tempfile.mkdtemp()
            with zipfile.ZipFile(input_path) as z:
                z.extractall(tmp)
            input_path = tmp
        elif input_path.endswith(".js"):
            js = [input_path]
        elif input_path.endswith(".csv"):
            csv = [input_path]
    if os.path.isdir(input_path):
        js = sorted(glob.glob(os.path.join(input_path, "**", "tweets*.js"), recursive=True))
        csv = sorted(glob.glob(os.path.join(input_path, "**", "tweets*.csv"), recursive=True))
    return js, csv


def load_js(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    # strip a leading assignment like window.YTD.tweet.part0 =
    idx = text.find("[")
    if idx == -1:
        return []
    arr = json.loads(text[idx:])
    tweets = []
    for obj in arr:
        t = obj.get("tweet", obj) if isinstance(obj, dict) else obj
        tweets.append(t)
    return tweets


def load_csv(path):
    import csv
    rows = []
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def norm_tweet(raw):
    """Normalize a raw entry (from .js or .csv) into a dict."""
    if isinstance(raw, dict):
        created = raw.get("created_at", "")
        full = raw.get("full_text") or raw.get("text") or raw.get("content") or ""
        retweeted = bool(raw.get("retweeted")) or bool(raw.get("retweeted_status"))
        urls = []
        ents = raw.get("entities", {})
        for u in ents.get("urls", []) or []:
            exp = u.get("expanded_url") or u.get("url") or ""
            if exp:
                urls.append(exp)
        return {
            "created_at": created,
            "text": full,
            "retweeted": retweeted or bool(RT_RE.match(full)),
            "urls": urls,
        }
    return None


# ---------------------------------------------------------------------------
# Classification & extraction
# ---------------------------------------------------------------------------
def extract_urls(text):
    return re.findall(r"https?://[^\s]+", text)


def is_paper_post(post, matrix_kw):
    text = post["text"]
    urls = post["urls"] or extract_urls(text)
    raw = " ".join(urls)
    if ACADEMIC_RE.search(raw):
        return True
    if ACADEMIC_RE.search(text):
        return True
    if PAPER_PHRASE_RE.search(text):
        return True
    # matches an existing matrix keyword (paper they talk about w/o direct link)
    low = text.lower()
    for kw in matrix_kw:
        if " " in kw and kw in low:  # multiword only, to reduce false positives
            return True
    return False


def load_matrix_keywords():
    if not os.path.exists(KEYWORD_MATRIX):
        return []
    txt = open(KEYWORD_MATRIX, encoding="utf-8").read()
    kws = []
    # capture comma-separated lists under each "### X —" header up to next "###"
    blocks = re.split(r"\n### ", txt)
    for b in blocks[1:]:
        lines = b.splitlines()
        body = []
        for ln in lines[1:]:
            if ln.startswith("### "):
                break
            body.append(ln)
        flat = " ".join(body)
        for tok in flat.split(","):
            tok = tok.strip().lower()
            if tok and len(tok) > 2:
                kws.append(tok)
    return kws


def tokenize(text):
    toks = re.findall(r"[a-z][a-z0-9+#\-]{2,}", text.lower())
    return [t for t in toks if t not in STOPWORDS and not t.isdigit()]


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------
def render_html(posts, total_tweets, total_rt):
    rows = []
    for p in posts:
        badge = '<span class="rt">RT</span>' if p["retweeted"] else ""
        links = " ".join(
            f'<a href="{u}" target="_blank">{u}</a>' for u in p["urls"][:5]
        )
        date = p["date"]
        rows.append(
            f'<div class="post"><div class="meta">{date} {badge}</div>'
            f'<div class="text">{escape(p["text"])}</div>'
            f'<div class="links">{links}</div></div>'
        )
    sub = (f'@{HANDLE} — {len(posts)} paper-related posts of {total_tweets} total '
           f'(retweets: {total_rt}). Generated {datetime.now():%Y-%m-%d}.')
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>X Paper Posts — @{HANDLE}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
background:#f8f9fa;color:#1a1a1a;line-height:1.6;max-width:820px;margin:0 auto;padding:32px 20px}}
h1{{font-size:24px;font-weight:700;margin-bottom:4px}}
.sub{{color:#666;font-size:14px;margin-bottom:24px}}
.post{{background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:16px 18px;margin-bottom:12px;
box-shadow:0 1px 3px rgba(0,0,0,0.06)}}
.meta{{font-size:12px;color:#888;margin-bottom:6px}}
.rt{{display:inline-block;font-size:10px;font-weight:700;color:#fff;background:#10b981;
padding:1px 6px;border-radius:3px;margin-left:6px}}
.text{{font-size:14px;color:#222;white-space:pre-wrap;word-break:break-word}}
.links{{font-size:12px;margin-top:8px}}
.links a{{color:#1d4ed8;text-decoration:none;word-break:break-all}}
.links a:hover{{text-decoration:underline}}
</style></head><body>
<h1>🐦 X Paper Posts</h1>
<div class="sub">{sub}</div>
{''.join(rows)}
</body></html>"""


def escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_markdown(posts):
    out = [f"# X Paper Posts — @{HANDLE}\n", f"_{len(posts)} paper-related posts_\n"]
    for i, p in enumerate(posts, 1):
        kind = "RT" if p["retweeted"] else "tweet"
        out.append(f"### {i}. ({kind}) {p['date']}\n")
        out.append(p["text"].strip() + "\n")
        if p["urls"]:
            out.append("\nLinks:")
            for u in p["urls"][:5]:
                out.append(f"  - {u}")
            out.append("")
    return "\n".join(out)


def make_charts(tokens_all, out_dir):
    freq = Counter(tokens_all)
    top = freq.most_common(40)
    # bar chart
    if top:
        labels = [t for t, _ in top][::-1]
        counts = [c for _, c in top][::-1]
        fig, ax = plt.subplots(figsize=(8, 10))
        ax.barh(labels, counts, color="#3b82f6")
        ax.set_xlabel("frequency (paper posts)")
        ax.set_title(f"Top keywords in @{HANDLE} paper posts")
        ax.tick_params(labelsize=9)
        fig.tight_layout()
        bar_path = os.path.join(out_dir, "x-keywords-bar.png")
        fig.savefig(bar_path, dpi=130)
        plt.close(fig)
    else:
        bar_path = None
    # word cloud
    wc_path = None
    if HAVE_WORDCLOUD and tokens_all:
        wc = WordCloud(width=900, height=500, background_color="white",
                       max_words=150, colormap="viridis").generate(" ".join(tokens_all))
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        fig.tight_layout()
        wc_path = os.path.join(out_dir, "x-wordcloud.png")
        fig.savefig(wc_path, dpi=130)
        plt.close(fig)
    return bar_path, wc_path


def suggest_keywords(tokens_all, matrix_kw):
    freq = Counter(tokens_all)
    existing = set(matrix_kw)
    suggestions = []
    for tok, c in freq.most_common(200):
        if tok in existing:
            continue
        # also skip if it is a substring of an existing multiword kw or vice versa
        if any(tok in kw or kw in tok for kw in existing):
            continue
        suggestions.append((tok, c))
    return suggestions[:60]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
HANDLE = "Qihong_Lu"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(PROJECT_ROOT, "x-archive"))
    ap.add_argument("--out", default=os.path.join(PROJECT_ROOT, "outputs"))
    args = ap.parse_args()

    js_files, csv_files = find_tweet_files(args.input)
    if not js_files and not csv_files:
        print(f"[parse_x_archive] No tweets.js / tweets.csv found under: {args.input}")
        print("Drop your X export there (the unzipped archive, or the ZIP) and re-run.")
        return

    raws = []
    for f in js_files:
        raws.extend(load_js(f))
    for f in csv_files:
        raws.extend(load_csv(f))
    posts = [norm_tweet(r) for r in raws if r]
    posts = [p for p in posts if p and p.get("text")]

    print(f"[parse_x_archive] Loaded {len(posts)} total posts "
          f"(js={len(js_files)} csv={len(csv_files)}).")

    matrix_kw = load_matrix_keywords()
    paper_posts = [p for p in posts if is_paper_post(p, matrix_kw)]
    rt_count = sum(1 for p in paper_posts if p["retweeted"])

    # parse dates
    for p in paper_posts:
        c = p.get("created_at", "")
        try:
            dt = datetime.strptime(c[:19], "%Y-%m-%dT%H:%M:%S")
            p["date"] = dt.strftime("%Y-%m-%d")
        except Exception:
            p["date"] = c[:10] if c else "unknown"
    paper_posts.sort(key=lambda p: p["date"], reverse=True)

    os.makedirs(args.out, exist_ok=True)
    html = render_html(paper_posts, len(posts), rt_count)
    with open(os.path.join(args.out, "x-paper-posts.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(args.out, "x-paper-posts.md"), "w", encoding="utf-8") as f:
        f.write(render_markdown(paper_posts))

    # Tokenize tweet TEXT only for keyword analysis (URLs are used for
    # detection but their tokens are noise for the word cloud).
    # Strip URLs (incl. the t.co short links embedded in full_text) first.
    tokens_all = []
    for p in paper_posts:
        clean = re.sub(r"https?://\S+", " ", p["text"])
        tokens_all.extend(tokenize(clean))

    bar_path, wc_path = make_charts(tokens_all, args.out)
    suggestions = suggest_keywords(tokens_all, matrix_kw)

    sug_md = ["# Suggested keyword additions (not yet in the matrix)\n",
               f"_Top new tokens from @{HANDLE} paper posts (frequency in parentheses)_\n\n"]
    for tok, c in suggestions:
        sug_md.append(f"- {tok} ({c})")
    sug_md.append("")
    with open(os.path.join(args.out, "x-keyword-suggestions.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(sug_md))

    print(f"[parse_x_archive] Paper-related posts: {len(paper_posts)} "
          f"(retweets: {rt_count}).")
    print(f"[parse_x_archive] Wrote: x-paper-posts.html, x-paper-posts.md, "
          f"x-keyword-suggestions.md")
    if bar_path:
        print(f"[parse_x_archive] Wrote: x-keywords-bar.png")
    if wc_path:
        print(f"[parse_x_archive] Wrote: x-wordcloud.png")
    print("\nTop suggested new keywords:")
    for tok, c in suggestions[:30]:
        print(f"  {tok} ({c})")


if __name__ == "__main__":
    main()
