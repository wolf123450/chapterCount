"""
Integration tests that run inside Calibre.
Each test is a generator that yields (name, passed, detail) tuples.
run_all() collects all results.

Fixture files live inside the plugin ZIP, not on the real filesystem.
_fixture() extracts them to a tempfile so detectors can open them normally.
"""
import contextlib
import os
import pkgutil
import tempfile
import traceback

_PKG = 'calibre_plugins.chapter_count.tests.integration'


@contextlib.contextmanager
def _fixture(name):
    """Yield a real filesystem path to a bundled fixture file."""
    # During development the fixtures directory exists on disk
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', name)
    if os.path.exists(local):
        yield local
        return

    # Inside Calibre's ZIP: pkgutil.get_data() returns None when the loader
    # doesn't implement get_data(); fall back to Calibre's get_resources()
    data = pkgutil.get_data(_PKG, f'fixtures/{name}')
    if data is None:
        data = get_resources(f'tests/integration/fixtures/{name}')
    suffix = os.path.splitext(name)[1]
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(fd, data)
        os.close(fd)
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


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
        except Exception:
            yield test_fn.__name__, False, traceback.format_exc(limit=3)


def _test_epub_detector():
    from calibre_plugins.chapter_count.detectors.epub_detector import EpubDetector
    with _fixture('fixture.epub') as path:
        result = EpubDetector().detect(path, {})
    yield 'EPUB detector: fixture.epub', result.count == 3 and result.method == 'toc', \
          f'count={result.count} method={result.method}'


def _test_mobi_detector():
    from calibre_plugins.chapter_count.detectors.mobi_detector import MobiDetector
    with _fixture('fixture.mobi') as path:
        result = MobiDetector().detect(path, {'mobi_use_toc': True})
    yield 'MOBI detector: fixture.mobi', result.count == 3 and result.method == 'toc', \
          f'count={result.count} method={result.method}'


def _test_pdf_adapter_import():
    try:
        from calibre_plugins.chapter_count.detectors._calibre_pdf_adapter import (
            get_pdf_bookmarks, extract_pdf_text
        )
        yield 'PDF adapter: import', True, 'ok'
        with _fixture('fixture.pdf') as path:
            bookmarks = get_pdf_bookmarks(path)
        yield 'PDF adapter: get_pdf_bookmarks on fixture', isinstance(bookmarks, list), \
              f'returned {bookmarks!r}'
    except Exception as exc:
        yield 'PDF adapter: import', False, str(exc)


def _test_config_roundtrip():
    import tempfile
    from calibre_plugins.chapter_count.config import load_per_book_config, save_per_book_config

    with tempfile.TemporaryDirectory() as tmp:
        cfg = {'manual_count': 7, 'force_method': None, 'heading_tags': None, 'heuristic_enabled': None}
        save_per_book_config(tmp, cfg)
        loaded = load_per_book_config(tmp)
    yield 'Config: per-book roundtrip', loaded == cfg, f'saved={cfg!r} loaded={loaded!r}'


def _test_factory_dispatch():
    from calibre_plugins.chapter_count.detectors.factory import get_result_for_book
    with _fixture('fixture.epub') as path:
        result = get_result_for_book(path, 'epub', {})
    yield 'Factory: dispatches epub to EpubDetector', result.method == 'toc', \
          f'method={result.method} count={result.count}'

    with _fixture('fixture.epub') as path:
        result2 = get_result_for_book(path, 'cbz', {})
    yield 'Factory: unknown format → undetected', result2.method == 'undetected', \
          f'method={result2.method}'
