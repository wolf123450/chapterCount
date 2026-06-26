# Calibre Chapter Count Plugin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Calibre plugin that detects and stores chapter counts for EPUB, MOBI/AZW3, and PDF books using tiered detection (TOC → structural → heuristic → manual), with per-book configuration and a live in-Calibre diagnostic test runner.

**Architecture:** A `BaseDetector` ABC with format-specific subclasses (no Calibre imports) drives detection; a `factory.py` dispatches to the right detector and applies per-book overrides; `column_manager.py` applies the overwrite policy; `batch_processor.py` runs everything in a QThread with Qt signal progress reporting. The `_calibre_pdf_adapter.py` shim is the single file that touches Calibre's internal PDF API.

**Tech Stack:** Python 3.8+, Calibre 5+ (embedded Python + PyQt5), stdlib only for detectors (`zipfile`, `xml.etree`, `struct`, `re`, `json`), `calibre.utils.config.JSONConfig` for prefs, `calibre.gui2.actions.InterfaceAction` for the plugin entry point, `pytest` for unit tests (run outside Calibre).

---

## File Map

| File | Responsibility |
|---|---|
| `__init__.py` | Plugin descriptor (`InterfaceActionBase`) — metadata + prefs wiring |
| `action.py` | Calibre GUI action (`InterfaceAction`) — toolbar, menus, hooks |
| `config.py` | Global prefs (JSONConfig) + per-book config load/save/merge |
| `column_manager.py` | Custom column creation + overwrite policy enforcement |
| `batch_processor.py` | `QThread` subclass + Qt signals for batched scanning |
| `detectors/__init__.py` | Empty |
| `detectors/base.py` | `DetectionResult` dataclass + `BaseDetector` ABC + `UNDETECTED` sentinel |
| `detectors/epub_detector.py` | EPUB: toc.ncx / nav.xhtml → h1/h2 spine scan |
| `detectors/mobi_detector.py` | MOBI/AZW3: byte scan for embedded NCX |
| `detectors/pdf_detector.py` | PDF: bookmarks → heuristic text scan (via adapter) |
| `detectors/_calibre_pdf_adapter.py` | Shim for Calibre's internal PDF API |
| `detectors/factory.py` | Extension → detector + manual override + force_method |
| `ui/__init__.py` | Empty |
| `ui/preferences_widget.py` | `ConfigWidget` subclass — all prefs fields |
| `ui/book_config_dialog.py` | Per-book override `QDialog` |
| `ui/batch_progress_dialog.py` | Bulk scan progress `QDialog` + book selector |
| `ui/test_runner_dialog.py` | Integration test runner `QDialog` |
| `tests/unit/conftest.py` | sys.path + fixture builders |
| `tests/unit/test_base.py` | `DetectionResult` + `BaseDetector` tests |
| `tests/unit/test_epub_detector.py` | EPUB detector tests |
| `tests/unit/test_mobi_detector.py` | MOBI detector tests |
| `tests/unit/test_pdf_detector.py` | PDF detector tests (adapter mocked) |
| `tests/unit/test_factory.py` | Factory dispatch + override tests |
| `tests/unit/test_config.py` | `merge_config` tests |
| `tests/integration/__init__.py` | Empty |
| `tests/integration/fixtures/` | Bundled minimal EPUB, MOBI, PDF shipped in plugin ZIP |
| `tests/integration/test_integration.py` | In-Calibre integration tests |
| `build.py` | Packages plugin as distributable ZIP |
| `requirements-test.txt` | `pytest` only |
| `conftest.py` | Root-level: adds project root to sys.path for unit tests |

---

## Task 1: Project Scaffold

**Files:**
- Create: `__init__.py`
- Create: `action.py`
- Create: `detectors/__init__.py`
- Create: `ui/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/fixtures/` (directory)
- Create: `requirements-test.txt`
- Create: `conftest.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p detectors ui tests/unit/fixtures tests/integration/fixtures
touch detectors/__init__.py ui/__init__.py tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
```

- [ ] **Step 2: Create `requirements-test.txt`**

```
pytest
```

- [ ] **Step 3: Create root `conftest.py`** (adds project root to sys.path so unit tests can import `detectors.*` directly)

```python
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 4: Create `__init__.py`** (Calibre plugin descriptor)

```python
from calibre.customize import InterfaceActionBase


class ChapterCountPlugin(InterfaceActionBase):
    name                    = 'Chapter Count'
    description             = 'Count chapters in ebooks and store in custom columns'
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = 'Your Name'
    version                 = (0, 1, 0)
    minimum_calibre_version = (5, 0, 0)
    actual_plugin           = 'calibre_plugins.chapter_count.action:ChapterCountAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.chapter_count.ui.preferences_widget import PreferencesWidget
        return PreferencesWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
```

- [ ] **Step 5: Create stub `action.py`** (will be completed in Task 15)

```python
from calibre.gui2.actions import InterfaceAction


class ChapterCountAction(InterfaceAction):
    name        = 'Chapter Count'
    action_spec = ('Chapter Count', None, 'Count chapters in selected books', None)

    def genesis(self):
        self.qaction.triggered.connect(self.count_selected)

    def initialization_complete(self):
        pass

    def count_selected(self):
        pass
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: scaffold project structure and plugin descriptor"
```

---

## Task 2: DetectionResult + BaseDetector

**Files:**
- Create: `detectors/base.py`
- Create: `tests/unit/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_base.py
from detectors.base import DetectionResult, BaseDetector, UNDETECTED


def test_detection_result_column_value():
    r = DetectionResult(count=12, method='toc', confidence='high')
    assert r.column_value() == 'toc · high'


def test_undetected_sentinel():
    assert UNDETECTED.count == 0
    assert UNDETECTED.method == 'undetected'
    assert UNDETECTED.confidence == 'low'


def test_base_detector_is_abstract():
    import pytest
    with pytest.raises(TypeError):
        BaseDetector()
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_base.py -v
```

Expected: `ModuleNotFoundError: No module named 'detectors.base'`

- [ ] **Step 3: Create `detectors/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DetectionResult:
    count: int
    method: str      # "toc" | "structural" | "heuristic" | "manual" | "undetected"
    confidence: str  # "high" | "medium" | "low"

    def column_value(self) -> str:
        return f'{self.method} · {self.confidence}'


UNDETECTED = DetectionResult(count=0, method='undetected', confidence='low')


class BaseDetector(ABC):
    @abstractmethod
    def detect(self, book_path: str, per_book_config: dict) -> DetectionResult:
        ...
```

- [ ] **Step 4: Run to confirm pass**

```bash
pytest tests/unit/test_base.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add detectors/base.py tests/unit/test_base.py
git commit -m "feat: add DetectionResult dataclass and BaseDetector ABC"
```

---

## Task 3: Config Module

**Files:**
- Create: `config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing tests** (only tests pure Python merge logic — JSONConfig is integration-tested)

```python
# tests/unit/test_config.py
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Create `config.py`**

```python
import json
import os

try:
    from calibre.utils.config import JSONConfig
    PREFS = JSONConfig('plugins/chapter_count')
except ImportError:
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
```

- [ ] **Step 4: Run to confirm pass**

```bash
pytest tests/unit/test_config.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add config.py tests/unit/test_config.py
git commit -m "feat: add config module with global prefs and per-book config merge"
```

---

## Task 4: EPUB Fixture Builder + EPUB Detector

**Files:**
- Create: `tests/unit/conftest.py`
- Create: `detectors/epub_detector.py`
- Create: `tests/unit/test_epub_detector.py`

- [ ] **Step 1: Create `tests/unit/conftest.py`** with fixture builders for EPUB, MOBI, and PDF test files

```python
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
    p.write_bytes(_make_epub())
    return str(p)


@pytest.fixture
def corrupted_epub(tmp_path):
    p = tmp_path / 'bad.epub'
    p.write_bytes(b'not a zip file at all')
    return str(p)
