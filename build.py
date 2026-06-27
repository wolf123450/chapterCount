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
    'plugin-import-name-chapter_count.txt',
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
