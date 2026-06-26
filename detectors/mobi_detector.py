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
