from engine.pipeline import _append_plate_sanity_note


def test_plate_sanity_lint_uses_configured_band_with_25_percent_tolerance(monkeypatch):
    monkeypatch.setattr(
        "engine.pipeline.load_standards",
        lambda: {"plate_sanity_g": {"1-5": [300, 500]}},
    )
    lint = {"notes": []}

    _append_plate_sanity_note(lint, 225, "1-5")
    _append_plate_sanity_note(lint, 625, "1-5")
    assert lint["notes"] == []

    _append_plate_sanity_note(lint, 224.9, "1-5")
    _append_plate_sanity_note(lint, 625.1, "1-5")
    assert len(lint["notes"]) == 2
    assert all("outside the loose 1-5 band check" in note
               for note in lint["notes"])


def test_plate_sanity_lint_ignores_unknown_band_and_missing_lint(monkeypatch):
    monkeypatch.setattr(
        "engine.pipeline.load_standards",
        lambda: {"plate_sanity_g": {"1-5": [300, 500]}},
    )
    _append_plate_sanity_note(None, 100, "1-5")
    lint = {"notes": []}
    _append_plate_sanity_note(lint, 100, "unknown")
    assert lint["notes"] == []
