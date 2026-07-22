from pathlib import Path


def test_repository_workspace_has_no_low_confidence_filter_chip():
    template_path = Path(__file__).resolve().parents[1] / "templates" / "session.html"
    content = template_path.read_text(encoding="utf-8")

    assert 'data-status="LowConfidence"' not in content
    assert 'Low confidence' not in content
