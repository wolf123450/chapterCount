# Calibre Chapter Count Plugin — Design Spec

**Date:** 2026-06-26  
**Status:** Approved  
**Project:** chapterCount

---

## Overview

A Calibre plugin that detects and stores chapter counts for books in the user's library. Detection is tiered (TOC → structural → heuristic → manual), per-book configurable, and operates across EPUB, MOBI/AZW3, and PDF formats. Results are stored in two custom Calibre columns. The plugin is designed to be shared publicly.

---

## Module Structure

```
chapterCount/
├── __init__.py                    # InterfaceAction plugin entry point
├── config.py                      # Preferences model + persistence (JSONConfig)
├── column_manager.py              # Custom column creation & update logic
├── batch_processor.py             # Batched scanning with Qt signal-based progress
├── detectors/
│   ├── base.py                    # BaseDetector ABC + DetectionResult dataclass
│   ├── epub_detector.py           # EPUB: toc.ncx / nav.xhtml → h1/h2 spine scan
│   ├── mobi_detector.py           # MOBI/AZW3: TOC record parsing via struct
│   ├── pdf_detector.py            # PDF: bookmarks → optional heuristic text scan
│   ├── _calibre_pdf_adapter.py    # Shim isolating Calibre internal PDF API calls
│   └── factory.py                 # Maps file extension → detector instance
├── ui/
│   ├── preferences_widget.py      # Calibre prefs panel (ConfigWidget subclass)
│   ├── book_config_dialog.py      # Per-book override dialog (QDialog)
│   ├── batch_progress_dialog.py   # Progress UI for bulk scans (QDialog + QThread)
│   └── test_runner_dialog.py      # Integration test runner dialog (QDialog + QThread)
└── tests/
    ├── unit/                      # Pure-Python pytest tests (run outside Calibre)
    │   ├── fixtures/              # Minimal EPUB, MOBI, PDF fixture files
    │   └── test_*.py
    └── integration/               # Bundled in plugin ZIP, run inside Calibre
        └── test_*.py
```

**Key design principles:**
- Detectors are pure functions (path in → `DetectionResult` out) with no Calibre dependencies — unit-testable outside Calibre with pytest
- UI and detection logic are fully decoupled — `batch_processor.py` calls detectors and emits Qt signals; UI consumes signals
- Config is always merged (per-book config on top of global prefs) at detection time — `null` per-book values mean "use global default"
- The `_calibre_pdf_adapter.py` shim is the single point of contact with Calibre's internal PDF API — if a Calibre version breaks it, only this file needs updating

---

## Detection Pipeline

### Core types

```python
@dataclass
class DetectionResult:
    count: int
    method: str      # "toc" | "structural" | "heuristic" | "manual" | "undetected"
    confidence: str  # "high" | "medium" | "low"

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, book_path: str, per_book_config: dict) -> DetectionResult:
        ...
```

### Manual override (checked first by factory)

If a book has a manual count in its per-book config, `factory.py` returns immediately with `DetectionResult(count=n, method="manual", confidence="high")` before dispatching to any detector.

If `force_method` is set (e.g., "toc"), the detector runs only that method's step and does **not** fall through to subsequent tiers on failure — it returns `undetected` directly. This is intentional: "force" means "use only this method."

### EPUB detector (tiered)

1. Parse `toc.ncx` (`navPoint` entries) or `nav.xhtml` (`<nav epub:type="toc">` `<li>` entries) for top-level items → `method="toc"`, `confidence="high"`
2. If TOC missing or empty: open each spine item and count configured heading tags (default: `h1`, `h2`) → `method="structural"`, `confidence="medium"`
3. Falls through to `DetectionResult(count=0, method="undetected", confidence="low")`

### MOBI/AZW3 detector (tiered)

1. Parse the MOBI header's TOC record using `struct` → `method="toc"`, `confidence="high"`
2. Falls through to `undetected` (structural scanning MOBI requires full decompression; not attempted)

### PDF detector (tiered)

1. Extract bookmark tree via `_calibre_pdf_adapter.py` (wraps `calibre.utils.podofo`) → `method="toc"`, `confidence="high"`
2. If heuristic opt-in enabled in prefs: invoke Calibre's internal text extraction, then scan extracted text against configurable regex patterns (e.g., `^Chapter\s+(\d+|[A-Z][a-z]+)`, `^CHAPTER\s+`) → `method="heuristic"`, `confidence="low"`
3. Falls through to `undetected`

### Error handling in detectors

All detectors catch all exceptions internally. Any failure returns `DetectionResult(count=0, method="undetected", confidence="low")`. The error is written to Calibre's debug log with book ID and path. A bad book never crashes a batch run.

---

## Custom Columns

Two columns are created on first run:

| Column | Lookup name | Type | Example value |
|---|---|---|---|
| Chapter Count | `#chapter_count` | Integer | `24` |
| Detection Method | `#chapter_detection_method` | Text | `toc · high` |

The detection method column stores `{method} · {confidence}` as a plain string. This is human-readable and filterable in Calibre's search bar (e.g., `#chapter_detection_method:"=undetected"` to audit books needing review).

Column lookup names are configurable in preferences. If a column is accidentally deleted, `column_manager.py` recreates it on the next plugin action with a non-blocking warning dialog.

---

## Per-Book Configuration

Stored as `chaptercount_config.json` in the book's Calibre data directory alongside other book metadata. This keeps plugin data out of the Calibre database and portable if the library is moved.

