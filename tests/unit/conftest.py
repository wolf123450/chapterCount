# tests/unit/conftest.py
import io
import os
import zipfile
import pytest


def _make_epub(toc_ncx=None, nav_xhtml=None, spine_content=None, opf_toc_attr=''):
    """Build a minimal EPUB ZIP in memory and return bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('mimetype', 'application/epub+zip')
        zf.writestr('META-INF/container.xml', '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>''')

        manifest_items = [
            '<item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>',
        ]
        if toc_ncx:
            manifest_items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
        if nav_xhtml:
            manifest_items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')

        opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test Book</dc:title>
  </metadata>
  <manifest>
    {''.join(manifest_items)}
  </manifest>
  <spine {opf_toc_attr}>
    <itemref idref="ch1"/>
  </spine>
</package>'''
        zf.writestr('OEBPS/content.opf', opf)

        if toc_ncx:
            zf.writestr('OEBPS/toc.ncx', toc_ncx)
        if nav_xhtml:
            zf.writestr('OEBPS/nav.xhtml', nav_xhtml)

        content = spine_content or '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Chapter 1</h1><p>Text</p></body></html>'
        zf.writestr('OEBPS/ch1.xhtml', content)

    return buf.getvalue()


def _ncx(chapters):
    nav_points = '\n'.join(
        f'<navPoint id="ch{i}"><navLabel><text>Chapter {i}</text></navLabel>'
        f'<content src="ch{i}.xhtml"/></navPoint>'
        for i in range(1, chapters + 1)
    )
    return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>{nav_points}</navMap>
</ncx>'''


def _nav(chapters):
    items = '\n'.join(f'<li><a href="ch{i}.xhtml">Chapter {i}</a></li>' for i in range(1, chapters + 1))
    return f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body>
  <nav epub:type="toc">
    <ol>{items}</ol>
  </nav>
</body>
</html>'''


@pytest.fixture
def epub_with_ncx(tmp_path):
    p = tmp_path / 'book.epub'
    p.write_bytes(_make_epub(toc_ncx=_ncx(5)))
    return str(p)


@pytest.fixture
def epub_with_nav(tmp_path):
    p = tmp_path / 'book.epub'
    p.write_bytes(_make_epub(nav_xhtml=_nav(3)))
    return str(p)


@pytest.fixture
def epub_with_headings_only(tmp_path):
    content = '''<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1>Chapter One</h1><p>Text</p>
<h1>Chapter Two</h1><p>Text</p>
<h2>Section 2.1</h2><p>Text</p>
</body></html>'''
    p = tmp_path / 'book.epub'
    p.write_bytes(_make_epub(spine_content=content))
    return str(p)


@pytest.fixture
def epub_empty(tmp_path):
    p = tmp_path / 'book.epub'
    # Explicitly pass spine content with no heading tags so structural scan finds nothing
    p.write_bytes(_make_epub(spine_content='<html xmlns="http://www.w3.org/1999/xhtml"><body><p>Text only, no headings.</p></body></html>'))
    return str(p)


@pytest.fixture
def corrupted_epub(tmp_path):
    p = tmp_path / 'bad.epub'
    p.write_bytes(b'not a zip file at all')
    return str(p)


def _make_mobi(nav_points=0, nav_li=0):
    """
    Build minimal MOBI bytes containing an NCX fragment in plain text.
    Real MOBI files compress content, but this fixture embeds the NCX
    uncompressed so the byte-scan detector can find it.
    """
    ncx_fragment = b''
    if nav_points > 0:
        ncx_fragment = (b'<navPoint id="p1">' * nav_points)
    elif nav_li > 0:
        ncx_fragment = (
            b'<nav epub:type="toc"><ol>'
            + b'<li><a>Chapter</a></li>' * nav_li
            + b'</ol></nav>'
        )

    # Minimal PalmDOC database header (78 bytes) + 1 record pointing to offset 78
    # Record 0 at offset 78 contains our NCX fragment directly (no real MOBI header)
    # This is not a valid MOBI but is sufficient for the byte-scan detector tests.
    record_offset = 78 + 8   # header (78) + one record descriptor (8)
    header = (
        b'Test Book\x00' + b'\x00' * 22          # name (32 bytes)
        + b'\x00\x00'                             # attributes
        + b'\x00\x00'                             # version
        + b'\x00' * 8                             # dates
        + b'\x00' * 8                             # app/sort info
        + b'BOOK'                                 # type
        + b'MOBI'                                 # creator
        + b'\x00' * 4                             # unique ID seed
        + b'\x00' * 4                             # next record list ID
        + b'\x00\x01'                             # num records = 1
        # Record 0 descriptor: 4-byte offset + 4-byte attribs
        + record_offset.to_bytes(4, 'big')
        + b'\x00\x00\x00\x00'
    )
    return header + ncx_fragment


@pytest.fixture
def mobi_with_nav_points(tmp_path):
    p = tmp_path / 'book.mobi'
    p.write_bytes(_make_mobi(nav_points=7))
    return str(p)


@pytest.fixture
def mobi_with_nav_li(tmp_path):
    p = tmp_path / 'book.mobi'
    p.write_bytes(_make_mobi(nav_li=4))
    return str(p)


@pytest.fixture
def mobi_no_toc(tmp_path):
    p = tmp_path / 'book.mobi'
    p.write_bytes(_make_mobi())
    return str(p)


@pytest.fixture
def corrupted_mobi(tmp_path):
    p = tmp_path / 'bad.mobi'
    p.write_bytes(b'\x00\x01\x02\x03')
    return str(p)
