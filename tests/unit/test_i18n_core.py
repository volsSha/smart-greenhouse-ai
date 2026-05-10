from app.i18n import core


def test_normalize_language_accepts_supported_languages() -> None:
    assert core.normalize_language("en") == "en"
    assert core.normalize_language("uk") == "uk"


def test_normalize_language_falls_back_to_default() -> None:
    assert core.normalize_language("de") == core.DEFAULT_LANGUAGE
    assert core.normalize_language(None) == core.DEFAULT_LANGUAGE


def test_translate_falls_back_to_source_text_without_catalog() -> None:
    assert core.translate("Dashboard") == "Dashboard"


def test_translate_interpolates_named_values() -> None:
    assert core.translate("Greenhouse: {greenhouse_id}", greenhouse_id="gh-1") == "Greenhouse: gh-1"


def test_set_language_stores_normalized_language(monkeypatch) -> None:
    storage: dict[str, object] = {}
    monkeypatch.setattr(core, "_user_storage", lambda: storage)

    core.set_language("uk")
    assert storage["language"] == "uk"

    core.set_language("invalid")
    assert storage["language"] == core.DEFAULT_LANGUAGE


def test_get_current_language_reads_storage(monkeypatch) -> None:
    monkeypatch.setattr(core, "_user_storage", lambda: {"language": "uk"})

    assert core.get_current_language() == "uk"
