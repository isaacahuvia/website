#!/usr/bin/env python3
"""Convert the CV from Word (.docx) to PDF with LibreOffice.

Usage: python3 cv_to_pdf.py <cv.docx> <out.pdf>

The Word file is never changed. The conversion works on a temporary copy and
makes six adjustments so that LibreOffice lays the document out the way
Word does:

1. Fonts embedded in the .docx (the bullet font) are made available to
   LibreOffice, so bullets keep their size.
2. A centred paragraph that carries a left indent with an equal hanging indent
   (the name at the top) has that indent removed. Word centres such a line on
   the page; LibreOffice pushes it to the left margin.
3. An empty paragraph with a bottom border that is followed by another
   paragraph with the same border loses its border. Word draws one rule under
   such a group; LibreOffice draws a stray rule when the group is split across
   two pages.

4. A ruled section heading is kept on the same page as the line after it, so
   no heading is left alone at the foot of a page.
5. Round list bullets set as U+25CF in a symbol font that has no such glyph
   (as Google Docs writes them) become ordinary bullets (U+2022) in the text
   font. Word shows them as small bullets; LibreOffice otherwise substitutes
   a large glyph from another font, which also makes those lines taller.
6. A field with no stored result (the page numbers in the footer, as Google
   Docs writes them) is given a result that carries the field's own font and
   size. Word shows such a number in the font set on the field; LibreOffice
   otherwise falls back to the document's default font (Calibri).

Times New Roman is replaced by Liberation Serif, which has the same metrics.
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

PARA = re.compile(r"<w:p[ >].*?</w:p>", re.S)
BORDER = re.compile(r"<w:pBdr>.*?</w:pBdr>", re.S)
HANGING_CENTRE = re.compile(r'<w:ind w:left="(\d+)" w:hanging="\1"/>(?=<w:jc w:val="center"/>)')


def patch_document(xml: str) -> tuple[str, dict]:
    notes = {"centred_indent_removed": 0, "empty_border_removed": 0, "headings_kept_with_next": 0}

    xml, n = HANGING_CENTRE.subn("", xml)
    notes["centred_indent_removed"] = n

    paras = list(PARA.finditer(xml))
    out, last = [], 0
    for i, m in enumerate(paras):
        p = m.group(0)
        border = BORDER.search(p)
        has_text = bool(re.search(r"<w:t[ >]|<w:drawing|<w:br[ /]|<w:tab/>", p))
        nxt = paras[i + 1].group(0) if i + 1 < len(paras) else ""
        nxt_border = BORDER.search(nxt)
        if border and not has_text and nxt_border and nxt_border.group(0) == border.group(0):
            p = p.replace(border.group(0), "", 1)
            notes["empty_border_removed"] += 1
        elif border and has_text and 'w:val="single"' in border.group(0) and "<w:keepNext" not in p:
            # A ruled section heading stays with the line that follows it.
            p = p.replace("<w:pPr>", '<w:pPr><w:keepNext w:val="1"/>', 1)
            notes["headings_kept_with_next"] += 1
        out.append(xml[last:m.start()])
        out.append(p)
        last = m.end()
    out.append(xml[last:])
    return "".join(out), notes


# One run holding a whole field with nothing between "separate" and "end".
EMPTY_FIELD = re.compile(
    r"<w:r(?: [^>]*)?>(<w:rPr>(?:(?!</w:rPr>).)*</w:rPr>)?"
    r'<w:fldChar w:fldCharType="begin"/>'
    r"(<w:instrText[^>]*>[^<]*</w:instrText>)"
    r'<w:fldChar w:fldCharType="separate"/>'
    r'<w:fldChar w:fldCharType="end"/></w:r>',
    re.S,
)


def patch_fields(xml: str) -> tuple[str, int]:
    """Give empty fields a result run with the field's own character formatting."""

    def fix(m: re.Match) -> str:
        rpr, instr = m.group(1) or "", m.group(2)
        run = lambda inner: f"<w:r>{rpr}{inner}</w:r>"
        return (
            run('<w:fldChar w:fldCharType="begin"/>')
            + run(instr)
            + run('<w:fldChar w:fldCharType="separate"/>')
            + run("<w:t>1</w:t>")
            + run('<w:fldChar w:fldCharType="end"/>')
        )

    return EMPTY_FIELD.subn(fix, xml)


LEVEL = re.compile(r"<w:lvl [^>]*>.*?</w:lvl>", re.S)


def patch_numbering(xml: str) -> tuple[str, int]:
    count = 0

    def fix(m: re.Match) -> str:
        nonlocal count
        lvl = m.group(0)
        if 'w:lvlText w:val="●"' not in lvl:
            return lvl
        count += 1
        lvl = lvl.replace('w:lvlText w:val="●"', 'w:lvlText w:val="•"')
        return lvl.replace("Noto Sans Symbols", "Times New Roman")

    return LEVEL.sub(fix, xml), count


def main() -> int:
    src, dst = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
    work = pathlib.Path(tempfile.mkdtemp(prefix="cv2pdf-"))
    home = work / "home"
    fonts = home / ".fonts"
    fonts.mkdir(parents=True)

    patched = work / "cv.docx"
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(patched, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                text, notes = patch_document(data.decode("utf-8"))
                data = text.encode("utf-8")
                print("adjustments:", notes)
            if item.filename == "word/numbering.xml":
                text, n = patch_numbering(data.decode("utf-8"))
                data = text.encode("utf-8")
                print("bullet levels adjusted:", n)
            if re.fullmatch(r"word/(document|header\d*|footer\d*)\.xml", item.filename):
                text, n = patch_fields(data.decode("utf-8"))
                if n:
                    data = text.encode("utf-8")
                    print(f"fields given their own font in {item.filename}:", n)
            if item.filename.startswith("word/fonts/") and item.filename.lower().endswith((".ttf", ".otf")):
                (fonts / pathlib.Path(item.filename).name).write_bytes(data)
            zout.writestr(item, data)

    env = {"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    subprocess.run(["fc-cache", "-f", str(fonts)], env=env, check=False, capture_output=True)
    run = subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(work), str(patched)],
        env=env, capture_output=True, text=True, timeout=300,
    )
    made = work / "cv.pdf"
    if not made.exists():
        print(run.stdout, run.stderr, file=sys.stderr)
        return 1
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(made, dst)
    shutil.rmtree(work, ignore_errors=True)
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
