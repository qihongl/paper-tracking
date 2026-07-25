#!/usr/bin/env python3
"""
Unify X (Twitter) archive + Bluesky posts into ONE canonical format, then
recompute topics / categories for the paper tracker.

Pipeline:
  1. normalize_x()   -> data/raw/x_posts.json      (from x-archive/data/tweets.js)
  2. fetch_bsky()     -> data/raw/bsky_posts.json   (from public Bluesky API)
  3. merge            -> data/posts_normalized.json  (the unified "same format" file)
  4. analyze          -> outputs/paper-posts-unified.html
                         outputs/wordcloud-unified.png
                         outputs/keywords-bar-unified.png
                         outputs/category-breakdown.md
                         outputs/keyword-suggestions.md

Canonical record schema (identical for both platforms):
  {platform, id, author, original_author, is_share, created_at,
   text, urls[], lang, engagement{likes,shares,replies}, source}

Run:  python scripts/social_unify.py
"""

import glob
import html
import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from wordcloud import WordCloud
    HAVE_WORDCLOUD = True
except Exception:
    HAVE_WORDCLOUD = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X_ARCHIVE = os.path.join(ROOT, "x-archive")
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "outputs")
MATRIX = os.path.join(ROOT, "prompts", "daily-paper-tracker.md")

HANDLE_X = "Qihong_Lu"
HANDLE_BSKY = "qlu.bsky.social"
BSKY_DID = "did:plc:ppeiyjusu53ydpuvzafgjnvt"  # @qlu.bsky.social