```

- [ ] **Step 2: Write the failing test**

```python
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
```

- [ ] **Step 3: Run to confirm failure**

```bash
pytest tests/unit/test_epub_detector.py -v
```

Expected: `ModuleNotFoundError: No module named 'detectors.epub_detector'`

- [ ] **Step 4: Create `detectors/epub_detector.py`**

```python
import zipfile
import xml.etree.ElementTree as ET
from typing import Optional

from .base import BaseDetector, DetectionResult, UNDETECTED

_NCX_NS   = 'http://www.daisy.org/z3986/2005/ncx/'
_OPF_NS   = 'http://www.idpf.org/2007/opf'
_XHTML_NS = 'http://www.w3.org/1999/xhtml'
_EPUB_NS  = 'http://www.idpf.org/2007/ops'

_CONTAINER = 'META-INF/container.xml'
_CONTAINER_NS = 'urn:oasis:names:tc:opendocument:xmlns:container'


class EpubDetector(BaseDetector):

    def detect(self, book_path: str, per_book_config: dict) -> DetectionResult:
        try:
            return self._detect(book_path, per_book_config)
        except Exception:
            return UNDETECTED

    def _detect(self, book_path: str, cfg: dict) -> DetectionResult:
        force = cfg.get('force_method')
        use_toc        = cfg.get('epub_use_toc', True)
        use_structural = cfg.get('epub_use_structural', True)
        heading_tags   = cfg.get('epub_heading_tags', ['h1', 'h2'])

        with zipfile.ZipFile(book_path, 'r') as zf:
            names = zf.namelist()

            if force != 'structural' and use_toc:
                result = self._try_toc(zf, names)
                if result is not None and result.count > 0:
                    return result
                if force == 'toc':
                    return UNDETECTED

            if force != 'toc' and use_structural:
                result = self._try_structural(zf, names, heading_tags)
                if result is not None and result.count > 0:
                    return result

        return UNDETECTED

    def _try_toc(self, zf: zipfile.ZipFile, names: list) -> Optional[DetectionResult]:
        # EPUB2: toc.ncx
        ncx_path = next((n for n in names if n.endswith('toc.ncx')), None)
        if ncx_path:
            root = ET.fromstring(zf.read(ncx_path))
            nav_map = root.find(f'{{{_NCX_NS}}}navMap')
            if nav_map is not None:
                top = nav_map.findall(f'{{{_NCX_NS}}}navPoint')
                if top:
                    return DetectionResult(count=len(top), method='toc', confidence='high')

        # EPUB3: nav.xhtml
        nav_path = next((n for n in names if n.endswith('nav.xhtml') or n.endswith('nav.htm')), None)
        if nav_path:
            root = ET.fromstring(zf.read(nav_path))
            for nav in root.iter(f'{{{_XHTML_NS}}}nav'):
                if 'toc' in nav.get(f'{{{_EPUB_NS}}}type', ''):
                    ol = nav.find(f'{{{_XHTML_NS}}}ol')
                    if ol is not None:
                        items = ol.findall(f'{{{_XHTML_NS}}}li')
                        if items:
                            return DetectionResult(count=len(items), method='toc', confidence='high')

        return None

    def _try_structural(self, zf: zipfile.ZipFile, names: list, heading_tags: list) -> Optional[DetectionResult]:
        if _CONTAINER not in names:
            return None
        container_root = ET.fromstring(zf.read(_CONTAINER))
        opf_path_el = container_root.find(f'.//{{{_CONTAINER_NS}}}rootfile')
        if opf_path_el is None:
            return None
        opf_path = opf_path_el.get('full-path', '')

        if opf_path not in names:
            return None
        opf_root  = ET.fromstring(zf.read(opf_path))
        opf_dir   = opf_path.rsplit('/', 1)[0] if '/' in opf_path else ''
        spine     = opf_root.find(f'{{{_OPF_NS}}}spine')
        manifest  = opf_root.find(f'{{{_OPF_NS}}}manifest')
        if spine is None or manifest is None:
            return None

        id_to_href = {
            item.get('id'): item.get('href', '')
            for item in manifest.findall(f'{{{_OPF_NS}}}item')
        }

        count = 0
        for itemref in spine.findall(f'{{{_OPF_NS}}}itemref'):
            href      = id_to_href.get(itemref.get('idref', ''), '')
            full_path = f'{opf_dir}/{href}' if opf_dir else href
            if full_path not in names:
                continue
            content_root = ET.fromstring(zf.read(full_path))
            for tag in heading_tags:
                count += len(content_root.findall(f'.//{{{_XHTML_NS}}}{tag}'))

        return DetectionResult(count=count, method='structural', confidence='medium') if count else None
```

- [ ] **Step 5: Run to confirm pass**

```bash
pytest tests/unit/test_epub_detector.py -v
```

Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add detectors/epub_detector.py tests/unit/conftest.py tests/unit/test_epub_detector.py
git commit -m "feat: add EPUB detector with TOC and structural heading detection"
```

---

## Task 5: MOBI Detector

**Files:**
- Create: `detectors/mobi_detector.py`
- Create: `tests/unit/test_mobi_detector.py`
- Modify: `tests/unit/conftest.py`

- [ ] **Step 1: Add MOBI fixture builder to `tests/unit/conftest.py`**

Append to the end of `conftest.py`:

```python
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
```

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/test_mobi_detector.py
from detectors.mobi_detector import MobiDetector


def test_detects_nav_points(mobi_with_nav_points):
    result = MobiDetector().detect(mobi_with_nav_points, {'mobi_use_toc': True})
    assert result.count == 7
    assert result.method == 'toc'
    assert result.confidence == 'high'


def test_detects_nav_li(mobi_with_nav_li):
    result = MobiDetector().detect(mobi_with_nav_li, {'mobi_use_toc': True})
    assert result.count == 4
    assert result.method == 'toc'


def test_returns_undetected_when_no_toc(mobi_no_toc):
    result = MobiDetector().detect(mobi_no_toc, {'mobi_use_toc': True})
    assert result.method == 'undetected'


def test_returns_undetected_when_toc_disabled(mobi_with_nav_points):
    result = MobiDetector().detect(mobi_with_nav_points, {'mobi_use_toc': False})
    assert result.method == 'undetected'


def test_returns_undetected_for_corrupted_file(corrupted_mobi):
    result = MobiDetector().detect(corrupted_mobi, {})
    assert result.method == 'undetected'


def test_force_method_toc_returns_undetected_when_no_toc(mobi_no_toc):
    result = MobiDetector().detect(mobi_no_toc, {'force_method': 'toc', 'mobi_use_toc': True})
    assert result.method == 'undetected'
```

- [ ] **Step 3: Run to confirm failure**

```bash
pytest tests/unit/test_mobi_detector.py -v
```

Expected: `ModuleNotFoundError: No module named 'detectors.mobi_detector'`

- [ ] **Step 4: Create `detectors/mobi_detector.py`**

```python
import re
from typing import Optional

from .base import BaseDetector, DetectionResult, UNDETECTED


class MobiDetector(BaseDetector):
    """
    Detects chapter count from MOBI/AZW3 files by byte-scanning for embedded
    NCX navPoint or EPUB3 nav content. Works for uncompressed or lightly
    structured MOBI files; returns UNDETECTED for heavily compressed content.
    """

    _NAV_POINT = re.compile(rb'<navPoint\b', re.IGNORECASE)
    _NAV_TOC   = re.compile(
        rb'epub:type=["\']toc["\'].*?<ol\b[^>]*>(.*?)</ol>',
        re.DOTALL | re.IGNORECASE,
    )
    _NAV_LI    = re.compile(rb'<li\b', re.IGNORECASE)

    def detect(self, book_path: str, per_book_config: dict) -> DetectionResult:
        try:
            return self._detect(book_path, per_book_config)
        except Exception:
            return UNDETECTED

    def _detect(self, book_path: str, cfg: dict) -> DetectionResult:
        force    = cfg.get('force_method')
        use_toc  = cfg.get('mobi_use_toc', True)

        if force not in (None, 'toc'):
            return UNDETECTED

        if not use_toc:
            return UNDETECTED

        with open(book_path, 'rb') as f:
            data = f.read()

        count = self._scan_for_toc(data)

        if count is not None and count > 0:
            return DetectionResult(count=count, method='toc', confidence='high')

        return UNDETECTED

    def _scan_for_toc(self, data: bytes) -> Optional[int]:
        points = self._NAV_POINT.findall(data)
        if points:
            return len(points)

        match = self._NAV_TOC.search(data)
        if match:
            items = self._NAV_LI.findall(match.group(1))
            if items:
                return len(items)

        return None
