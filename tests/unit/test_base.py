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
