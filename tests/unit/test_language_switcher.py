from app.i18n import core
from app.ui.components import language_switcher


def test_language_switcher_uses_current_language(monkeypatch) -> None:
    calls: list[str] = []

    class FakeButton:
        def __init__(self, label: str) -> None:
            self.label = label

        def props(self, value: str) -> "FakeButton":
            calls.append(f"{self.label}:{value}")
            return self

        def tooltip(self, value: str) -> None:
            calls.append(f"{self.label}:tooltip:{value}")

    class FakeRow:
        def classes(self, value: str) -> "FakeRow":
            calls.append(f"row:{value}")
            return self

        def __enter__(self) -> "FakeRow":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(language_switcher, "get_current_language", lambda: "uk")
    monkeypatch.setattr(language_switcher.ui, "row", lambda: FakeRow())
    monkeypatch.setattr(language_switcher.ui, "button", lambda label, on_click: FakeButton(label))
    monkeypatch.setattr(core, "get_current_language", lambda: "en")

    language_switcher.language_switcher()

    assert "UA:color=primary" in calls
    assert "EN:flat" in calls
    assert "UA:tooltip:Ukrainian" in calls
    assert "EN:tooltip:English" in calls
