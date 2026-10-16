#!/usr/bin/env python3
"""Turn a reading list kept as a Google Doc into a page of the site and a PDF.

Usage:
    python3 scripts/reading_list.py <slug> <doc.html> <doc.pdf>

<doc.html> and <doc.pdf> are the Google Doc exported as HTML and as PDF.
<slug> is the page's address, e.g. "social-construction-reading-list", which
gives the page src/pages/<slug>.html (served at /<slug>/) and the PDF
site/media/<slug>.pdf. Add the page to PAGES in scripts/build_site.py once,
then run that script to publish the HTML.

What the doc is expected to look like (the Social Construction list does):
- a bold title, then a "Compiled by ..." line, then intro paragraphs;
- bold "Unit N: ..." headings, and one closing bold heading for anything
  else (e.g. "Additional Teaching Resources");
- bold topic headings numbered "1.1 ...", each followed by a one-paragraph
  description;
- readings marked with a left border (the green bar in the doc); paragraphs
  without one are shown as ordinary text.
Comments on the doc are ignored. Footnotes become notes at the foot of the
page. The PDF loses its first page when that page carries only the doc's tab
name, as Google Docs exports it.

Needs BeautifulSoup (bs4) and PyMuPDF (pymupdf).
"""
import html
import pathlib
import re
import sys
import urllib.parse

import pymupdf
from bs4 import BeautifulSoup, NavigableString

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Colour band for each section, in order; the last is used for any further sections.
BANDS = ["honey", "rose", "celadon", "pale", "rule"]


def clean_url(url):
    """Google wraps links as google.com/url?q=<target>; unwrap them."""
    if url.startswith("https://www.google.com/url"):
        return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["q"][0]
    return url


def runs(p, notes):
    """The paragraph's text as HTML, keeping italics, links and footnote marks."""
    out = []
    for node in p.children:
        if isinstance(node, NavigableString):
            out.append(html.escape(str(node), quote=False))
            continue
        if node.name == "sup":
            a = node.find("a")
            href = a.get("href", "") if a else ""
            if href.startswith("#ftnt"):  # a footnote: number it
                n = len(notes) + 1
                notes.append(href[1:])
                out.append(f'<sup class="rl-mark"><a href="#note-{n}" id="note-ref-{n}">{n}</a></sup>')
            continue  # comment marks ([a], [b], ...) are dropped
        if node.name == "a":
            text = html.escape(node.get_text(), quote=False)
            out.append(f'<a href="{html.escape(clean_url(node["href"]))}">{text}</a>')
            continue
        style = node.get("style", "")
        inner = "".join(runs(node, notes)) if node.find(True) else html.escape(node.get_text(), quote=False)
        if "font-style:italic" in style and inner.strip():
            # keep the spaces outside the italics
            lead = inner[: len(inner) - len(inner.lstrip())]
            trail = inner[len(inner.rstrip()):]
            inner = f"{lead}<i>{inner.strip()}</i>{trail}"
        out.append(inner)
    return out


def text_of(p, notes):
    s = "".join(runs(p, notes))
    s = re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()
    return s.replace("</i><i>", "")


def is_bold(p):
    spans = [s for s in p.find_all("span") if s.get_text().strip()]
    return bool(spans) and all("font-weight:700" in s.get("style", "") for s in spans)


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text).lower()
    text = re.sub(r"^unit (\d+):.*", r"unit-\1", text)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def parse(doc_html):
    soup = BeautifulSoup(doc_html, "html.parser")
    notes = []
    title = byline = None
    intro, sections = [], []
    section = topic = None
    for p in soup.body.find_all("p", recursive=False):
        if "title" in (p.get("class") or []):
            continue  # the doc's tab name
        if not p.get_text().strip():
            continue
        text = text_of(p, notes)
        plain = re.sub(r"<[^>]+>", "", text)
        if title is None:
            title = plain
            continue
        if byline is None and plain.lower().startswith("compiled by"):
            byline = plain
            continue
        bold = is_bold(p)
        if bold and (re.match(r"Unit \d+:", plain) or (section is not None and not re.match(r"\d+\.\d+", plain))):
            section = {"title": text, "id": slugify(text), "topics": [], "items": []}
            sections.append(section)
            topic = None
            continue
        if bold and re.match(r"\d+\.\d+", plain):
            topic = {"title": text, "id": "topic-" + plain.split()[0].replace(".", "-"), "desc": None, "items": []}
            section["topics"].append(topic)
            continue
        if section is None:
            intro.append(text)
            continue
        is_reading = "border-left-style:solid" in p.get("style", "")
        target = topic if topic is not None else section
        if topic is not None and topic["desc"] is None and not is_reading:
            topic["desc"] = text
            continue
        target["items"].append(("reading" if is_reading else "text", text))

    footnotes = {}
    for div in soup.body.find_all("div", recursive=False):
        a = div.find("a", id=re.compile(r"^ftnt\d+$"))
        if not a:
            continue
        p = a.find_parent("p")
        a.extract()
        footnotes[a["id"]] = re.sub(r"^\s+", "", text_of(p, []))
    return title, byline, intro, sections, [footnotes[n] for n in notes]


