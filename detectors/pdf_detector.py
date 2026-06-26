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
