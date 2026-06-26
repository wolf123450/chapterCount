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
