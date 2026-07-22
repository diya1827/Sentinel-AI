"""Unit tests for language and package-manager detection."""

from app.services.detection import detect_languages, detect_package_managers


def test_detect_languages_picks_dominant() -> None:
    files = [
        ("app/main.py", 100),
        ("app/util.py", 50),
        ("web/index.ts", 30),
        ("README.md", 10),  # unrecognized → ignored
    ]
    primary, breakdown = detect_languages(files)
    assert primary == "Python"
    assert breakdown[0].file_count == 2
    assert breakdown[0].percentage == round(2 / 3 * 100, 2)


def test_detect_languages_empty() -> None:
    primary, breakdown = detect_languages([("README.md", 10)])
    assert primary is None
    assert breakdown == []


def test_detect_package_managers_refines_by_lockfile() -> None:
    files = [("package.json", 1), ("pnpm-lock.yaml", 1), ("requirements.txt", 1)]
    managers = detect_package_managers(files)
    assert "pnpm" in managers
    assert "npm" not in managers
    assert "pip" in managers


def test_detect_package_managers_poetry() -> None:
    managers = detect_package_managers([("pyproject.toml", 1), ("poetry.lock", 1)])
    assert managers == ["Poetry"]
