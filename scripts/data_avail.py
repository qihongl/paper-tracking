#!/usr/bin/env python3
"""Detect whether a paper publicly releases its DATA and its CODE, separately.

Usage:
    data_avail.py IN.json OUT.json        # annotate a candidate list
    data_avail.py --doi 10.1038/xxxx      # single lookup, JSON to stdout

Each annotated record gains:
    data_avail            open_data | restricted | on_request | unknown
    data_avail_evidence   data-availability statement (truncated)
    data_avail_url        repository link named in that statement
    code_avail            open_code | on_request | unknown
    code_avail_evidence   code-availability statement (truncated)
    code_avail_url        code repository link

The two are INDEPENDENT: a paper can earn both badges, one, or neither.
`open_data` means the data themselves are publicly downloadable — from a
repository, or as published Source Data / Supplementary files. It does NOT
include "available upon reasonable request", controlled access (dbGaP, EGA,
UK Biobank), or a code-only release. `open_code` requires a code statement that
names a repository or URL; a passing mention of "code is available" without a
location does not qualify.

Statements are read from the article's Data availability and Code availability
sections — never the abstract. Resolution order:
    publisher page (resolved from the DOI) -> Europe PMC full text -> abstract links
"""
import html as htmlmod
import json
import re
import subprocess
import sys
import time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# ---------------------------------------------------------------- repositories
# (label, regex). AMBIGUOUS_HOSTS can hold either data or code, so there a
# repository only counts when a data-ish (or code-ish) word sits near the link.
REPOS = [
    ("OSF",             r"\bosf\.io"),
    ("Dryad",           r"datadryad\.org|10\.5061/dryad"),
    ("Zenodo",          r"zenodo\.org|10\.5281/zenodo"),
    ("Figshare",        r"figshare\.com|10\.6084/m9\.figshare"),
    ("OpenNeuro",       r"openneuro\.org|\bds00\d{4}\b"),
    ("NeuroVault",      r"neurovault\.org"),
    ("DABI",            r"dabi\.loni\.usc\.edu"),
    ("GIN",             r"gin\.g-node\.org"),
    ("NITRC",           r"nitrc\.org"),
    ("DANDI",           r"dandiarchive\.org"),
    ("EBRAINS",         r"ebrains\.eu"),
    ("BossDB",          r"bossdb\.org"),
    ("GEO",             r"ncbi\.nlm\.nih\.gov/geo|\bGSE\d{3,}\b"),
    ("SRA/ENA",         r"ncbi\.nlm\.nih\.gov/sra|ebi\.ac\.uk/ena"),
    ("PRIDE",           r"ebi\.ac\.uk/pride"),
    ("MetaboLights",    r"ebi\.ac\.uk/metabolights"),
    ("IEEE DataPort",   r"ieee-dataport\.org"),
    ("Dataverse",       r"dataverse\.|10\.7910/DVN"),
    ("Mendeley Data",   r"data\.mendeley\.com|10\.17632/"),
    ("PhysioNet",       r"physionet\.org"),
    ("Code Ocean",      r"codeocean\.com"),
    ("Hugging Face",    r"huggingface\.co/datasets"),
    ("Kaggle",          r"kaggle\.com/datasets"),
    ("UK Data Service", r"ukdataservice\.ac\.uk|icpsr\.umich\.edu"),
    ("GitHub",          r"github\.com|gitlab\.com|bitbucket\.org"),
]
AMBIGUOUS_HOSTS = {"Zenodo", "Figshare", "Dataverse", "Mendeley Data",
                   "Code Ocean", "GitHub"}

RESTRICTED = (r"dbgap|ega-archive|ega\.eu|uk ?biobank|controlled[- ]access|"
              r"data[- ]use agreement|data access committee|upon approval|"
              r"access (?:is )?subject to|restricted[- ]access|"
              r"not publicly available|under licen[cs]e")
ON_REQUEST = (r"upon (?:reasonable )?request|on (?:reasonable )?request|"
              r"from the (?:corresponding|lead|first) author|"
              r"available from the authors|request(?:ed)? from")
