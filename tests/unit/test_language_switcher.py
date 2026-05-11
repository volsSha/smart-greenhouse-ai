from app.i18n import core
from app.ui.components import language_switcher


def test_language_switcher_uses_current_language(monkeypatch) -> None:
    calls: list[str] = []
    selects: list[FakeSelect] = []

    class FakeSelect:
        def __init__(self, options: list[str], value: str, on_change) -> None:
            self.options = options
            self.value = value
            self.on_change = on_change

        def props(self, value: str) -> "FakeSelect":
            calls.append(f"props:{value}")
            return self

        def classes(self, value: str) -> "FakeSelect":
            calls.append(f"classes:{value}")
            return self

    def fake_select(options: list[str], value: str, on_change) -> FakeSelect:
        select = FakeSelect(options, value, on_change)
        selects.append(select)
        return select

    class FakeEvent:
        value = "English"

    switched_languages: list[str] = []

    monkeypatch.setattr(language_switcher, "get_current_language", lambda: "uk")
    monkeypatch.setattr(language_switcher, "set_language_and_reload", switched_languages.append)
    monkeypatch.setattr(language_switcher.ui, "select", fake_select)
    monkeypatch.setattr(core, "get_current_language", lambda: "en")

    language_switcher.language_switcher()
    selects[0].on_change(FakeEvent())

    assert selects[0].options == ["Ukrainian", "English"]
    assert selects[0].value == "Ukrainian"
    assert "props:dense outlined options-dense" in calls
    assert "classes:w-36" in calls
    assert switched_languages == ["en"]