```

- [ ] **Step 5: Run to confirm pass**

```bash
pytest tests/unit/test_mobi_detector.py -v
```

Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add detectors/mobi_detector.py tests/unit/test_mobi_detector.py tests/unit/conftest.py
git commit -m "feat: add MOBI detector with byte-scan NCX detection"
```

---

## Task 6: PDF Adapter Shim + PDF Detector

**Files:**
- Create: `detectors/_calibre_pdf_adapter.py`
- Create: `detectors/pdf_detector.py`
- Create: `tests/unit/test_pdf_detector.py`
- Modify: `tests/unit/conftest.py`

- [ ] **Step 1: Add PDF fixture to `tests/unit/conftest.py`**

Append to `conftest.py`:

```python
def _make_minimal_pdf():
    """Minimal valid PDF with no bookmarks."""
    return (
        b'%PDF-1.4\n'
        b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
        b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
        b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n'
        b'xref\n0 4\n0000000000 65535 f \n'
        b'trailer<</Size 4/Root 1 0 R>>\n%%EOF\n'
    )


@pytest.fixture
def pdf_file(tmp_path):
    p = tmp_path / 'book.pdf'
    p.write_bytes(_make_minimal_pdf())
    return str(p)


@pytest.fixture
def corrupted_pdf(tmp_path):
    p = tmp_path / 'bad.pdf'
    p.write_bytes(b'\x00\x01\x02\x03')
    return str(p)
```

- [ ] **Step 2: Create `detectors/_calibre_pdf_adapter.py`**

```python
"""
Shim for Calibre's internal PDF API.

All Calibre-specific imports are isolated here. If a future Calibre version
changes the internal API, only this file needs updating. The PDF detector
depends only on the two public functions below.
"""


def get_pdf_bookmarks(pdf_path: str) -> list:
    """Return a flat list of top-level PDF bookmark titles, or [] if none."""
    try:
        from calibre.utils.podofo import get_podofo, podofo_err
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
```

- [ ] **Step 3: Write the failing test**

```python
# tests/unit/test_pdf_detector.py
from unittest.mock import patch
from detectors.pdf_detector import PdfDetector


_ADAPTER = 'detectors.pdf_detector._adapter'


def test_detects_bookmarks(pdf_file):
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=['Chapter 1', 'Chapter 2', 'Chapter 3']):
        result = PdfDetector().detect(pdf_file, {'pdf_use_bookmarks': True})
    assert result.count == 3
    assert result.method == 'toc'
    assert result.confidence == 'high'


def test_returns_undetected_when_no_bookmarks_and_no_heuristic(pdf_file):
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]):
        result = PdfDetector().detect(pdf_file, {'pdf_use_bookmarks': True, 'pdf_heuristic_enabled': False})
    assert result.method == 'undetected'


def test_heuristic_detects_chapter_headings(pdf_file):
    text = 'Chapter 1\nSome text\nChapter 2\nMore text\nChapter 3\n'
    patterns = [r'^Chapter\s+\d+']
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]), \
         patch(f'{_ADAPTER}.extract_pdf_text', return_value=text):
        result = PdfDetector().detect(pdf_file, {
            'pdf_use_bookmarks': True,
            'pdf_heuristic_enabled': True,
            'pdf_heuristic_patterns': patterns,
        })
    assert result.count == 3
    assert result.method == 'heuristic'
    assert result.confidence == 'low'


def test_heuristic_disabled_returns_undetected(pdf_file):
    text = 'Chapter 1\nChapter 2\n'
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]), \
         patch(f'{_ADAPTER}.extract_pdf_text', return_value=text):
        result = PdfDetector().detect(pdf_file, {
            'pdf_use_bookmarks': True,
            'pdf_heuristic_enabled': False,
        })
    assert result.method == 'undetected'


def test_returns_undetected_for_corrupted_file(corrupted_pdf):
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]):
        result = PdfDetector().detect(corrupted_pdf, {})
    assert result.method == 'undetected'


def test_force_method_toc_skips_heuristic(pdf_file):
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]):
        result = PdfDetector().detect(pdf_file, {
            'force_method': 'toc',
            'pdf_use_bookmarks': True,
            'pdf_heuristic_enabled': True,
        })
    assert result.method == 'undetected'  # forced toc, no bookmarks → undetected


def test_bookmarks_disabled_falls_through(pdf_file):
    text = 'Chapter 1\nChapter 2\n'
    patterns = [r'^Chapter\s+\d+']
    with patch(f'{_ADAPTER}.extract_pdf_text', return_value=text):
        result = PdfDetector().detect(pdf_file, {
            'pdf_use_bookmarks': False,
            'pdf_heuristic_enabled': True,
            'pdf_heuristic_patterns': patterns,
        })
    assert result.method == 'heuristic'
    assert result.count == 2
```

- [ ] **Step 4: Run to confirm failure**

```bash
pytest tests/unit/test_pdf_detector.py -v
```

Expected: `ModuleNotFoundError: No module named 'detectors.pdf_detector'`

- [ ] **Step 5: Create `detectors/pdf_detector.py`**

```python
import re
from typing import Optional

from .base import BaseDetector, DetectionResult, UNDETECTED
from . import _calibre_pdf_adapter as _adapter


class PdfDetector(BaseDetector):

    def detect(self, book_path: str, per_book_config: dict) -> DetectionResult:
        try:
            return self._detect(book_path, per_book_config)
        except Exception:
            return UNDETECTED

    def _detect(self, book_path: str, cfg: dict) -> DetectionResult:
        force              = cfg.get('force_method')
        use_bookmarks      = cfg.get('pdf_use_bookmarks', True)
        heuristic_enabled  = cfg.get('pdf_heuristic_enabled', False)
        patterns           = cfg.get('pdf_heuristic_patterns', [])

        if force not in (None, 'toc', 'heuristic'):
            return UNDETECTED

        if force != 'heuristic' and use_bookmarks:
            bookmarks = _adapter.get_pdf_bookmarks(book_path)
            if bookmarks:
                return DetectionResult(count=len(bookmarks), method='toc', confidence='high')
            if force == 'toc':
                return UNDETECTED

        if force != 'toc' and heuristic_enabled:
            count = self._heuristic_count(book_path, patterns)
            if count > 0:
                return DetectionResult(count=count, method='heuristic', confidence='low')

        return UNDETECTED

    def _heuristic_count(self, book_path: str, patterns: list) -> int:
        text = _adapter.extract_pdf_text(book_path)
        if not text:
            return 0
        compiled = [re.compile(p, re.MULTILINE) for p in patterns]
        matches = set()
        for line_num, line in enumerate(text.splitlines()):
            for pattern in compiled:
                if pattern.search(line):
                    matches.add(line_num)
                    break
        return len(matches)
```

- [ ] **Step 6: Run to confirm pass**

```bash
pytest tests/unit/test_pdf_detector.py -v
```

Expected: 7 passed

- [ ] **Step 7: Commit**

```bash
git add detectors/_calibre_pdf_adapter.py detectors/pdf_detector.py tests/unit/test_pdf_detector.py tests/unit/conftest.py
git commit -m "feat: add PDF detector with bookmark and heuristic text detection"
```

---

## Task 7: Detector Factory

