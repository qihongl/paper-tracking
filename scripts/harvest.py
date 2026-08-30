#!/usr/bin/env python3
"""Harvest candidate papers from arXiv, PubMed, bioRxiv, Crossref for a date window.

Usage: harvest.py START END OUT.json
Dates: YYYY-MM-DD
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

UA = "paper-tracker/1.0 (mailto:qihonglu@gmail.com)"


def get(url, retries=3, timeout=90):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            sys.stderr.write(f"  retry {i+1} {type(e).__name__} {e}\n")
            time.sleep(3)
    return None


# ---------------- arXiv ----------------
ARXIV_CATS = [
    "cs.CL", "cs.AI", "cs.LG", "cs.NE", "q-bio.NC", "stat.ML", "cs.HC",
    "cond-mat.dis-nn", "cs.IR", "cs.MA",
]


def arxiv(start, end):
    out = []
    catq = " OR ".join(f"cat:{c}" for c in ARXIV_CATS)
    q = f"({catq}) AND submittedDate:[{start.replace('-','')}0000 TO {end.replace('-','')}2359]"
    url = ("http://export.arxiv.org/api/query?search_query="
           + urllib.parse.quote(q)
           + "&start=0&max_results=2000&sortBy=submittedDate&sortOrder=descending")
    raw = get(url)
    if not raw:
        return out
    import xml.etree.ElementTree as ET
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(raw)
    for e in root.findall("a:entry", ns):
        eid = e.findtext("a:id", "", ns)
        title = " ".join(e.findtext("a:title", "", ns).split())
        summ = " ".join(e.findtext("a:summary", "", ns).split())
        pub = e.findtext("a:published", "", ns)[:10]
        upd = e.findtext("a:updated", "", ns)[:10]
        authors = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
        doi = e.findtext("{http://arxiv.org/schemas/atom}doi", "") or ""
        cats = [c.get("term") for c in e.findall("a:category", ns)]
        out.append({
            "src": "arXiv", "id": eid, "doi": doi, "title": title,
            "abstract": summ, "authors": authors, "date": pub, "updated": upd,
            "venue": "arXiv " + (cats[0] if cats else ""),
        })
    return out


# ---------------- PubMed ----------------
PUBMED_TERMS = [
    'episodic memory', 'hippocampus memory', 'hippocampal replay',
    'sharp-wave ripple', 'schema memory', 'temporal context memory',
    'serial recall', 'free recall', 'pattern separation', 'pattern completion',
    'naturalistic fMRI memory', 'inter-subject correlation memory',
    'working memory', 'memory consolidation sleep', 'event segmentation memory',
    'memory reactivation', 'spatial navigation memory', 'entorhinal cortex',
    'cognitive map', 'retrieval practice', 'narrative memory',
]


def pubmed(start, end):
    ids = set()
    s = start.replace("-", "/")
    e = end.replace("-", "/")
    for t in PUBMED_TERMS:
        u = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmax=200"
             + "&sort=date&term=" + urllib.parse.quote(t)
             + f'&mindate={s}&maxdate={e}&datetype=edat&retmode=json')
        raw = get(u, timeout=60)
        if not raw:
            continue
        try:
            d = json.loads(raw)
            ids.update(d["esearchresult"]["idlist"])
        except Exception as ex:
            sys.stderr.write(f"pubmed parse {ex}\n")
        time.sleep(0.4)
    ids = sorted(ids)
    sys.stderr.write(f"pubmed ids: {len(ids)}\n")
    out = []
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        u = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id="
             + ",".join(chunk))
        raw = get(u, timeout=120)
        if not raw:
            continue
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(raw)
        except Exception as ex:
            sys.stderr.write(f"efetch parse {ex}\n")
            continue
        for art in root.findall(".//PubmedArticle"):
            pmid = art.findtext(".//PMID", "")
            title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
            abstract = " ".join("".join(x.itertext()) for x in art.findall(".//AbstractText"))
            journal = art.findtext(".//Journal/ISOAbbreviation", "") or art.findtext(".//Journal/Title", "")
            authors = []
            for a in art.findall(".//Author"):
                ln = a.findtext("LastName", "")
                fn = a.findtext("ForeName", "")
                if ln:
                    authors.append(f"{fn} {ln}".strip())
            # NOTE: must read the DOI from PubmedData/ArticleIdList only. Scanning
            # ".//ArticleId" also picks up DOIs inside <ReferenceList>, which silently
            # attaches a *reference's* DOI to the record (observed 2026-08-30).
            doi = ""
            for aid in art.findall("./PubmedData/ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = (aid.text or "").strip()
                    break
            date = ""
            for path in (".//ArticleDate", ".//PubMedPubDate[@PubStatus='entrez']"):
                n = art.find(path)
                if n is not None:
                    y = n.findtext("Year", "")
                    m = n.findtext("Month", "01").zfill(2)
                    dd = n.findtext("Day", "01").zfill(2)
                    date = f"{y}-{m}-{dd}"
                    break
            out.append({
                "src": "PubMed", "id": "PMID:" + pmid, "doi": doi,
                "title": " ".join(title.split()), "abstract": " ".join(abstract.split()),
                "authors": authors, "date": date, "venue": journal,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
        time.sleep(0.5)
    return out


# ---------------- bioRxiv / medRxiv ----------------
def biorxiv(start, end, server="biorxiv"):
    out = []
    url = f"https://api.biorxiv.org/details/{server}/{start}/{end}/0"
    raw = get(url, retries=2, timeout=180)
    if not raw:
        return out
    try:
        d = json.loads(raw)
    except Exception as e:
        sys.stderr.write(f"biorxiv parse {e}\n")
        return out
    coll = d.get("collection", [])
    for it in coll:
        out.append({
            "src": server, "id": it.get("doi", ""), "doi": it.get("doi", ""),
            "title": " ".join((it.get("title") or "").split()),
            "abstract": " ".join((it.get("abstract") or "").split()),
            "authors": (it.get("authors") or "").split("; "),
            "date": it.get("date", ""), "venue": it.get("category", server),
            "url": f"https://www.biorxiv.org/content/{it.get('doi','')}v1",
        })
    return out


# ---------------- Crossref (journals) ----------------
CROSSREF_ISSN = [
    "1097-6256",  # Nat Neurosci
    "2397-3374",  # Nat Hum Behav
    "2041-1723",  # Nat Commun
    "0896-6273",  # Neuron
    "2050-084X",  # eLife
    "0960-9822",  # Curr Biol
    "0270-6474",  # J Neurosci
    "1364-6613",  # Trends Cogn Sci
    "0027-8424",  # PNAS
    "1053-8119",  # NeuroImage
    "1471-003X",  # Nat Rev Neurosci
    "0092-8674",  # Cell
    "1050-9631",  # Hippocampus
    "2662-9992",  # Commun Psychol
    "2399-3642",  # Commun Biol
    "2052-4463",  # Sci Data
    "0096-3445",  # JEP:General
    "0963-7214",  # Cognition
    "0010-0285",  # Cogn Psychol
    "0364-0213",  # Cogn Sci
    "1552-5260",  # Neurobiol Aging
    "1873-9245",  # Cortex
    "1759-1198",  # Nat Rev Psychol
    "2057-1720",  # npj Sci Learn
    "1467-9280",  # Psych Sci
]


def crossref(start, end):
    out = []
    for issn in CROSSREF_ISSN:
        u = ("https://api.crossref.org/works?filter=issn:" + issn
             + f",from-pub-date:{start},until-pub-date:{end}&rows=200&sort=published&order=desc"
             + "&select=DOI,title,abstract,author,published,container-title,URL")
        raw = get(u, timeout=90)
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except Exception:
            continue
        for it in d.get("message", {}).get("items", []):
            t = (it.get("title") or [""])[0]
            ab = it.get("abstract", "") or ""
            import re as _re
            ab = _re.sub(r"<[^>]+>", " ", ab)
            parts = (it.get("published", {}).get("date-parts") or [[None]])[0]
            date = "-".join(str(p).zfill(2) for p in parts) if parts and parts[0] else ""
            authors = [f"{a.get('given','')} {a.get('family','')}".strip() for a in it.get("author", [])]
            out.append({
                "src": "Crossref", "id": it.get("DOI", ""), "doi": it.get("DOI", ""),
                "title": " ".join(t.split()), "abstract": " ".join(ab.split()),
                "authors": authors, "date": date,
                "venue": (it.get("container-title") or [""])[0],
            })
        time.sleep(0.2)
    return out


if __name__ == "__main__":
    start, end, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    allp = []
    sys.stderr.write("arXiv...\n")
    a = arxiv(start, end)
    sys.stderr.write(f"  {len(a)}\n")
    allp += a
    sys.stderr.write("PubMed...\n")
    p = pubmed(start, end)
    sys.stderr.write(f"  {len(p)}\n")
    allp += p
    sys.stderr.write("bioRxiv...\n")
    b = biorxiv(start, end)
    sys.stderr.write(f"  {len(b)}\n")
    allp += b
    sys.stderr.write("Crossref...\n")
    c = crossref(start, end)
    sys.stderr.write(f"  {len(c)}\n")
    allp += c
    with open(outp, "w") as f:
        json.dump(allp, f)
    print(f"TOTAL {len(allp)} -> {outp}")