def items_html(items):
    out, readings = [], []
    def flush():
        if readings:
            out.append('<ul class="rl-readings">\n' + "".join(f"<li>{r}</li>\n" for r in readings) + "</ul>")
            readings.clear()
    for kind, text in items:
        if kind == "reading":
            readings.append(text)
        else:
            flush()
            out.append(f'<p class="rl-text">{text}</p>')
    flush()
    return "\n".join(out)


def page_html(slug, title, byline, intro, sections, notes):
    pdf = f"/media/{slug}.pdf"
    parts = [
        '<div class="rl-head">',
        f'<h1 class="page-title">{html.escape(title)}</h1>',
        f'<div class="rl-by">{html.escape(byline or "")}{" · " if byline else ""}<a href="{pdf}">Download PDF</a></div>',
        "</div>",
        "",
        '<div class="rl-intro">',
        *[f"<p>{p}</p>" for p in intro],
        "</div>",
        "",
        '<nav class="rl-jump" aria-label="Sections">',
        *[f'<a href="#{s["id"]}">{re.sub(r":.*", "", s["title"]) if s["title"].startswith("Unit") else s["title"]}</a>' for s in sections],
        "</nav>",
    ]
    for i, s in enumerate(sections):
        band = BANDS[min(i, len(BANDS) - 1)]
        parts += ["", f'<section class="rl-section" id="{s["id"]}">', f'<h2 class="rl-band rl-band--{band}">{s["title"]}</h2>']
        if s["items"]:
            parts.append(items_html(s["items"]))
        for t in s["topics"]:
            parts.append(f'<div class="rl-topic" id="{t["id"]}">')
            parts.append(f'<h3 class="rl-topic-head">{t["title"]}</h3>')
            if t["desc"]:
                parts.append(f'<p class="rl-desc">{t["desc"]}</p>')
            parts.append(items_html(t["items"]))
            parts.append("</div>")
        parts.append("</section>")
    if notes:
        parts += ["", '<section class="rl-notes" aria-label="Notes">', "<ol>"]
        parts += [f'<li id="note-{n}">{text} <a href="#note-ref-{n}" aria-label="Back to the text">↩</a></li>' for n, text in enumerate(notes, 1)]
        parts += ["</ol>", "</section>"]
    return "\n".join(parts) + "\n"


def make_pdf(src, dst, title):
    d = pymupdf.open(src)
    first = d[0].get_text().split()
    if len(first) <= 4 and len(d) > 1:  # only the tab name on page 1
        d.delete_page(0)
    d.set_metadata({**d.metadata, "title": title, "author": "Isaac Ahuvia"})
    d.save(dst, garbage=3, deflate=True)
    return len(d)


def main():
    slug, doc_html, doc_pdf = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]
    title, byline, intro, sections, notes = parse(doc_html.read_text(encoding="utf-8"))
    out = ROOT / "src" / "pages" / f"{slug}.html"
    out.write_text(page_html(slug, title, byline, intro, sections, notes), encoding="utf-8")
    pages = make_pdf(doc_pdf, ROOT / "site" / "media" / f"{slug}.pdf", title)
    counts = [(re.sub(r"<[^>]+>", "", s["title"]), len(s["topics"]),
               sum(len(t["items"]) for t in s["topics"]) + len(s["items"])) for s in sections]
    print(f"title: {title}\nbyline: {byline}\nintro paragraphs: {len(intro)}\nnotes: {notes}")
    for c in counts:
        print("  section:", c)
    print(f"wrote {out.relative_to(ROOT)} and site/media/{slug}.pdf ({pages} pages)")


if __name__ == "__main__":
    main()
