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
