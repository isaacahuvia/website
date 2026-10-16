# isaacahuvia.com

Isaac Ahuvia's personal website. It is a small static site: plain HTML, one
stylesheet, self-hosted fonts and photos. Netlify publishes the `site/` folder
from the `master` branch exactly as it is; nothing is built on Netlify.

## Layout of the repo

| Path | What it is |
| --- | --- |
| `site/` | The published site. Netlify serves this folder. |
| `src/layout.html` | The head, menu and footer shared by every page. |
| `src/pages/` | The content of each page (home, research, press, teaching, photography, contact, the "message sent" page and the "not found" page). |
| `scripts/build_site.py` | Puts each page into the layout and writes the HTML into `site/`. |
| `scripts/cv_to_pdf.py` | Converts the CV from Word to PDF with LibreOffice. |
| `scripts/cv_source.json` | Which version of the CV on Google Drive the published PDF was made from. |
| `netlify.toml` | Tells Netlify to publish `site/` without a build. |

## Changing a page

1. Edit the page in `src/pages/` (or `src/layout.html` for the menu and footer).
2. Run `python3 scripts/build_site.py`. It needs only Python 3.
3. Commit the changed files in both `src/` and `site/`, and push to `master`.

The HTML pages, `sitemap.xml` and `robots.txt` in `site/` are written by the
build script, so edit their sources, not the files themselves. Everything else
in `site/` is kept there directly:

- `site/css/site.css`: all styles. Colours, type and spacing follow Isaac's visual identity.
- `site/fonts/`: Source Serif 4 and Source Sans 3 (SIL Open Font License), reduced to Latin characters.
- `site/img/`: photos, each at two sizes.
- `site/media/Isaac Ahuvia CV.pdf`: the CV.
- `site/favicon.svg`, `site/favicon.ico`, `site/apple-touch-icon.png`: the tab icon.
- `site/_redirects`: sends addresses from the previous version of the site to the new pages.

To look at the site locally: `python3 -m http.server --directory site 8000`,
then open http://localhost:8000.

## The CV

The CV is written in Word and kept on Google Drive. A weekly scheduled task
finds the newest version, converts it with `scripts/cv_to_pdf.py`, checks the
result and commits it to `site/media/Isaac Ahuvia CV.pdf`. The file name never
changes, so links to the CV keep working.

## Reading lists

A reading list is written as a Google Doc and published twice: as a page of the
site and as a PDF. Export the doc as HTML and as PDF, then run

    python3 scripts/reading_list.py social-construction-reading-list doc.html doc.pdf
    python3 scripts/build_site.py

The first command writes `src/pages/<name>.html` and `site/media/<name>.pdf`
(it needs `bs4` and `pymupdf`); the second builds the page at `/<name>/`.
`scripts/reading_list.py` describes what it expects of the doc. A new list
also needs one line in `PAGES` in `scripts/build_site.py` and links from the
Teaching page.

## The contact form

The form on `/contact/` is a Netlify form named `contact` with the fields
`name`, `email` and `message`. Netlify finds it when the site is deployed and
sends each message to Isaac by email (set under Forms > Submission
notifications in Netlify). After sending, visitors land on `/contact/thanks/`.

## Photos

To add a photo, save it in `site/img/` at two widths (for example 800 and 1600
pixels, as `name-800.jpg` and `name-1600.jpg`), without embedded location data,
and add a `<figure>` to `src/pages/photography.html` following the ones there.
In each row, a photo's `flex` value is its width divided by its height.
