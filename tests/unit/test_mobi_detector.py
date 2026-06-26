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
