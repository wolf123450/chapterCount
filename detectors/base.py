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
