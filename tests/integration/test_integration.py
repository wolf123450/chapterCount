"""
Integration tests that run inside Calibre.
Each test is a generator that yields (name, passed, detail) tuples.
run_all() collects all results.
"""
import os
import traceback

_FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')
_EPUB     = os.path.join(_FIXTURES, 'fixture.epub')
_MOBI     = os.path.join(_FIXTURES, 'fixture.mobi')
_PDF      = os.path.join(_FIXTURES, 'fixture.pdf')


def run_all():
    tests = [
        _test_epub_detector,
        _test_mobi_detector,
        _test_pdf_adapter_import,
        _test_config_roundtrip,
        _test_factory_dispatch,
    ]
    for test_fn in tests:
        try:
            for name, passed, detail in test_fn():
                yield name, passed, detail
        except Exception as exc:
            yield test_fn.__name__, False, traceback.format_exc(limit=3)


def _test_epub_detector():
    from calibre_plugins.chapter_count.detectors.epub_detector import EpubDetector
    result = EpubDetector().detect(_EPUB, {})
    yield 'EPUB detector: fixture.epub', result.count == 3 and result.method == 'toc', \
          f'count={result.count} method={result.method}'


def _test_mobi_detector():
    from calibre_plugins.chapter_count.detectors.mobi_detector import MobiDetector
    result = MobiDetector().detect(_MOBI, {'mobi_use_toc': True})
    yield 'MOBI detector: fixture.mobi', result.count == 3 and result.method == 'toc', \
          f'count={result.count} method={result.method}'


def _test_pdf_adapter_import():
    try:
        from calibre_plugins.chapter_count.detectors._calibre_pdf_adapter import (
            get_pdf_bookmarks, extract_pdf_text
        )
        yield 'PDF adapter: import', True, 'ok'
        bookmarks = get_pdf_bookmarks(_PDF)
        yield 'PDF adapter: get_pdf_bookmarks on fixture', isinstance(bookmarks, list), \
              f'returned {bookmarks!r}'
    except Exception as exc:
        yield 'PDF adapter: import', False, str(exc)


def _test_config_roundtrip():
    import tempfile, os
    from calibre_plugins.chapter_count.config import load_per_book_config, save_per_book_config

    with tempfile.TemporaryDirectory() as tmp:
        cfg = {'manual_count': 7, 'force_method': None, 'heading_tags': None, 'heuristic_enabled': None}
        save_per_book_config(tmp, cfg)
        loaded = load_per_book_config(tmp)
    yield 'Config: per-book roundtrip', loaded == cfg, f'saved={cfg!r} loaded={loaded!r}'


def _test_factory_dispatch():
    from calibre_plugins.chapter_count.detectors.factory import get_result_for_book
    result = get_result_for_book(_EPUB, 'epub', {})
    yield 'Factory: dispatches epub to EpubDetector', result.method == 'toc', \
          f'method={result.method} count={result.count}'

    result2 = get_result_for_book(_EPUB, 'cbz', {})
    yield 'Factory: unknown format → undetected', result2.method == 'undetected', \
          f'method={result2.method}'
