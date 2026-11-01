#!/usr/bin/env python3
"""Fetch a passage's text from Bible Gateway as plain text with verse numbers.

Usage: python3 scripture.py "Proverbs 1" NIV
Prints JSON: {"reference", "version", "url", "text"}. Verse numbers appear as [[n]].
Paragraphs are separated by blank lines. Footnotes and cross-references are dropped.
"""
import json
import re
import sys
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup



def fetch(reference, version):
    url = ("https://www.biblegateway.com/passage/?" +
           urllib.parse.urlencode({"search": reference, "version": version}))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(urllib.request.urlopen(req, timeout=30).read(), "html.parser")
    blocks = []
    for passage in soup.select("div.passage-text"):
        for junk in passage.select("sup.footnote, sup.crossreference, div.footnotes, "
                                   "div.crossrefs, div.publisher-info-bottom, a.full-chap-link, "
                                   "h3, h4, .passage-other-trans, .dropdown-display"):
            junk.decompose()
        for vn in passage.select("sup.versenum"):
            vn.replace_with("[[" + vn.get_text().strip() + "]] ")
        for cn in passage.select("span.chapternum"):
            # chapter number marks verse 1
            cn.replace_with("[[1]] ")
        for br in passage.find_all("br"):
            br.replace_with("\x00")
        for el in passage.select("p, li"):
            raw = el.get_text("")
            lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw.split("\x00")]
            t = "\n".join(ln for ln in lines if ln)
            if t:
                blocks.append(t)
    # Poetry spans can split a line across tags; tidy spacing before punctuation.
    text = "\n\n".join(re.sub(r" ([,.;:!?’”])", r"\1", b) for b in blocks)
    return {"reference": reference, "version": version, "url": url, "text": text}


if __name__ == "__main__":
    print(json.dumps(fetch(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "ESV"),
                     ensure_ascii=False, indent=1))