SI_PUBLIC = (r"source data (?:are|is) (?:provided|available)|"
             r"(?:data|dataset|data ?files?)[^.]{0,140}?(?:provided|available|deposited|included)"
             r"[^.]{0,80}?(?:supporting information|supplementary)[^.]{0,80}?"
             r"(?:file|files|dataset|spreadsheet|excel|table|data)|"
             r"(?:provided|available|deposited) in (?:the )?(?:supporting information|supplementary)"
             r"[^.]{0,80}?(?:file|files|dataset|spreadsheet|excel|table|data)")
DATA_WORDS = re.compile(r"\b(data|dataset|datasets|data ?files?|recordings?|spikes?|"
                        r"matrices|matrix|responses|imaging data|raw data|"
                        r"behaviou?ral data|processed data)\b", re.I)
CODE_WORDS = re.compile(r"\b(code|source code|scripts?|software|toolbox|pipeline|"
                        r"implementations?|algorithms?|codebase)\b", re.I)

HEADING = (r"\b(data (?:and code |, materials, and software |and materials |and software )?"
           r"availability(?: statement)?|availability of data(?: and materials)?)\b")
STOP = (r"\b(code availability|references|acknowledg|author contributions|"
        r"competing interests|supplementary information|materials and correspondence|"
        r"additional information|funding)\b")
CHROME = (r"ethical publishing practice|expressions of concern|disclosure of funding|"
          r"licenses and copyright|competing interests|authorship|"
          r"materials, software and code sharing|complementary research|"
          r"corrections, expressions")

DATA_ANCHORS = ('id="data-availability-content"', 'id="data-availability"',
                'data-title="Data availability"', 'sec-type="data-availability"')
CODE_ANCHORS = ('id="code-availability-content"', 'id="code-availability"',
                'data-title="Code availability"', 'sec-type="code-availability"')


def fetch(url, timeout=40):
    try:
        r = subprocess.run(["curl", "-sS", "-L", "-A", UA, "--max-time", str(timeout), url],
                           capture_output=True, text=True, errors="ignore")
        return r.stdout or ""
    except Exception:
        return ""


def strip_tags(s):
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def looks_like_chrome(text):
    return len(re.findall(CHROME, text, re.I)) >= 2


def slice_section(doc, kind):
    """Raw HTML of the 'data' or 'code' availability section, or ''."""
    for anchor in (DATA_ANCHORS if kind == "data" else CODE_ANCHORS):
        i = doc.find(anchor)
        if i == -1:
            continue
        seg = doc[i + len(anchor):i + 6000]
        if ">" in seg[:200]:
            seg = seg[seg.find(">") + 1:]        # drop the rest of the opening tag
        other = 'id="code-availability' if kind == "data" else 'id="data-availability'
        other_title = ('data-title="Code availability"' if kind == "data"
                       else 'data-title="Data availability"')
        for stop in ("</section>", other, other_title):
            j = seg.find(stop)
            if j > 0:
                seg = seg[:j]
        if len(strip_tags(seg)) > 30:
            return seg
    # Bold lead-in, e.g. PLOS/BMC: <p><strong>Data Availability: </strong>...</p>
    word = "data" if kind == "data" else "code"
    m = re.search(r"(?is)<p[^>]*>\s*<strong>\s*" + word +
                  r"[^<]{0,40}availability\s*:?\s*</strong>(.{0,2500}?)</p>", doc)
    if m:
        return m.group(0)
    # Heading tag.
    m = re.search(r"(?is)<h[1-4][^>]*>[^<]{0,40}?" + word +
                  r"[^<]{0,60}?availab[^<]{0,40}?</h[1-4]>", doc)
    if m:
        seg = doc[m.start():m.start() + 6000]
        nxt = re.search(r"(?is)</h[1-4]>.*?<h[1-4]", seg[10:])
        if nxt:
            seg = seg[:nxt.start() + 10]
        if len(strip_tags(seg)) > 30:
            return seg
    return ""


