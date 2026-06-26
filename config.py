import json
import os

try:
    from calibre.utils.config import JSONConfig
    PREFS = JSONConfig('plugins/chapter_count')
except (ImportError, TypeError, ValueError):
    # ImportError: calibre not installed (testing)
    # TypeError/ValueError: JSONConfig stubbed as dict (testing)
    PREFS = {}

DEFAULTS = {
    'auto_scan_on_add':       True,
    'notify_on_error':        True,
    'overwrite_policy':       'preserve_manual',  # 'always' | 'never' | 'preserve_manual'
    'batch_size':             50,
    'count_column':           '#chapter_count',
    'method_column':          '#chapter_detection_method',
    'epub_use_toc':           True,
    'epub_use_structural':    True,
    'epub_heading_tags':      ['h1', 'h2'],
    'mobi_use_toc':           True,
    'pdf_use_bookmarks':      True,
    'pdf_heuristic_enabled':  False,
    'pdf_heuristic_patterns': [
        r'^Chapter\s+(\d+|[A-Z][a-z]+)',
        r'^CHAPTER\s+',
        r'^Part\s+',
    ],
}

if hasattr(PREFS, 'defaults'):
    PREFS.defaults.update(DEFAULTS)

_PER_BOOK_FILE = 'chaptercount_config.json'

_PER_BOOK_KEYS = {
    'heading_tags':       'epub_heading_tags',
    'heuristic_enabled':  'pdf_heuristic_enabled',
    'force_method':       'force_method',
    'manual_count':       'manual_count',
}


def load_per_book_config(book_data_dir: str) -> dict:
    path = os.path.join(book_data_dir, _PER_BOOK_FILE)
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_per_book_config(book_data_dir: str, cfg: dict) -> None:
    path = os.path.join(book_data_dir, _PER_BOOK_FILE)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)


def merge_config(per_book: dict, global_prefs: dict) -> dict:
    """Return global_prefs overridden by any non-None per-book values."""
    merged = dict(global_prefs)
    merged.setdefault('force_method', None)
    merged.setdefault('manual_count', None)
    for per_key, global_key in _PER_BOOK_KEYS.items():
        value = per_book.get(per_key)
        if value is not None:
            merged[global_key] = value
            if per_key in ('force_method', 'manual_count'):
                merged[per_key] = value
    return merged