**Files:**
- Create: `detectors/factory.py`
- Create: `tests/unit/test_factory.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_factory.py
import os
import pytest
from unittest.mock import patch, MagicMock
from detectors.factory import get_result_for_book
from detectors.base import DetectionResult


def _mock_db(book_id, fmt='epub', path='/books/book.epub', data_dir='/books/data'):
    db = MagicMock()
    db.formats.return_value = [fmt.upper()]
    db.format_abspath.return_value = path
    db.field_for.return_value = None           # no existing column value
    book_data = MagicMock()
    book_data.__str__ = lambda self: data_dir
    db.field_for.return_value = None
    db.new_api.format_abspath.return_value = path
    db.new_api.field_for.return_value = None
    return db


def test_manual_count_returns_immediately(tmp_path):
    p = tmp_path / 'book.epub'
    p.write_bytes(b'dummy')
    cfg = {'manual_count': 42}
    result = get_result_for_book(str(p), 'epub', cfg)
    assert result.count == 42
    assert result.method == 'manual'
    assert result.confidence == 'high'


def test_dispatches_epub(epub_with_ncx):
    result = get_result_for_book(epub_with_ncx, 'epub', {})
    assert result.method == 'toc'
    assert result.count == 5


def test_dispatches_mobi(mobi_with_nav_points):
    result = get_result_for_book(mobi_with_nav_points, 'mobi', {'mobi_use_toc': True})
    assert result.method == 'toc'
    assert result.count == 7


def test_unknown_format_returns_undetected(tmp_path):
    p = tmp_path / 'book.cbz'
    p.write_bytes(b'dummy')
    result = get_result_for_book(str(p), 'cbz', {})
    assert result.method == 'undetected'


def test_force_method_propagates_to_detector(epub_with_ncx):
    result = get_result_for_book(epub_with_ncx, 'epub', {'force_method': 'structural', 'epub_use_structural': True, 'epub_heading_tags': ['h1']})
    assert result.method in ('structural', 'undetected')  # no h1 in spine → undetected or structural
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_factory.py -v
```

Expected: `ModuleNotFoundError: No module named 'detectors.factory'`

- [ ] **Step 3: Create `detectors/factory.py`**

```python
from .base import DetectionResult, UNDETECTED
from .epub_detector import EpubDetector
from .mobi_detector import MobiDetector
from .pdf_detector import PdfDetector

_DETECTORS = {
    'epub': EpubDetector(),
    'mobi': MobiDetector(),
    'azw3': MobiDetector(),
    'azw':  MobiDetector(),
    'pdf':  PdfDetector(),
}


def get_result_for_book(book_path: str, fmt: str, merged_config: dict) -> DetectionResult:
    """
    Top-level dispatch. Returns a DetectionResult for a single book file.
    Caller is responsible for merging global prefs + per-book config before calling.
    """
    manual = merged_config.get('manual_count')
    if manual is not None:
        return DetectionResult(count=int(manual), method='manual', confidence='high')

    detector = _DETECTORS.get(fmt.lower())
    if detector is None:
        return UNDETECTED

    return detector.detect(book_path, merged_config)
```

- [ ] **Step 4: Run to confirm pass**

```bash
pytest tests/unit/test_factory.py -v
```

Expected: 5 passed

- [ ] **Step 5: Run full unit test suite to confirm no regressions**

```bash
pytest tests/unit/ -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add detectors/factory.py tests/unit/test_factory.py
git commit -m "feat: add detector factory with format dispatch and manual override"
```

---

## Task 8: Column Manager

**Files:**
- Create: `column_manager.py`

Note: `column_manager.py` depends on Calibre's DB API and is tested manually via a dev Calibre library. No unit tests in this task.

- [ ] **Step 1: Create `column_manager.py`**

```python
"""
Manages the two custom columns and applies the overwrite policy.

Column lookup names are read from config so users can rename them.
Calibre DB is passed in (not imported) to keep this module testable via DI.
"""
import re


_COLUMN_DEFS = {
    'count': {
        'label_key':   'count_column',
        'name':        'Chapter Count',
        'datatype':    'int',
        'is_multiple': None,
        'editable':    True,
        'display':     {},
    },
    'method': {
        'label_key':   'method_column',
        'name':        'Chapter Detection Method',
        'datatype':    'text',
        'is_multiple': None,
        'editable':    True,
        'display':     {},
    },
}


def ensure_columns(db, prefs: dict) -> None:
    """Create missing custom columns. Call on plugin init and before every write."""
    existing = {col['label'] for col in db.custom_column_list()}
    for key, defn in _COLUMN_DEFS.items():
        label = _bare_label(prefs[defn['label_key']])
        if label not in existing:
            db.create_custom_column(
                label=label,
                name=defn['name'],
                datatype=defn['datatype'],
                is_multiple=defn['is_multiple'],
                editable=defn['editable'],
                display=defn['display'],
            )


def should_write(db, book_id: int, new_result, prefs: dict) -> bool:
    """
    Return True if the new DetectionResult should be written,
    based on the configured overwrite policy.
    """
    policy = prefs.get('overwrite_policy', 'preserve_manual')

    method_label = _bare_label(prefs.get('method_column', '#chapter_detection_method'))
    current_method = db.get_custom(book_id, label=method_label, index_is_id=True)

    if current_method is None:
        return True  # empty → always write

    if policy == 'always':
        return True
    if policy == 'never':
        return False
    # 'preserve_manual': write unless current is manual
    return 'manual' not in str(current_method)


def write_result(db, book_id: int, result, prefs: dict) -> None:
    """Write DetectionResult to both custom columns."""
    ensure_columns(db, prefs)

    count_label  = _bare_label(prefs.get('count_column',  '#chapter_count'))
    method_label = _bare_label(prefs.get('method_column', '#chapter_detection_method'))

    db.set_custom(book_id, result.count,         label=count_label,  index_is_id=True)
    db.set_custom(book_id, result.column_value(), label=method_label, index_is_id=True)


def _bare_label(col_name: str) -> str:
    """Strip leading '#' from a column lookup name."""
    return col_name.lstrip('#')
```

- [ ] **Step 2: Commit**

```bash
git add column_manager.py
git commit -m "feat: add column manager with overwrite policy and column creation"
```

---

## Task 9: Batch Processor

**Files:**
- Create: `batch_processor.py`

- [ ] **Step 1: Create `batch_processor.py`**

```python
"""
Runs detection across a list of book IDs in a QThread.
Emits Qt signals so the UI can update without polling.
Caller provides a Calibre DB reference and merged config factory.
"""
try:
    from PyQt5.Qt import QThread, pyqtSignal
except ImportError:
    from PyQt6.Qt import QThread, pyqtSignal  # Calibre 7+

from detectors.factory import get_result_for_book
from column_manager import should_write, write_result
import time


class BatchProcessor(QThread):
    progress   = pyqtSignal(int, int, str)   # current, total, book_title
    book_done  = pyqtSignal(int, object)     # book_id, DetectionResult
    finished_  = pyqtSignal(dict)            # summary: {detected, skipped, failed}

    def __init__(self, db, book_ids: list, prefs: dict, per_book_loader, parent=None):
        super().__init__(parent)
        self._db              = db
        self._book_ids        = list(book_ids)
        self._prefs           = prefs
        self._per_book_loader = per_book_loader  # callable(book_data_dir) -> dict
        self._cancelled       = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        summary  = {'detected': 0, 'skipped': 0, 'failed': 0}
        total    = len(self._book_ids)
        batch_sz = self._prefs.get('batch_size', 50)

        for idx, book_id in enumerate(self._book_ids):
            if self._cancelled:
                break

            try:
                title = self._db.field_for('title', book_id) or f'Book {book_id}'
                self.progress.emit(idx + 1, total, title)

                result = self._detect_one(book_id)

                if should_write(self._db, book_id, result, self._prefs):
                    write_result(self._db, book_id, result, self._prefs)
                    if result.method != 'undetected':
                        summary['detected'] += 1
                    else:
                        summary['failed'] += 1
                else:
                    summary['skipped'] += 1

                self.book_done.emit(book_id, result)

            except Exception:
                summary['failed'] += 1

            # Yield between batches so Calibre UI stays responsive
            if (idx + 1) % batch_sz == 0:
                time.sleep(0.01)

        self.finished_.emit(summary)

    def _detect_one(self, book_id: int):
        from config import load_per_book_config, merge_config

        fmts = self._db.formats(book_id, index_is_id=True)
        if not fmts:
            from detectors.base import UNDETECTED
            return UNDETECTED

        preferred = preferred_format(fmts)
        book_path = self._db.format_abspath(book_id, preferred, index_is_id=True)
        data_dir  = self._db.field_for('path', book_id)

        per_book = self._per_book_loader(data_dir) if data_dir else {}
        merged   = merge_config(per_book, dict(self._prefs))

        return get_result_for_book(book_path, preferred.lower(), merged)


_FORMAT_PRIORITY = ['epub', 'azw3', 'mobi', 'azw', 'pdf']


def preferred_format(fmts: list) -> str:
    lower = [f.lower() for f in fmts]
    for fmt in _FORMAT_PRIORITY:
        if fmt in lower:
            return fmt
    return fmts[0].lower()
```

