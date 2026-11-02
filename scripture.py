#!/usr/bin/env python3
"""Fetch a passage's text from Bible Gateway as plain text with verse numbers.

Usage: python3 scripture.py "Proverbs 1" NIV
Prints JSON: {"reference", "version", "url", "text"}. Verse numbers appear as [[n]].
Paragraphs are separated by blank lines. Footnotes and cross-references are dropped.
Standard library only, so it runs without installing anything.
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

VOID = {"br", "img", "hr", "input", "meta", "link", "area", "base", "col", "embed",
        "source", "track", "wbr"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.parent, self.children = tag, parent, []
        self.attrs = dict(attrs)
        self.classes = set((self.attrs.get("class") or "").split())


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node("root", [], None)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def walk(n):
    for c in n.children:
        if isinstance(c, Node):
            yield c
            yield from walk(c)


def skip(n):
    return (n.tag in ("h3", "h4") or
            (n.tag == "sup" and n.classes & {"footnote", "crossreference"}) or
            (n.tag == "div" and n.classes & {"footnotes", "crossrefs", "publisher-info-bottom"}) or
            (n.tag == "a" and "full-chap-link" in n.classes) or
            n.classes & {"passage-other-trans", "dropdown-display"})


def text_of(n):
    out = []
    for c in n.children:
        if isinstance(c, str):
            out.append(c)
        elif skip(c):
            continue
        elif c.tag == "br":
            out.append("\x00")
        elif c.tag == "sup" and "versenum" in c.classes:
            out.append("[[" + "".join(x for x in c.children if isinstance(x, str)).strip() + "]] ")
        elif c.tag == "span" and "chapternum" in c.classes:
            out.append("[[1]] ")  # chapter number marks verse 1
        else:
            out.append(text_of(c))
    return "".join(out)


def fetch(reference, version):
    url = ("https://www.biblegateway.com/passage/?" +
           urllib.parse.urlencode({"search": reference, "version": version}))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    t = Tree()
    t.feed(urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace"))
    blocks = []
    for passage in (n for n in walk(t.root) if n.tag == "div" and "passage-text" in n.classes):
        for el in walk(passage):
            if el.tag not in ("p", "li"):
                continue
            # skip paragraphs inside removed sections (footnotes, cross-refs)
            p, bad = el.parent, False
            while p is not None and p is not passage:
                if skip(p):
                    bad = True
                    break
                p = p.parent
            if bad:
                continue
            lines = [re.sub(r"\s+", " ", ln).strip() for ln in text_of(el).split("\x00")]
            t2 = "\n".join(ln for ln in lines if ln)
            if t2:
                blocks.append(t2)
    # Poetry spans can split a line across tags; tidy spacing before punctuation.
    text = "\n\n".join(re.sub(r" ([,.;:!?’”])", r"\1", b) for b in blocks)
    return {"reference": reference, "version": version, "url": url, "text": text}


if __name__ == "__main__":
    print(json.dumps(fetch(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "ESV"),
                     ensure_ascii=False, indent=1))
