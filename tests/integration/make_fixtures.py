#!/usr/bin/env python3
"""Run once: python tests/integration/make_fixtures.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import io, zipfile

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')
os.makedirs(FIXTURES, exist_ok=True)

# EPUB with NCX TOC (3 chapters)
def make_epub():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('mimetype', 'application/epub+zip')
        zf.writestr('META-INF/container.xml', '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf"
    media-type="application/oebps-package+xml"/></rootfiles>
</container>''')
        zf.writestr('OEBPS/content.opf', '''<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Fixture Book</dc:title></metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="c1"  href="ch1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx"><itemref idref="c1"/></spine>
</package>''')
        zf.writestr('OEBPS/toc.ncx', '''<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="c1"><navLabel><text>Chapter 1</text></navLabel><content src="ch1.xhtml"/></navPoint>
    <navPoint id="c2"><navLabel><text>Chapter 2</text></navLabel><content src="ch2.xhtml"/></navPoint>
    <navPoint id="c3"><navLabel><text>Chapter 3</text></navLabel><content src="ch3.xhtml"/></navPoint>
  </navMap>
</ncx>''')
        zf.writestr('OEBPS/ch1.xhtml',
            '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Chapter 1</h1></body></html>')
    return buf.getvalue()

with open(os.path.join(FIXTURES, 'fixture.epub'), 'wb') as f:
    f.write(make_epub())

# MOBI with nav points in raw bytes
def make_mobi():
    nav = b'<navPoint id="p1"><navPoint id="p2"><navPoint id="p3">'
    record_offset = 78 + 8
    header = (
        b'Fixture Book\x00' + b'\x00' * 20
        + b'\x00\x00' + b'\x00\x00' + b'\x00' * 16
        + b'BOOK' + b'MOBI' + b'\x00' * 8 + b'\x00\x01'
        + record_offset.to_bytes(4, 'big') + b'\x00\x00\x00\x00'
    )
    return header + nav

with open(os.path.join(FIXTURES, 'fixture.mobi'), 'wb') as f:
    f.write(make_mobi())

# Minimal PDF (no bookmarks — adapter returns [])
pdf = (
    b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
    b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
    b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n'
    b'xref\n0 4\n0000000000 65535 f \n'
    b'trailer<</Size 4/Root 1 0 R>>\n%%EOF\n'
)
with open(os.path.join(FIXTURES, 'fixture.pdf'), 'wb') as f:
    f.write(pdf)

print('Fixtures written to', FIXTURES)
