from pathlib import Path


def test_archived_sessions_section_is_not_rendered():
    dashboard_template = Path(__file__).resolve().parents[1] / "templates" / "dashboard.html"
    dashboard_content = dashboard_template.read_text(encoding="utf-8")

    assert "Archived Sessions" not in dashboard_content
    assert "archivedSessions" not in dashboard_content


def test_archived_link_is_not_in_main_navigation():
    base_template = Path(__file__).resolve().parents[1] / "templates" / "base.html"
    base_content = base_template.read_text(encoding="utf-8")

    assert "#archivedSessions" not in base_content