- [ ] **Step 2: Commit**

```bash
git add batch_processor.py
git commit -m "feat: add QThread batch processor with Qt signals and cancel support"
```

---

## Task 10: Preferences Widget

**Files:**
- Create: `ui/preferences_widget.py`

- [ ] **Step 1: Create `ui/preferences_widget.py`**

```python
try:
    from PyQt5.Qt import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
        QLabel, QLineEdit, QComboBox, QSpinBox, QPlainTextEdit,
        QPushButton, Qt,
    )
except ImportError:
    from PyQt6.Qt import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
        QLabel, QLineEdit, QComboBox, QSpinBox, QPlainTextEdit,
        QPushButton, Qt,
    )

from config import PREFS, DEFAULTS


class PreferencesWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    # ------------------------------------------------------------------ build

    def _build_ui(self):
        root = QVBoxLayout(self)

        root.addWidget(self._general_group())
        root.addWidget(self._columns_group())
        root.addWidget(self._epub_group())
        root.addWidget(self._mobi_group())
        root.addWidget(self._pdf_group())

        diag_btn = QPushButton('Run Diagnostic Tests')
        diag_btn.clicked.connect(self._run_diagnostics)
        root.addWidget(diag_btn)
        root.addStretch()

    def _general_group(self):
        g = QGroupBox('General')
        v = QVBoxLayout(g)

        self.auto_scan_cb   = QCheckBox('Auto-scan books when added to library')
        self.notify_err_cb  = QCheckBox('Show notification on auto-scan error')

        pol_row = QHBoxLayout()
        pol_row.addWidget(QLabel('Overwrite policy:'))
        self.overwrite_combo = QComboBox()
        self.overwrite_combo.addItems([
            'Preserve manual, overwrite auto-detected',
            'Always overwrite',
            'Never overwrite if set',
        ])
        pol_row.addWidget(self.overwrite_combo)
        pol_row.addStretch()

        batch_row = QHBoxLayout()
        batch_row.addWidget(QLabel('Batch size:'))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 5000)
        batch_row.addWidget(self.batch_spin)
        batch_row.addStretch()

        v.addWidget(self.auto_scan_cb)
        v.addWidget(self.notify_err_cb)
        v.addLayout(pol_row)
        v.addLayout(batch_row)
        return g

    def _columns_group(self):
        g = QGroupBox('Column Names')
        v = QVBoxLayout(g)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel('Chapter count column:'))
        self.count_col_edit = QLineEdit()
        row1.addWidget(self.count_col_edit)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel('Detection method column:'))
        self.method_col_edit = QLineEdit()
        row2.addWidget(self.method_col_edit)
        v.addLayout(row1)
        v.addLayout(row2)
        return g

    def _epub_group(self):
        g = QGroupBox('EPUB')
        v = QVBoxLayout(g)
        self.epub_toc_cb        = QCheckBox('Use TOC (toc.ncx / nav.xhtml)')
        self.epub_structural_cb = QCheckBox('Use structural heading scan')
        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel('Heading tags to scan:'))
        self.epub_tags_edit = QLineEdit()
        tag_row.addWidget(self.epub_tags_edit)
        v.addWidget(self.epub_toc_cb)
        v.addWidget(self.epub_structural_cb)
        v.addLayout(tag_row)
        return g

    def _mobi_group(self):
        g = QGroupBox('MOBI / AZW3')
        v = QVBoxLayout(g)
        self.mobi_toc_cb = QCheckBox('Use TOC record')
        v.addWidget(self.mobi_toc_cb)
        return g

    def _pdf_group(self):
        g = QGroupBox('PDF')
        v = QVBoxLayout(g)
        self.pdf_bookmarks_cb = QCheckBox('Use bookmark tree')
        self.pdf_heuristic_cb = QCheckBox('Enable heuristic text scan (slower)')
        v.addWidget(self.pdf_bookmarks_cb)
        v.addWidget(self.pdf_heuristic_cb)
        v.addWidget(QLabel('Heuristic patterns (regex, one per line):'))
        self.pdf_patterns_edit = QPlainTextEdit()
        self.pdf_patterns_edit.setMaximumHeight(80)
        v.addWidget(self.pdf_patterns_edit)
        return g

    # ------------------------------------------------------------------ I/O

    _POLICY_VALUES = ['preserve_manual', 'always', 'never']

    def _load(self):
        p = PREFS
        self.auto_scan_cb.setChecked(p.get('auto_scan_on_add', DEFAULTS['auto_scan_on_add']))
        self.notify_err_cb.setChecked(p.get('notify_on_error',   DEFAULTS['notify_on_error']))
        self.overwrite_combo.setCurrentIndex(
            self._POLICY_VALUES.index(p.get('overwrite_policy', DEFAULTS['overwrite_policy']))
        )
        self.batch_spin.setValue(p.get('batch_size', DEFAULTS['batch_size']))
        self.count_col_edit.setText(p.get('count_column',  DEFAULTS['count_column']))
        self.method_col_edit.setText(p.get('method_column', DEFAULTS['method_column']))
        self.epub_toc_cb.setChecked(p.get('epub_use_toc', DEFAULTS['epub_use_toc']))
        self.epub_structural_cb.setChecked(p.get('epub_use_structural', DEFAULTS['epub_use_structural']))
        self.epub_tags_edit.setText(', '.join(p.get('epub_heading_tags', DEFAULTS['epub_heading_tags'])))
        self.mobi_toc_cb.setChecked(p.get('mobi_use_toc', DEFAULTS['mobi_use_toc']))
        self.pdf_bookmarks_cb.setChecked(p.get('pdf_use_bookmarks',     DEFAULTS['pdf_use_bookmarks']))
        self.pdf_heuristic_cb.setChecked(p.get('pdf_heuristic_enabled', DEFAULTS['pdf_heuristic_enabled']))
        self.pdf_patterns_edit.setPlainText(
            '\n'.join(p.get('pdf_heuristic_patterns', DEFAULTS['pdf_heuristic_patterns']))
        )

    def save_settings(self):
        PREFS['auto_scan_on_add']      = self.auto_scan_cb.isChecked()
        PREFS['notify_on_error']       = self.notify_err_cb.isChecked()
        PREFS['overwrite_policy']      = self._POLICY_VALUES[self.overwrite_combo.currentIndex()]
        PREFS['batch_size']            = self.batch_spin.value()
        PREFS['count_column']          = self.count_col_edit.text().strip()
        PREFS['method_column']         = self.method_col_edit.text().strip()
        PREFS['epub_use_toc']          = self.epub_toc_cb.isChecked()
        PREFS['epub_use_structural']   = self.epub_structural_cb.isChecked()
        PREFS['epub_heading_tags']     = [t.strip() for t in self.epub_tags_edit.text().split(',') if t.strip()]
        PREFS['mobi_use_toc']          = self.mobi_toc_cb.isChecked()
        PREFS['pdf_use_bookmarks']     = self.pdf_bookmarks_cb.isChecked()
        PREFS['pdf_heuristic_enabled'] = self.pdf_heuristic_cb.isChecked()
        PREFS['pdf_heuristic_patterns'] = [
            ln.strip() for ln in self.pdf_patterns_edit.toPlainText().splitlines() if ln.strip()
        ]

    def _run_diagnostics(self):
        from calibre_plugins.chapter_count.ui.test_runner_dialog import TestRunnerDialog
        dlg = TestRunnerDialog(parent=self)
        dlg.exec_()
```

