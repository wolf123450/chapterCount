import sys, types

# Stub out calibre before importing config
calibre_stub = types.ModuleType('calibre')
calibre_utils = types.ModuleType('calibre.utils')
calibre_config = types.ModuleType('calibre.utils.config')
calibre_config.JSONConfig = dict  # use plain dict as stand-in
calibre_stub.utils = calibre_utils
calibre_utils.config = calibre_config
sys.modules.setdefault('calibre', calibre_stub)
sys.modules.setdefault('calibre.utils', calibre_utils)
sys.modules.setdefault('calibre.utils.config', calibre_config)

from config import merge_config, DEFAULTS


def test_merge_config_null_values_use_defaults():
    per_book = {'manual_count': None, 'force_method': None, 'heading_tags': None}
    merged = merge_config(per_book, DEFAULTS.copy())
    assert merged['epub_heading_tags'] == ['h1', 'h2']


def test_merge_config_override_applies():
    per_book = {'heading_tags': ['h1'], 'force_method': 'toc', 'manual_count': None, 'heuristic_enabled': None}
    merged = merge_config(per_book, DEFAULTS.copy())
    assert merged['epub_heading_tags'] == ['h1']
    assert merged['force_method'] == 'toc'


def test_merge_config_manual_count_propagates():
    per_book = {'manual_count': 42, 'force_method': None, 'heading_tags': None, 'heuristic_enabled': None}
    merged = merge_config(per_book, DEFAULTS.copy())
    assert merged['manual_count'] == 42


def test_load_save_per_book_config_roundtrip(tmp_path):
    from config import load_per_book_config, save_per_book_config
    cfg = {'manual_count': 10, 'force_method': 'toc', 'heading_tags': None, 'heuristic_enabled': None}
    save_per_book_config(str(tmp_path), cfg)
    loaded = load_per_book_config(str(tmp_path))
    assert loaded == cfg