# ---- science stopwords (extends cleaned Bluesky set) ----
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
led share sharing shared our my we you they he she just got make makes making thing things lot
much want need know like likes liked love love great cool awesome interesting read reading watch
watching listen listening episode episode podcast newslette
""".split())

STOPWORDS |= {"across", "often", "provide", "available", "support", "will",
              "check", "latest", "finally", "announce", "information", "already",
              "along", "also", "get", "got", "going", "dont", "cant", "didnt",
              "looking", "thrilled", "super", "help", "trained", "learned",
              "excited", "happy", "glad", "proud", "congratulations", "pleased",
              "honored", "delighted", "welcome", "thanks", "thank", "join", "register",
              "science", "bsky", "social"}

# ---- generic noise: real words but NOT diagnostic of a paper topic ----
# (sentiment/eval adjectives, quantifiers, framing verbs, seasonal/event
#  words, typo artifacts). Added after user review of keyword-suggestions.md.
GENERIC_NOISE = {
    # sentiment / eval adjectives
    "better", "amazing", "simple", "novel", "well", "great", "cool", "nice",
    "interesting", "exciting", "awesome", "wonderful", "fantastic", "love",
    # quantifiers / generic framing
    "many", "beyond", "much", "lot", "few", "several", "various", "multiple",
    "role", "evidence", "complex", "findings", "experiments", "results",
    "conclusion", "implications", "contribution",
    # framing verbs (author voice, not topic)
    "uses", "propose", "related", "solve", "developed", "interested",
    "finding", "suggest", "suggests", "show", "shows", "argue", "argues",
    "discuss", "discusses", "present", "presents", "report", "reports",
    "demonstrate", "demonstrates", "reveal", "reveals", "highlight",
    "explore", "explores", "investigate", "investigates", "examine",
    "examines", "introduce", "introduces", "develop", "develops",
    # seasonal / event / people words
    "summer", "upcoming", "course", "conference", "workshop", "seminar",
    "colleagues", "collaboration", "collaborators", "team", "group",
    "come", "version", "together", "finally", "recently", "today",
    # typo / misspelling artifacts
    "neuroskyence",
    # second pass (surfaced after first batch removed): eval adj + verbs + generic
    "important", "special", "final", "showed", "look", "updated",
    "scientific", "issue", "toward", "supporting",
}
STOPWORDS |= GENERIC_NOISE

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
URL_RE = re.compile(r"https?://\S+|www\.\S+|[\w.-]+\.(com|org|net|edu|gov|io|ai|app|social|html|pdf|zip)\S*")

# X snowflake IDs encode the exact UTC creation time (ms since Twitter epoch).
def snowflake_to_iso(id_str):
    try:
        sid = int(id_str)
    except (ValueError, TypeError):
        return None
    ts_ms = (sid >> 22) + 1288834974657
    try:
        return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

# Journal/publisher/handle tokens that are noise for *topic* keyword mining.
BRAND_BLACKLIST = set("""
bsky nature neuro neursci neuroscience science cell plos pnas biorxiv arxiv doi pubmed
psyarxiv frontiers mdpi wiley springer elsevier ncbi annualreviews sagepub tandfonline
cambridge oxford natureneuro ptoncompmemlab doellerlab hassonlab mariam s41
rss feed twitter xcom com org net gov edu https http www html pdf doi
""".split())

def _is_brand(tok):
    if tok in BRAND_BLACKLIST:
        return True
    if tok.endswith("lab"):
        return True
    if len(tok) <= 3:
        return True
    return False


# ---------------------------------------------------------------------------
# 1. X normalization
# ---------------------------------------------------------------------------
def normalize_x():
    js_files = sorted(glob.glob(os.path.join(X_ARCHIVE, "**", "tweets*.js"), recursive=True))
    if not js_files:
        return []
    posts = []
    for path in js_files:
        text = open(path, encoding="utf-8", errors="replace").read()
        i = text.find("[")
        if i == -1:
            continue
        arr = json.loads(text[i:])
        for obj in arr:
            t = obj.get("tweet", obj) if isinstance(obj, dict) else obj
            full = t.get("full_text") or t.get("text") or ""
            created = t.get("created_at", "")
            if not re.match(r"^\d{4}-\d{2}-\d{2}T", created or ""):
                # X export mixes in year-less "Wed Sep 29 ..." dates;
                # recover the exact UTC time from the snowflake ID instead.
                created = snowflake_to_iso(t.get("id_str") or t.get("id")) or (created or "")
            else:
                created = created[:19] + "Z"
            retweeted = bool(t.get("retweeted")) or bool(t.get("retweeted_status"))
            orig = None
            if t.get("retweeted_status"):
                orig = (t["retweeted_status"].get("user") or {}).get("screen_name")
            if orig is None and RT_RE.match(full):
                m = re.match(r"^\s*RT\s+@(\w+)", full)
                if m:
                    orig = m.group(1)
            urls = []
            for u in (t.get("entities", {}) or {}).get("urls", []) or []:
                exp = u.get("expanded_url") or u.get("url") or ""
                if exp:
                    urls.append(exp)
            dt = created[:19] if created else ""
            posts.append({
                "platform": "x",
                "id": str(t.get("id_str") or t.get("id") or ""),
                "author": HANDLE_X,
                "original_author": orig,
                "is_share": bool(retweeted or orig),
                "created_at": dt + "Z" if dt else "",
                "text": full,
                "urls": urls,
                "lang": t.get("lang", "en") or "en",
                "engagement": {
                    "likes": int(t.get("favorite_count") or 0),
                    "shares": int(t.get("retweet_count") or 0),
                    "replies": int(t.get("reply_count") or 0),
                },
                "source": os.path.relpath(path, ROOT),
            })
    return posts


# ---------------------------------------------------------------------------
# 2. Bluesky fetch + normalize
# ---------------------------------------------------------------------------
def _bsky_get(params):
    url = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?" + params
    req = urllib.request.Request(url, headers={"User-Agent": "paper-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_bsky():
    posts = []
    cursor = ""
    pages = 0
    while True:
        params = "actor=" + BSKY_DID + "&limit=100"
        if cursor:
            params += "&cursor=" + urllib.parse.quote(cursor)
        try:
            data = _bsky_get(params)
        except Exception as e:
            print(f"[social_unify] Bluesky fetch error: {e}")
            break
        feed = data.get("feed", [])
        if not feed:
            break
        for item in feed:
            post = item.get("post", {})
            rec = post.get("record", {})
            reason = item.get("reason") or {}
            is_share = reason.get("$type", "").endswith("reasonRepost")
            pauthor = post.get("author", {}).get("handle", "")
            if is_share:
                sharer = HANDLE_BSKY
                orig = pauthor
            else:
                sharer = pauthor
                orig = None
            # urls from facets + external embed
            urls = []
            for f in rec.get("facets", []) or []:
                for feat in f.get("features", []) or []:
                    if feat.get("$type", "").endswith("link"):
                        u = feat.get("uri", "")
                        if u:
                            urls.append(u)
            ext = (((post.get("embed") or {}).get("external")) or {})
            if ext.get("uri"):
                urls.append(ext["uri"])
            elif ext.get("url"):
                urls.append(ext["url"])
            created = rec.get("createdAt", "")
            posts.append({
                "platform": "bluesky",
                "id": post.get("uri", ""),
                "author": sharer,
                "original_author": orig,
                "is_share": is_share,
                "created_at": created,
                "text": rec.get("text", ""),
                "urls": urls,
                "lang": "en",
                "engagement": {
                    "likes": int(post.get("likeCount") or 0),
                    "shares": int(post.get("repostCount") or 0),
                    "replies": int(post.get("replyCount") or 0),
                },
                "source": "bluesky api (getAuthorFeed)",
            })
        pages += 1
        cursor = data.get("cursor", "")
        if not cursor or pages >= 25:  # safety cap ~2500 posts
            break
    return posts


# ---------------------------------------------------------------------------
# 3. matrix + classification
# ---------------------------------------------------------------------------
def load_matrix_categories():
    if not os.path.exists(MATRIX):
        return {}
    txt = open(MATRIX, encoding="utf-8").read()
    cats = {}
    blocks = re.split(r"\n### ", txt)
    for b in blocks[1:]:
        lines = b.splitlines()
        header = lines[0]
        m = re.match(r"([A-G])\s*[—-]\s*(.+)", header)
        if not m:
            continue
        key = m.group(1) + " — " + m.group(2).strip()
        body = []
        for ln in lines[1:]:
            if ln.strip() == "" or ln.startswith("#"):
                break
            body.append(ln)
        kws = [t.strip().lower() for t in " ".join(body).split(",") if t.strip()]
        cats[key] = kws
    return cats


def all_matrix_keywords(cats):
    s = set()
    for kws in cats.values():
        s.update(kws)
    return s


def detect_paper(post, matrix_kw):
    text = post["text"]
    raw = " ".join(post.get("urls", []))
    if ACADEMIC_RE.search(raw) or ACADEMIC_RE.search(text):
        return True
    if PAPER_PHRASE_RE.search(text):
        return True
    low = text.lower()
    for kw in matrix_kw:
        if " " in kw and kw in low:
            return True
    return False


def tokenize(text):
    clean = URL_RE.sub(" ", text)
    clean = re.sub(r"@[\w.-]+", " ", clean)  # drop full @handles incl. dotted (e.g. @qlu.bsky.social)
    toks = re.findall(r"[a-z][a-z0-9+#\-]{2,}", clean.lower())
    return [t for t in toks if t not in STOPWORDS and not t.isdigit()]


# ---------------------------------------------------------------------------
# 4. analyze + render
# ---------------------------------------------------------------------------
def render_unified_html(paper_posts, stats):
    rows = []
    for p in paper_posts:
        pb = '<span class="share">SHARE</span>' if p["is_share"] else ""
        links = " ".join(f'<a href="{u}" target="_blank">{html.escape(u)}</a>' for u in p["urls"][:5])
        plat = "X" if p["platform"] == "x" else "BSKY"
        rows.append(
            f'<div class="post"><div class="meta">[{plat}] {p["created_at"][:10]} {pb} '
            f'{(p["original_author"] and "via @"+p["original_author"]) or ""}</div>'
            f'<div class="text">{html.escape(p["text"])}</div>'
            f'<div class="links">{links}</div></div>'
        )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Posts — Unified (X + Bluesky)</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
background:#f8f9fa;color:#1a1a1a;line-height:1.6;max-width:840px;margin:0 auto;padding:32px 20px}}
h1{{font-size:24px;font-weight:700;margin-bottom:4px}}
.sub{{color:#666;font-size:14px;margin-bottom:24px}}
.post{{background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:16px 18px;margin-bottom:12px;
box-shadow:0 1px 3px rgba(0,0,0,0.06)}}
.meta{{font-size:12px;color:#888;margin-bottom:6px}}
.share{{display:inline-block;font-size:10px;font-weight:700;color:#fff;background:#10b981;
padding:1px 6px;border-radius:3px;margin-left:6px}}
.text{{font-size:14px;color:#222;white-space:pre-wrap;word-break:break-word}}
.links{{font-size:12px;margin-top:8px}}
.links a{{color:#1d4ed8;text-decoration:none;word-break:break-all}}
.links a:hover{{text-decoration:underline}}
</style></head><body>
<h1>🐦🦋 Unified Paper Posts</h1>
<div class="sub">{stats}</div>
{''.join(rows)}
</body></html>"""