- [ ] **Step 2: Commit**

```bash
git add ui/preferences_widget.py
git commit -m "feat: add preferences widget with all config fields and diagnostic test button"
```

---

## Task 11: Per-Book Config Dialog

**Files:**
- Create: `ui/book_config_dialog.py`

- [ ] **Step 1: Create `ui/book_config_dialog.py`**

```python
try:
    from PyQt5.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
        QRadioButton, QComboBox, QSpinBox, QCheckBox, QPushButton,
        QDialogButtonBox, QButtonGroup, Qt,
    )
except ImportError:
    from PyQt6.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
        QRadioButton, QComboBox, QSpinBox, QCheckBox, QPushButton,
        QDialogButtonBox, QButtonGroup, Qt,
    )

from config import load_per_book_config, save_per_book_config

_FORCE_OPTIONS = ['', 'toc', 'structural', 'heuristic']
_FORCE_LABELS  = ['(auto)', 'TOC', 'Structural', 'Heuristic']


class BookConfigDialog(QDialog):

    def __init__(self, book_id: int, title: str, fmt: str,
                 book_data_dir: str, current_count, current_method,
                 parent=None):
        super().__init__(parent)
        self._book_data_dir = book_data_dir
        self._fmt           = (fmt or '').lower()
        self.setWindowTitle(f'Chapter Detection — {title}')
        self._cfg = load_per_book_config(book_data_dir)
        self._build_ui(title, current_count, current_method)
        self._load()

    # ------------------------------------------------------------------ build

    def _build_ui(self, title, current_count, current_method):
        root = QVBoxLayout(self)

        info = QGroupBox()
        info_v = QVBoxLayout(info)
        info_v.addWidget(QLabel(f'<b>{title}</b>'))
        count_str  = str(current_count) if current_count is not None else '—'
        method_str = current_method or 'not yet detected'
        info_v.addWidget(QLabel(f'Current count: {count_str}  [{method_str}]'))
        root.addWidget(info)

        override = QGroupBox('Override')
        ov = QVBoxLayout(override)

        self._btn_group = QButtonGroup(self)
        self.rb_default = QRadioButton('Use library defaults')
        self.rb_force   = QRadioButton('Force method:')
        self.rb_manual  = QRadioButton('Set manual count:')
        for btn in (self.rb_default, self.rb_force, self.rb_manual):
            self._btn_group.addButton(btn)

        force_row = QHBoxLayout()
        force_row.addWidget(self.rb_force)
        self.force_combo = QComboBox()
        self.force_combo.addItems(_FORCE_LABELS)
        force_row.addWidget(self.force_combo)
        force_row.addStretch()

        manual_row = QHBoxLayout()
        manual_row.addWidget(self.rb_manual)
        self.manual_spin = QSpinBox()
        self.manual_spin.setRange(0, 9999)
        manual_row.addWidget(self.manual_spin)
        manual_row.addStretch()

        ov.addWidget(self.rb_default)
        ov.addLayout(force_row)
        ov.addLayout(manual_row)
        root.addWidget(override)

        if self._fmt == 'epub':
            root.addWidget(self._epub_options())
        elif self._fmt == 'pdf':
            root.addWidget(self._pdf_options())

        btn_row = QHBoxLayout()
        clear_btn = QPushButton('Clear override')
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        root.addLayout(btn_row)

    def _epub_options(self):
        g = QGroupBox('EPUB options (this book only)')
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        row.addWidget(QLabel('Heading tags:'))
        self.epub_tags_edit = QLineEdit()  # QLineEdit imported at top of file
        row.addWidget(self.epub_tags_edit)
        v.addLayout(row)
        return g

    def _pdf_options(self):
        g = QGroupBox('PDF options (this book only)')
        v = QVBoxLayout(g)
        self.pdf_heuristic_cb = QCheckBox('Enable heuristic text scan')
        v.addWidget(self.pdf_heuristic_cb)
        return g

    # ------------------------------------------------------------------ I/O

    def _load(self):
        manual = self._cfg.get('manual_count')
        force  = self._cfg.get('force_method')

        if manual is not None:
            self.rb_manual.setChecked(True)
            self.manual_spin.setValue(int(manual))
        elif force:
            self.rb_force.setChecked(True)
            idx = _FORCE_OPTIONS.index(force) if force in _FORCE_OPTIONS else 0
            self.force_combo.setCurrentIndex(idx)
        else:
            self.rb_default.setChecked(True)

        if self._fmt == 'epub' and hasattr(self, 'epub_tags_edit'):
            tags = self._cfg.get('heading_tags') or []
            self.epub_tags_edit.setText(', '.join(tags))
        if self._fmt == 'pdf' and hasattr(self, 'pdf_heuristic_cb'):
            self.pdf_heuristic_cb.setChecked(bool(self._cfg.get('heuristic_enabled')))

    def _clear(self):
        self._cfg = {}
        save_per_book_config(self._book_data_dir, self._cfg)
        self.accept()

    def _save_and_accept(self):
        cfg = {'manual_count': None, 'force_method': None, 'heading_tags': None, 'heuristic_enabled': None}

        if self.rb_manual.isChecked():
            cfg['manual_count'] = self.manual_spin.value()
        elif self.rb_force.isChecked():
            idx = self.force_combo.currentIndex()
            cfg['force_method'] = _FORCE_OPTIONS[idx] or None

        if self._fmt == 'epub' and hasattr(self, 'epub_tags_edit'):
            text = self.epub_tags_edit.text().strip()
            cfg['heading_tags'] = [t.strip() for t in text.split(',') if t.strip()] or None
        if self._fmt == 'pdf' and hasattr(self, 'pdf_heuristic_cb'):
            cfg['heuristic_enabled'] = self.pdf_heuristic_cb.isChecked() or None

        save_per_book_config(self._book_data_dir, cfg)
        self.accept()
```

- [ ] **Step 2: Commit**

```bash
git add ui/book_config_dialog.py
git commit -m "feat: add per-book config dialog with format-aware options"
```

---

## Task 12: Batch Progress Dialog + Book Selector

**Files:**
- Create: `ui/batch_progress_dialog.py`

- [ ] **Step 1: Create `ui/batch_progress_dialog.py`**

