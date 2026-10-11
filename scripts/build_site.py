#!/usr/bin/env python3
"""Build the pages of isaacahuvia.com.

Usage: python3 scripts/build_site.py

Each page is src/pages/<name>.html (the content of the page) placed inside
src/layout.html (the head, menu and footer every page shares). The finished
pages are written into site/, which is the folder Netlify publishes as it is,
with no build step of its own.

Only the HTML pages, sitemap.xml and robots.txt in site/ are written here.
Everything else in site/ (styles, fonts, images, the CV, icons, _redirects) is
kept there directly and is never touched by this script.

Uses the Python standard library only.
"""
import datetime
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SITE = ROOT / "site"
ORIGIN = "https://isaacahuvia.com"
CV = "/media/Isaac%20Ahuvia%20CV.pdf"
SHARE_IMAGE = "/img/oystercatcher-home-2000.jpg"

MENU = [
    ("research", "Research", "/research/"),
    ("press", "Press", "/press/"),
    ("teaching", "Teaching", "/teaching/"),
    ("photography", "Photography", "/photography/"),
    ("contact", "Contact", "/contact/"),
    ("cv", "CV", CV),
]

HOME_DESCRIPTION = (
    "Isaac Ahuvia is a postdoctoral fellow at Northwestern University and an instructor at "
    "Harvard University. His research investigates mental illness identity, the online spaces "
    "that shape it, and how to promote healthier understandings of mental health and illness."
)

# source file, output file, address, title, menu item, class of <main>, description, listed in search engines
PAGES = [
    ("home.html", "index.html", "/", None, None, "wrap wrap--home", HOME_DESCRIPTION, True),
    ("research.html", "research/index.html", "/research/", "Research", "research", "wrap",
     "Peer-reviewed publications, other publications, manuscripts under review and work in progress by Isaac Ahuvia.", True),
    ("press.html", "press/index.html", "/press/", "Press", "press", "wrap",
     "Press coverage of Isaac Ahuvia's research, with interviews and op-eds.", True),
    ("teaching.html", "teaching/index.html", "/teaching/", "Teaching", "teaching", "wrap",
     "Courses taught by Isaac Ahuvia at Harvard University and Stony Brook University.", True),
    ("photography.html", "photography/index.html", "/photography/", "Photography", "photography", "wrap wrap--photos",
     "Bird photographs by Isaac Ahuvia.", True),
    ("contact.html", "contact/index.html", "/contact/", "Contact", "contact", "wrap wrap--contact",
     "Send a message to Isaac Ahuvia.", True),
    ("thanks.html", "contact/thanks/index.html", "/contact/thanks/", "Message sent", "contact", "wrap wrap--contact",
     "Your message has been sent.", False),
    ("404.html", "404.html", None, "Page not found", None, "wrap wrap--contact",
     "There is no page at this address.", False),
]

PERSON = {
    "@context": "https://schema.org",
    "@type": "Person",
    "name": "Isaac Ahuvia",
    "url": ORIGIN + "/",
    "image": ORIGIN + "/img/portrait-360.jpg",
    "jobTitle": "Postdoctoral Fellow",
    "affiliation": [
        {"@type": "CollegeOrUniversity", "name": "Northwestern University"},
        {"@type": "CollegeOrUniversity", "name": "Harvard University"},
    ],
    "alumniOf": [
        {"@type": "CollegeOrUniversity", "name": "Stony Brook University"},
        {"@type": "CollegeOrUniversity", "name": "University of Michigan"},
    ],
    "sameAs": [
        "https://scholar.google.com/citations?user=3vPivbUAAAAJ",
        "https://osf.io/c432p",
        "https://github.com/isaacahuvia",
        "https://www.linkedin.com/in/isaacahuvia",
    ],
}


def menu(current):
    lines = []
    for key, label, href in MENU:
        if key == current:
            lines.append(f'<a href="{href}" aria-current="page"><span>{label}</span></a>')
        else:
            lines.append(f'<a href="{href}">{label}</a>')
    return "\n".join(lines)


def social(title, description, address, is_home):
    if address is None:
        return ""
    lines = [
        f'<link rel="canonical" href="{ORIGIN}{address}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Isaac Ahuvia">',
        f'<meta property="og:title" content="{html.escape(title)}">',
        f'<meta property="og:description" content="{html.escape(description)}">',
        f'<meta property="og:url" content="{ORIGIN}{address}">',
        f'<meta property="og:image" content="{ORIGIN}{SHARE_IMAGE}">',
        '<meta property="og:image:alt" content="An American oystercatcher on a beach feeding one of its two chicks">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if is_home:
        lines.append('<script type="application/ld+json">' + json.dumps(PERSON, separators=(",", ":")) + "</script>")
    return "\n".join(lines) + "\n"


def main():
    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    year = str(datetime.date.today().year)
    listed = []
    for source, out, address, title, current, main_class, description, index in PAGES:
        content = (SRC / "pages" / source).read_text(encoding="utf-8")
        full_title = "Isaac Ahuvia" if title is None else f"{title} · Isaac Ahuvia"
        page = layout
        for key, value in {
            "title": html.escape(full_title),
            "description": html.escape(description),
            "robots": "" if index else '<meta name="robots" content="noindex">\n',
            "social": social(full_title, description, address, title is None) if index else "",
            "nav": menu(current),
            "main_class": main_class,
            "content": content,
            "year": year,
        }.items():
            page = page.replace("{{" + key + "}}", value)
        assert "{{" not in page, f"unfilled placeholder in {source}"
        target = SITE / out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        if index:
            listed.append(address)
        print("wrote", target.relative_to(ROOT))

    urls = "\n".join(f"  <url><loc>{ORIGIN}{address}</loc></url>" for address in listed)
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "\n</urlset>\n",
        encoding="utf-8",
    )
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n", encoding="utf-8")
    print("wrote site/sitemap.xml and site/robots.txt")


if __name__ == "__main__":
    main()