def generic_scan(doc):
    """Fallback for pages with no anchored section: first heading with real content."""
    text = strip_tags(doc)
    for m in re.finditer(HEADING, text, re.I):
        tail = text[m.end():m.end() + 900]
        if looks_like_chrome(tail):
            continue
        if not re.search(r"available|deposit|accession|provided|archiv|request|restrict",
                         tail, re.I):
            continue
        s = re.search(STOP, tail, re.I)
        if s and s.start() > 40:
            tail = tail[:s.start()]
        return tail.strip()
    return ""


def extract(doc):
    """-> (data_stmt, data_hrefs, code_stmt, code_hrefs)"""
    ds = slice_section(doc, "data")
    cs = slice_section(doc, "code")
    d_txt = strip_tags(ds) if ds else ""
    c_txt = strip_tags(cs) if cs else ""
    if d_txt and looks_like_chrome(d_txt):
        d_txt = ""
    if c_txt and looks_like_chrome(c_txt):
        c_txt = ""
    if not d_txt:
        d_txt = generic_scan(doc)
    return (d_txt[:1500], re.findall(r'href="([^"]+)"', ds),
            c_txt[:1200], re.findall(r'href="([^"]+)"', cs))


def _repo_hit(low, words, hrefs):
    """First repository whose link sits near a matching word, else first plain repo."""
    for label, pat in REPOS:
        m = re.search(pat, low, re.I)
        if not m:
            continue
        if label in AMBIGUOUS_HOSTS:
            window = low[max(0, m.start() - 170):m.end() + 170]
            if not words.search(window):
                continue
        return label
    for label, pat in REPOS:
        for h in hrefs:
            if re.search(pat, h, re.I):
                return label
    return None


def classify_data(stmt, hrefs):
    if not stmt:
        return "unknown"
    blob = (stmt + " " + " ".join(hrefs)).lower()
    if re.search(RESTRICTED, blob):
        return "restricted"
    if _repo_hit(stmt.lower(), DATA_WORDS, hrefs):
        return "open_data"
    if re.search(ON_REQUEST, blob):
        return "on_request"
    if re.search(SI_PUBLIC, blob):
        return "open_data"
    return "unknown"


def classify_code(code_stmt, code_hrefs, data_stmt="", data_hrefs=()):
    stmt = (code_stmt or "").strip()
    hrefs = list(code_hrefs or [])
    # Some papers put the code statement inside the data statement.
    if not stmt and data_stmt and re.search(r"\bcode\b", data_stmt, re.I):
        stmt, hrefs = data_stmt, list(data_hrefs)
    if not stmt:
        return "unknown"
    blob = (stmt + " " + " ".join(hrefs)).lower()
    if re.search(ON_REQUEST, blob) and not re.search(r"https?://", blob):
        return "on_request"
    if re.search(r"https?://", blob) or _repo_hit(stmt.lower(), CODE_WORDS, hrefs):
        return "open_code"
    if re.search(r"\bcode\b[^.]{0,160}?(?:available|deposited|archived|released)", blob):
        return "open_code"
    return "unknown"


def pick_url(stmt, hrefs):
    """The repository URL mentioned EARLIEST in the statement (not list order)."""
    cand = [h for h in hrefs
            if re.search(r"https?://", h) and not re.search(r"#(ref|sec|fig|table|Sec|Fig)", h)]
    best, best_pos = "", 1e9
    low = (stmt or "").lower()
    for idx, h in enumerate(cand):
        dom = re.sub(r"^https?://", "", h).split("/")[0].lower()
        pos = low.find(dom) if dom else -1
        if pos == -1:
            pos = len(low) + idx
        if pos < best_pos:
            best_pos, best = pos, h
    if best:
        return best
    m = re.search(r"https?://[^\s)\]\"']+", stmt or "")
    return m.group(0) if m else ""


def _https(u):
    return re.sub(r"^http://", "https://", u or "")