```json
{
  "manual_count": null,
  "force_method": null,
  "heading_tags": null,
  "heuristic_enabled": null
}
```

`null` means "inherit from global preference." Only non-null values override the global config. The config is merged at detection time in `factory.py`.

---

## Overwrite Policy

Evaluated by `column_manager.py` after a `DetectionResult` is returned. Detectors always return a result; the column manager decides whether to write it.

| Current column state | Default policy behavior |
|---|---|
| Empty | Always write |
| `method="manual"` | Never overwrite |
| `method=toc/structural/heuristic` | Overwrite |

Configurable overwrite policies (selected in preferences):
- **Preserve manual, overwrite auto-detected** (default)
- **Always overwrite**
- **Never overwrite if set**

---

## Triggers

| Trigger | Mechanism | Configurable |
|---|---|---|
| Auto on book add | `book_added` Calibre hook | On/off in prefs |
| Manual (selected books) | Right-click → "Count Chapters" | Always available |
| Per-book configuration | Right-click → "Configure Chapter Detection" | Always available |
| Bulk scan | Toolbar button → batch progress dialog | Always available |

**First-install behavior:** The plugin creates its custom columns, then shows a one-time dialog:
> *"X books found in library. Run a bulk scan now, or do it later from the toolbar?"*

No automatic scan is triggered on install.

**Auto-scan on add:** Uses the same detection pipeline but writes silently without a progress dialog. Errors are logged to Calibre's debug log. A preference controls whether errors additionally show a notification popup.

---

## Batch Processor

- Runs in a `QThread` to keep Calibre's UI responsive
- Qt signals: `progress(current, total, book_title)`, `book_done(book_id, result)`, `finished(summary)`
- Configurable batch size (default: 50 books); yields between batches to keep Calibre interactive
- Progress dialog shows: current book title, progress bar, running tally of detected/skipped/failed, and a Cancel button
- On cancel: thread finishes its current book cleanly and stops — no partial writes

---

## UI

### Preferences panel (Calibre Preferences → Plugins → Chapter Count)

```
General
  ☑ Auto-scan books when added to library
  ☑ Show notification on auto-scan error (vs. silent log only)
  Overwrite policy:  [Preserve manual, overwrite auto-detected ▼]
  Batch size:        [50]

Column Names
  Chapter count column:      [#chapter_count            ]
  Detection method column:   [#chapter_detection_method ]

EPUB
  ☑ Use TOC (toc.ncx / nav.xhtml)
  ☑ Use structural heading scan
  Heading tags to scan:  [h1, h2]

MOBI / AZW3
  ☑ Use TOC record

PDF
  ☑ Use bookmark tree
  ☐ Enable heuristic text scan (slower)
  Heuristic patterns (regex, one per line):
    ^Chapter\s+(\d+|[A-Z][a-z]+)
    ^CHAPTER\s+
    ^Part\s+

────────────────────────────────────────
[ Run Diagnostic Tests ]
```

### Per-book dialog (right-click → "Configure Chapter Detection")

```
Book: "The Name of the Wind"
Current count: 92    [detected via toc · high]

Override
  ○ Use library defaults
  ○ Force method:     [TOC ▼]
  ○ Set manual count: [   ]

EPUB options (this book only)       ← shown only for EPUB books
  Heading tags:  [h1, h2]

PDF options (this book only)        ← shown only for PDF books
  ☐ Enable heuristic text scan

[ Clear override ]              [ Cancel ]  [ Save ]
```

The format-specific options section is shown or hidden based on the book's primary file format. MOBI/AZW3 books have no per-book format options (no configurable parameters beyond the override above).

### Bulk scan dialog (toolbar button)

Book selector before starting:
- All books in library
- Selected books
- Books with missing chapter count
- Books with `method="undetected"`

Then launches the batch progress dialog.

---

## Testing

### Unit tests (outside Calibre)

- Live in `tests/unit/`, run with `pytest`
- All detectors are pure functions with no Calibre imports — fully testable in isolation
- Fixture corpus: valid EPUB with TOC, EPUB with no TOC (headings only), EPUB with neither, valid MOBI, PDF with bookmarks, PDF without bookmarks, corrupted file of each type
- `column_manager.py` and `batch_processor.py` have Calibre DB dependencies — tested manually via a dev Calibre library

### Integration tests (inside Calibre)

- Live in `tests/integration/`, bundled in the plugin ZIP
- Launched via "Run Diagnostic Tests" button in the preferences panel
- Run in a `QThread`; results stream into a `TestRunnerDialog` tree view (pass/fail/skip + expandable detail)
- Coverage:
  - Custom columns exist with correct types in the live Calibre DB
  - Each detector against bundled fixture files (minimal EPUB, MOBI, PDF shipped in the plugin ZIP)
  - Config read/write roundtrip
  - Batch processor against 3–5 fixture books in a temp library
  - `_calibre_pdf_adapter.py` import (pass = loads; skip = Calibre version incompatible)
- "Copy results to clipboard" button for easy bug reporting

---

## Distribution

- Plugin distributed as a ZIP file following Calibre's standard plugin structure
- No external dependencies bundled — uses only Python stdlib and Calibre's own libraries
- `tests/unit/` is excluded from the plugin ZIP (not needed at runtime)
- `tests/integration/` is included in the plugin ZIP (needed for the in-Calibre test runner)
