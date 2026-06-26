# tests/unit/test_epub_detector.py
import pytest
from detectors.epub_detector import EpubDetector


def test_detects_toc_from_ncx(epub_with_ncx):
    result = EpubDetector().detect(epub_with_ncx, {})
    assert result.count == 5
    assert result.method == 'toc'
    assert result.confidence == 'high'


def test_detects_toc_from_nav_xhtml(epub_with_nav):
    result = EpubDetector().detect(epub_with_nav, {})
    assert result.count == 3
    assert result.method == 'toc'
    assert result.confidence == 'high'


def test_falls_back_to_structural_headings(epub_with_headings_only):
    result = EpubDetector().detect(epub_with_headings_only, {'epub_use_toc': True, 'epub_use_structural': True, 'epub_heading_tags': ['h1', 'h2']})
    assert result.count == 3   # 2 h1 + 1 h2
    assert result.method == 'structural'
    assert result.confidence == 'medium'


def test_structural_respects_heading_tags(epub_with_headings_only):
    result = EpubDetector().detect(epub_with_headings_only, {'epub_use_toc': True, 'epub_use_structural': True, 'epub_heading_tags': ['h1']})
    assert result.count == 2   # only h1


def test_returns_undetected_for_empty_epub(epub_empty):
    result = EpubDetector().detect(epub_empty, {'epub_use_toc': True, 'epub_use_structural': True, 'epub_heading_tags': ['h1', 'h2']})
    assert result.method == 'undetected'
    assert result.count == 0


def test_returns_undetected_for_corrupted_file(corrupted_epub):
    result = EpubDetector().detect(corrupted_epub, {})
    assert result.method == 'undetected'


def test_force_method_toc_skips_structural(epub_with_headings_only):
    result = EpubDetector().detect(epub_with_headings_only, {'force_method': 'toc', 'epub_use_toc': True})
    assert result.method == 'undetected'  # forced toc, no toc → undetected (no fallthrough)


def test_force_method_structural_skips_toc(epub_with_ncx):
    result = EpubDetector().detect(epub_with_ncx, {'force_method': 'structural', 'epub_use_structural': True, 'epub_heading_tags': ['h1']})
    assert result.method == 'structural'  # forced structural, skips toc