```python
try:
    from PyQt5.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
        QProgressBar, QPushButton, QRadioButton, QButtonGroup,
        QDialogButtonBox, Qt,
    )
except ImportError:
    from PyQt6.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
        QProgressBar, QPushButton, QRadioButton, QButtonGroup,
        QDialogButtonBox, Qt,
    )

from batch_processor import BatchProcessor
from config import load_per_book_config


# ─────────────────────────────────────────── Book Selector Dialog

class BookSelectorDialog(QDialog):
    """Lets the user choose which books to scan before launching the batch."""

    SCOPE_ALL        = 'all'
    SCOPE_SELECTED   = 'selected'
    SCOPE_MISSING    = 'missing'
    SCOPE_UNDETECTED = 'undetected'

    def __init__(self, selected_ids: list, parent=None):
        super().__init__(parent)
        self._selected_ids = selected_ids
        self.chosen_scope  = self.SCOPE_ALL
        self.setWindowTitle('Select Books to Scan')
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        g = QGroupBox('Scan which books?')
        v = QVBoxLayout(g)
        self._bg = QButtonGroup(self)
        options = [
            (self.SCOPE_ALL,        'All books in library'),
            (self.SCOPE_SELECTED,   f'Selected books ({len(self._selected_ids)})'),
            (self.SCOPE_MISSING,    'Books with missing chapter count'),
            (self.SCOPE_UNDETECTED, 'Books with undetected method'),
        ]
        self._radios = {}
        for scope, label in options:
            rb = QRadioButton(label)
            if scope == self.SCOPE_ALL:
                rb.setChecked(True)
            self._bg.addButton(rb)
            self._radios[scope] = rb
            v.addWidget(rb)
        root.addWidget(g)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self):
        for scope, rb in self._radios.items():
            if rb.isChecked():
                self.chosen_scope = scope
                break
        self.accept()


# ─────────────────────────────────────────── Progress Dialog

class BatchProgressDialog(QDialog):

    def __init__(self, db, book_ids: list, prefs: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Counting Chapters…')
        self.setMinimumWidth(480)
        self._build_ui(len(book_ids))

        self._processor = BatchProcessor(
            db=db,
            book_ids=book_ids,
            prefs=prefs,
            per_book_loader=lambda d: load_per_book_config(d) if d else {},
            parent=self,
        )
        self._processor.progress.connect(self._on_progress)
        self._processor.book_done.connect(self._on_book_done)
        self._processor.finished_.connect(self._on_finished)
        self._processor.start()

    def _build_ui(self, total: int):
        root = QVBoxLayout(self)
        self._current_lbl  = QLabel('Starting…')
        self._bar          = QProgressBar()
        self._bar.setRange(0, total)
        self._tally_lbl    = QLabel('Detected: 0  Skipped: 0  Failed: 0')
        self._cancel_btn   = QPushButton('Cancel')
        self._cancel_btn.clicked.connect(self._cancel)
        root.addWidget(self._current_lbl)
        root.addWidget(self._bar)
        root.addWidget(self._tally_lbl)
        root.addWidget(self._cancel_btn, alignment=Qt.AlignRight)
        self._tally = {'detected': 0, 'skipped': 0, 'failed': 0}

    def _on_progress(self, current: int, total: int, title: str):
        self._bar.setValue(current)
        self._current_lbl.setText(f'{current}/{total} — {title}')

    def _on_book_done(self, book_id: int, result):
        if result.method not in ('undetected',):
            self._tally['detected'] += 1
        else:
            self._tally['failed'] += 1
        self._refresh_tally()

    def _refresh_tally(self):
        t = self._tally
        self._tally_lbl.setText(
            f"Detected: {t['detected']}  Skipped: {t['skipped']}  Failed: {t['failed']}"
        )

    def _on_finished(self, summary: dict):
        self._tally = summary
        self._refresh_tally()
        self._cancel_btn.setText('Close')
        self._cancel_btn.clicked.disconnect()
        self._cancel_btn.clicked.connect(self.accept)
        self._current_lbl.setText('Done.')

    def _cancel(self):
        self._processor.cancel()
        self._cancel_btn.setEnabled(False)
        self._current_lbl.setText('Cancelling…')
```

- [ ] **Step 2: Commit**

```bash
git add ui/batch_progress_dialog.py
git commit -m "feat: add batch progress dialog and book selector"
```

---

## Task 13: Integration Test Runner Dialog

**Files:**
- Create: `ui/test_runner_dialog.py`
- Create: `tests/integration/__init__.py` (already exists)

- [ ] **Step 1: Create `ui/test_runner_dialog.py`**

```python
try:
    from PyQt5.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
        QPushButton, QLabel, QApplication, Qt,
    )
except ImportError:
    from PyQt6.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
        QPushButton, QLabel, QApplication, Qt,
    )

try:
    from PyQt5.Qt import QThread, pyqtSignal
except ImportError:
    from PyQt6.Qt import QThread, pyqtSignal


class _TestRunner(QThread):
    result = pyqtSignal(str, bool, str)   # name, passed, detail
    done   = pyqtSignal()

    def run(self):
        from calibre_plugins.chapter_count.tests.integration import test_integration
        for name, passed, detail in test_integration.run_all():
            self.result.emit(name, passed, detail)
        self.done.emit()


class TestRunnerDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Chapter Count — Diagnostic Tests')
        self.setMinimumSize(600, 400)
        self._build_ui()
        self._run()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self._status = QLabel('Running tests…')
        root.addWidget(self._status)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(['Test', 'Result', 'Detail'])
        self._tree.setColumnWidth(0, 300)
        root.addWidget(self._tree)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton('Copy results to clipboard')
        copy_btn.clicked.connect(self._copy)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _run(self):
        self._runner = _TestRunner(parent=self)
        self._runner.result.connect(self._add_result)
        self._runner.done.connect(self._on_done)
        self._runner.start()

    def _add_result(self, name: str, passed: bool, detail: str):
        item = QTreeWidgetItem([name, 'PASS' if passed else 'FAIL', detail])
        color = Qt.green if passed else Qt.red
        item.setForeground(1, color)
        self._tree.addTopLevelItem(item)

    def _on_done(self):
        total  = self._tree.topLevelItemCount()
        passed = sum(
            1 for i in range(total)
            if self._tree.topLevelItem(i).text(1) == 'PASS'
        )
        self._status.setText(f'Completed: {passed}/{total} passed')

    def _copy(self):
        lines = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            lines.append(f"{item.text(1):4}  {item.text(0)}  {item.text(2)}")
        QApplication.clipboard().setText('\n'.join(lines))
```

- [ ] **Step 2: Commit**

```bash
git add ui/test_runner_dialog.py
git commit -m "feat: add integration test runner dialog with streaming results"
```

---

## Task 14: Integration Tests

**Files:**
- Create: `tests/integration/test_integration.py`
- Create: `tests/integration/fixtures/` (minimal EPUB, MOBI, PDF fixture files)

- [ ] **Step 1: Generate integration fixture files**

Create `tests/integration/make_fixtures.py` (run once, output committed):

```python
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
```

- [ ] **Step 2: Run the fixture generator**

```bash
python tests/integration/make_fixtures.py
```

Expected output: `Fixtures written to .../tests/integration/fixtures`

- [ ] **Step 3: Create `tests/integration/test_integration.py`**

```python
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
```

- [ ] **Step 4: Commit**

```bash
git add tests/integration/ 
git commit -m "feat: add integration tests with bundled fixtures and run_all() generator"
```

---

## Task 15: Plugin Action Wiring

**Files:**
- Modify: `action.py` (replace stub)

- [ ] **Step 1: Replace `action.py` with full implementation**