def make_charts(tokens):
    freq = Counter(tokens)
    top = freq.most_common(40)
    bar_path = wc_path = None
    if top:
        labels = [t for t, _ in top][::-1]
        counts = [c for _, c in top][::-1]
        fig, ax = plt.subplots(figsize=(8, 10))
        ax.barh(labels, counts, color="#6366f1")
        ax.set_xlabel("frequency (paper posts)")
        ax.set_title("Top keywords — unified X + Bluesky paper posts")
        ax.tick_params(labelsize=9)
        fig.tight_layout()
        bar_path = os.path.join(OUT, "keywords-bar-unified.png")
        fig.savefig(bar_path, dpi=130)
        plt.close(fig)
    if HAVE_WORDCLOUD and tokens:
        wc = WordCloud(width=900, height=500, background_color="white",
                       max_words=150, colormap="plasma").generate(" ".join(tokens))
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        fig.tight_layout()
        wc_path = os.path.join(OUT, "wordcloud-unified.png")
        fig.savefig(wc_path, dpi=130)
        plt.close(fig)
    return bar_path, wc_path


def main():
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    print("[social_unify] Normalizing X archive ...")
    x_posts = normalize_x()
    with open(os.path.join(RAW, "x_posts.json"), "w", encoding="utf-8") as f:
        json.dump(x_posts, f, ensure_ascii=False, indent=1)
    print(f"   X posts: {len(x_posts)}")

    print("[social_unify] Fetching Bluesky (public API) ...")
    bsky_posts = fetch_bsky()
    with open(os.path.join(RAW, "bsky_posts.json"), "w", encoding="utf-8") as f:
        json.dump(bsky_posts, f, ensure_ascii=False, indent=1)
    print(f"   Bluesky posts: {len(bsky_posts)}")

    merged = x_posts + bsky_posts
    merged.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    normalized = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platforms": {"x": len(x_posts), "bluesky": len(bsky_posts)},
        "posts": merged,
    }
    with open(os.path.join(ROOT, "data", "posts_normalized.json"), "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=1)
    print(f"[social_unify] Wrote data/posts_normalized.json ({len(merged)} records)")

    cats = load_matrix_categories()
    matrix_kw = all_matrix_keywords(cats)
    paper = [p for p in merged if detect_paper(p, matrix_kw)]
    rt = sum(1 for p in paper if p["is_share"])
    xc = sum(1 for p in paper if p["platform"] == "x")
    bc = sum(1 for p in paper if p["platform"] == "bluesky")
    print(f"[social_unify] Paper-related: {len(paper)} "
          f"(X={xc}, BSKY={bc}, shares={rt})")

    stats = (f"{len(paper)} paper-related posts "
             f"(X: {xc}, Bluesky: {bc}; shares/retweets: {rt}) of "
             f"{len(merged)} total. Generated {datetime.now():%Y-%m-%d}.")
    html_out = render_unified_html(paper, stats)
    with open(os.path.join(OUT, "paper-posts-unified.html"), "w", encoding="utf-8") as f:
        f.write(html_out)

    tokens = []
    for p in paper:
        tokens.extend(tokenize(p["text"]))
    bar_path, wc_path = make_charts(tokens)

    # category breakdown
    cat_hits = defaultdict(int)
    cat_samples = defaultdict(list)
    for p in paper:
        low = p["text"].lower()
        for label, kws in cats.items():
            hit = [kw for kw in kws if (" " in kw and kw in low) or (len(kw) > 4 and re.search(r"\b"+re.escape(kw)+r"\b", low))]
            if hit:
                cat_hits[label] += 1
                cat_samples[label].extend(hit[:3])
    cb = ["# Category breakdown (paper posts matched)\n"]
    for label in sorted(cat_hits, key=lambda k: -cat_hits[k]):
        samp = ", ".join(sorted(set(cat_samples[label]))[:8])
        cb.append(f"- **{label}**: {cat_hits[label]} posts  _(e.g. {samp})_")
    cb.append("")
    with open(os.path.join(OUT, "category-breakdown.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(cb))

    # keyword suggestions
    sug = [t for t, c in Counter(tokens).most_common(300)
           if t not in matrix_kw
           and not any(t in kw or kw in t for kw in matrix_kw)
           and t not in STOPWORDS
           and not _is_brand(t)]
    sug_md = ["# Suggested keyword additions (not yet in the matrix)\n",
              "_Top new tokens from unified paper posts (frequency in parentheses)_\n"]
    for t in sug[:60]:
        sug_md.append(f"- {t} ({tokens.count(t)})")
    sug_md.append("")
    with open(os.path.join(OUT, "keyword-suggestions.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(sug_md))

    print("[social_unify] Wrote: paper-posts-unified.html")
    if bar_path:
        print("[social_unify] Wrote: keywords-bar-unified.png")
    if wc_path:
        print("[social_unify] Wrote: wordcloud-unified.png")
    print("[social_unify] Wrote: category-breakdown.md, keyword-suggestions.md")
    print("\nCategory breakdown:")
    for line in cb[1:]:
        if line.strip():
            print("  " + line)


if __name__ == "__main__":
    main()