def scan_text(text):
    """Cheap channel for preprints: repo links near data/code words in the abstract."""
    if not text:
        return None, None
    low = text.lower()
    return (_repo_hit(low, DATA_WORDS, []), _repo_hit(low, CODE_WORDS, []))


def europepmc_fulltext(doi):
    q = fetch("https://www.ebi.ac.uk/europepmc/webservices/rest/search"
              "?query=DOI:%22" + doi + "%22&format=json&resultType=core")
    try:
        res = json.loads(q)["resultList"]["result"]
    except Exception:
        return ""
    if not res or not res[0].get("pmcid"):
        return ""
    return fetch("https://www.ebi.ac.uk/europepmc/webservices/rest/"
                 + res[0]["pmcid"] + "/fullTextXML")


def lookup(doi_or_url, abstract=""):
    """-> dict with data_* and code_* availability fields."""
    url = doi_or_url if re.match(r"https?://", doi_or_url) else "https://doi.org/" + doi_or_url
    candidates = [url]
    m = re.search(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", doi_or_url, re.I)
    if m:
        candidates.insert(0, "https://arxiv.org/html/" + m.group(1))
    docs = []
    for u in candidates:
        doc = fetch(u)
        if len(doc) >= 20000:          # skip bot stubs / paywalls
            docs.append(doc)
    doi = re.search(r"(10\.\d{4,9}/[^\s\"?#]+)", doi_or_url)
    if doi:
        xml = europepmc_fulltext(doi.group(1))
        if len(xml) > 5000:
            docs.append(xml)

    for doc in docs:
        d_stmt, d_hrefs, c_stmt, c_hrefs = extract(doc)
        d_status = classify_data(d_stmt, d_hrefs)
        c_status = classify_code(c_stmt, c_hrefs, d_stmt, d_hrefs)
        if d_status != "unknown" or c_status != "unknown":
            c_used, c_urls = c_stmt, c_hrefs
            if not c_used and re.search(r"\bcode\b", d_stmt, re.I):
                c_used, c_urls = d_stmt, d_hrefs      # statement shared with the data section
            return {
                "data_avail": d_status,
                "data_avail_evidence": d_stmt[:400],
                "data_avail_url": _https(pick_url(d_stmt, d_hrefs)) if d_status == "open_data" else "",
                "code_avail": c_status,
                "code_avail_evidence": c_used[:400],
                "code_avail_url": _https(pick_url(c_used, c_urls)) if c_status == "open_code" else "",
            }
    d_hit, c_hit = scan_text(abstract)
    return {
        "data_avail": "open_data" if d_hit else "unknown",
        "data_avail_evidence": ("[abstract] " + abstract[:300]) if d_hit else "",
        "data_avail_url": "",
        "code_avail": "open_code" if c_hit else "unknown",
        "code_avail_evidence": ("[abstract] " + abstract[:300]) if c_hit else "",
        "code_avail_url": "",
    }


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--doi":
        r = lookup(args[1])
        r["id"] = args[1]
        print(json.dumps(r, indent=1))
        return
    src, dst = args[0], args[1]
    rows = json.load(open(src))
    for i, p in enumerate(rows):
        key = p.get("DOI") or p.get("doi") or p.get("url") or p.get("URL") or ""
        if not key:
            p.update(data_avail="unknown", code_avail="unknown")
        else:
            p.update(lookup(key, p.get("abstract", "")))
        print(f"  [d:{p.get('data_avail','?'):11s} c:{p.get('code_avail','?'):10s}] "
              f"{key}  {(p.get('title') or '')[:52]}", file=sys.stderr)
        if i < len(rows) - 1:
            time.sleep(1.5)
    json.dump(rows, open(dst, "w"), indent=1, ensure_ascii=False)
    nd = sum(1 for p in rows if p.get("data_avail") == "open_data")
    nc = sum(1 for p in rows if p.get("code_avail") == "open_code")
    print(f"annotated={len(rows)} open_data={nd} open_code={nc} -> {dst}", file=sys.stderr)


if __name__ == "__main__":
    main()