```python
from functools import partial

try:
    from PyQt5.Qt import QApplication
except ImportError:
    from PyQt6.Qt import QApplication

from calibre.gui2.actions import InterfaceAction
from calibre.gui2 import error_dialog, info_dialog

from config import PREFS, DEFAULTS, load_per_book_config, merge_config
from column_manager import ensure_columns, should_write, write_result
from detectors.factory import get_result_for_book


class ChapterCountAction(InterfaceAction):
    name        = 'Chapter Count'
    action_spec = ('Chapter Count', None, 'Count chapters in selected books', None)

    # ─────────────────────────────── Calibre lifecycle

    def genesis(self):
        self.qaction.triggered.connect(self.bulk_scan_triggered)
        self.create_menu_action(
            self.qaction.menu() or self._make_menu(),
            'count_selected',
            'Count Chapters',
            triggered=self.count_selected,
        )
        self.create_menu_action(
            self.qaction.menu() or self._make_menu(),
            'configure_selected',
            'Configure Chapter Detection',
            triggered=self.configure_selected,
        )

    def _make_menu(self):
        from calibre.gui2.actions import create_menu_action
        import calibre.gui2 as gui2
        try:
            from PyQt5.Qt import QMenu
        except ImportError:
            from PyQt6.Qt import QMenu
        m = QMenu()
        self.qaction.setMenu(m)
        return m

    def initialization_complete(self):
        self._first_run_check()
        if PREFS.get('auto_scan_on_add', DEFAULTS['auto_scan_on_add']):
            try:
                self.gui.current_db.new_api.add_listener(self._on_books_added)
            except AttributeError:
                pass  # API not available in this Calibre version

    # ─────────────────────────────── First-run

    def _first_run_check(self):
        if PREFS.get('_installed'):
            return
        PREFS['_installed'] = True
        db    = self.gui.current_db
        count = db.count()
        ensure_columns(db, dict(PREFS))
        if count == 0:
            return
        from calibre.gui2 import question_dialog
        if question_dialog(
            self.gui,
            'Chapter Count',
            f'{count} book(s) found in your library. Run a bulk scan now?',
            default_yes=False,
        ):
            self.bulk_scan_triggered()

    # ─────────────────────────────── Auto-scan hook

    def _on_books_added(self, event, library_id, book_ids, **kwargs):
        if event != 'books-added':
            return
        db    = self.gui.current_db
        prefs = dict(PREFS)
        ensure_columns(db, prefs)
        for book_id in book_ids:
            try:
                self._scan_one_silent(db, book_id, prefs)
            except Exception as exc:
                import traceback
                from calibre.utils.logging import default_log
                default_log.error(f'Chapter Count auto-scan failed for book {book_id}: {exc}')
                if prefs.get('notify_on_error', DEFAULTS['notify_on_error']):
                    error_dialog(self.gui, 'Chapter Count', str(exc), show=True)

    def _scan_one_silent(self, db, book_id: int, prefs: dict):
        fmts = db.formats(book_id, index_is_id=True)
        if not fmts:
            return
        from batch_processor import preferred_format
        preferred = preferred_format(list(fmts))
        book_path = db.format_abspath(book_id, preferred, index_is_id=True)
        data_dir  = db.field_for('path', book_id)
        per_book  = load_per_book_config(data_dir) if data_dir else {}
        merged    = merge_config(per_book, prefs)
        result    = get_result_for_book(book_path, preferred.lower(), merged)
        if should_write(db, book_id, result, prefs):
            write_result(db, book_id, result, prefs)

    # ─────────────────────────────── Manual actions

    def count_selected(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return
        book_ids = [self.gui.library_view.model().id(r) for r in rows]
        self._launch_batch(book_ids)

    def configure_selected(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return
        book_id = self.gui.library_view.model().id(rows[0])
        db      = self.gui.current_db
        title   = db.field_for('title', book_id) or ''
        fmts    = db.formats(book_id, index_is_id=True) or []
        from batch_processor import preferred_format
        fmt      = preferred_format(list(fmts)) if fmts else ''
        data_dir = db.field_for('path', book_id) or ''
        prefs    = dict(PREFS)
        count_label  = prefs.get('count_column',  '#chapter_count').lstrip('#')
        method_label = prefs.get('method_column', '#chapter_detection_method').lstrip('#')
        current_count  = db.get_custom(book_id, label=count_label,  index_is_id=True)
        current_method = db.get_custom(book_id, label=method_label, index_is_id=True)

        from ui.book_config_dialog import BookConfigDialog
        dlg = BookConfigDialog(
            book_id=book_id, title=title, fmt=fmt,
            book_data_dir=data_dir,
            current_count=current_count, current_method=current_method,
            parent=self.gui,
        )
        dlg.exec_()

    def bulk_scan_triggered(self):
        from ui.batch_progress_dialog import BookSelectorDialog, BatchProgressDialog
        db       = self.gui.current_db
        selected = [
            self.gui.library_view.model().id(r)
            for r in self.gui.library_view.selectionModel().selectedRows()
        ]
        selector = BookSelectorDialog(selected_ids=selected, parent=self.gui)
        if selector.exec_() != BookSelectorDialog.Accepted:
            return

        book_ids = self._resolve_scope(selector.chosen_scope, selected, db)
        if not book_ids:
            info_dialog(self.gui, 'Chapter Count', 'No books matched the selected scope.', show=True)
            return

        ensure_columns(db, dict(PREFS))
        dlg = BatchProgressDialog(db=db, book_ids=book_ids, prefs=dict(PREFS), parent=self.gui)
        dlg.exec_()
        self.gui.library_view.model().refresh()

    def _resolve_scope(self, scope: str, selected_ids: list, db) -> list:
        from ui.batch_progress_dialog import BookSelectorDialog as BS
        prefs        = dict(PREFS)
        method_label = prefs.get('method_column', '#chapter_detection_method').lstrip('#')
        count_label  = prefs.get('count_column',  '#chapter_count').lstrip('#')

        if scope == BS.SCOPE_ALL:
            return db.all_ids()
        if scope == BS.SCOPE_SELECTED:
            return selected_ids
        if scope == BS.SCOPE_MISSING:
            return [bid for bid in db.all_ids()
                    if db.get_custom(bid, label=count_label, index_is_id=True) is None]
        if scope == BS.SCOPE_UNDETECTED:
            return [bid for bid in db.all_ids()
                    if 'undetected' in str(db.get_custom(bid, label=method_label, index_is_id=True) or '')]
        return []
```

- [ ] **Step 2: Commit**

```bash
git add action.py
git commit -m "feat: wire up full plugin action with auto-scan, context menu, and bulk scan"
```

---

## Task 16: Build Script

**Files:**
- Create: `build.py`

- [ ] **Step 1: Create `build.py`**

```python
#!/usr/bin/env python3
"""
Package the plugin as a Calibre-installable ZIP.

Usage:
    python build.py

Output: dist/chapter_count.zip
"""
import zipfile
import os
import sys

PLUGIN_DIR = os.path.dirname(__file__)
DIST_DIR   = os.path.join(PLUGIN_DIR, 'dist')
OUTPUT     = os.path.join(DIST_DIR, 'chapter_count.zip')

# Files/dirs to include (relative to PLUGIN_DIR)
INCLUDE = [
    '__init__.py',
    'action.py',
    'config.py',
    'column_manager.py',
    'batch_processor.py',
    'detectors/__init__.py',
    'detectors/base.py',
    'detectors/epub_detector.py',
    'detectors/mobi_detector.py',
    'detectors/pdf_detector.py',
    'detectors/_calibre_pdf_adapter.py',
    'detectors/factory.py',
    'ui/__init__.py',
    'ui/preferences_widget.py',
    'ui/book_config_dialog.py',
    'ui/batch_progress_dialog.py',
    'ui/test_runner_dialog.py',
    'tests/__init__.py',
    'tests/integration/__init__.py',
    'tests/integration/test_integration.py',
    'tests/integration/fixtures/fixture.epub',
    'tests/integration/fixtures/fixture.mobi',
    'tests/integration/fixtures/fixture.pdf',
]

def build():
    os.makedirs(DIST_DIR, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel_path in INCLUDE:
            full_path = os.path.join(PLUGIN_DIR, rel_path)
            if not os.path.exists(full_path):
                print(f'WARNING: missing {rel_path}')
                continue
            zf.write(full_path, rel_path)
    print(f'Built: {OUTPUT}')

if __name__ == '__main__':
    build()
```

- [ ] **Step 2: Run the build script to confirm it works**

```bash
python build.py
```

Expected: `Built: .../dist/chapter_count.zip`

- [ ] **Step 3: Verify the ZIP contents**

```bash
python -c "import zipfile; zf = zipfile.ZipFile('dist/chapter_count.zip'); print('\n'.join(sorted(zf.namelist())))"
```

Expected: all 28 files listed, no `tests/unit/` entries.

- [ ] **Step 4: Create `dist/.gitignore`** so the built ZIP is not committed

```
*
!.gitignore
```

- [ ] **Step 5: Commit**

```bash
git add build.py dist/.gitignore
git commit -m "feat: add build script that packages plugin as distributable ZIP"
```

---

## Post-Build: Install in Calibre for Manual Verification

After running `python build.py`:

1. Open Calibre → Preferences → Plugins → Load plugin from file
2. Select `dist/chapter_count.zip`
3. Restart Calibre
4. Verify toolbar button appears
5. Right-click a book → confirm "Count Chapters" and "Configure Chapter Detection" appear
6. Open Preferences → Plugins → Chapter Count → click "Run Diagnostic Tests"
7. Confirm all integration tests pass (or skip with explanation for PDF adapter)
8. Add a new EPUB to the library — confirm auto-scan triggers (if enabled)
9. Run a bulk scan on a small set of books and verify columns are populated

---

## Running Unit Tests

```bash
pip install pytest
pytest tests/unit/ -v
```

All 25+ unit tests should pass without Calibre installed.
