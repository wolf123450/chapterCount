"""
Shim for Calibre's internal PDF API.

All Calibre-specific imports are isolated here. If a future Calibre version
changes the internal API, only this file needs updating. The PDF detector
depends only on the two public functions below.
"""


def get_pdf_bookmarks(pdf_path: str) -> list:
    """Return a flat list of top-level PDF bookmark titles, or [] if none."""
    try:
        from calibre.utils.podofo import get_podofo
        podofo = get_podofo()
        if podofo is None:
            return []
        doc = podofo.PDFDoc()
        doc.load(pdf_path)
        toc = doc.get_toc()
        return [entry['title'] for entry in toc] if toc else []
    except Exception:
        return []


def extract_pdf_text(pdf_path: str) -> str:
    """Return plain text extracted from all pages, or '' on failure."""
    try:
        from calibre.ebooks.pdf.reflow import PDFInput
        from calibre.utils.logging import default_log
        opts = type('opts', (), {'input_encoding': None, 'debug_pipeline': None})()
        text = PDFInput().convert(pdf_path, opts, 'html', default_log)
        return text or ''
    except Exception:
        return ''
