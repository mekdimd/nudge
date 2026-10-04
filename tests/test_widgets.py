import os

import pytest

from nudge.core.models import AppRef


@pytest.mark.parametrize("actor", ["you", "jev", "gemini", "vision", "nudge", "app"])
def test_every_actor_has_an_icon(qapp, actor):
    from nudge.ui.icons import actor_icon

    pixmap = actor_icon(actor, AppRef("Google Chrome", 999999), 18)
    assert not pixmap.isNull()
    assert pixmap.deviceIndependentSize().width() == 18


def test_unknown_app_falls_back_to_a_letter_avatar(qapp):
    from nudge.ui.icons import actor_icon

    assert not actor_icon("app", AppRef("Zed", 999998)).isNull()
    assert not actor_icon("app", None).isNull()


def test_icons_are_cached(qapp):
    from nudge.ui.icons import actor_icon

    assert actor_icon("jev").cacheKey() == actor_icon("jev").cacheKey()


def test_running_process_icon_loads(qapp):
    from nudge.ui.icons import actor_icon

    assert not actor_icon("app", AppRef("Python", os.getpid()), 32).isNull()


def test_orb_modes_paint_without_errors(qapp):
    from nudge.ui.orb import Orb

    orb = Orb()
    for mode in Orb.MODES:
        orb.set_mode(mode)
        orb.set_level(0.8)
        assert not orb.grab().isNull()


def test_orb_rejects_unknown_modes(qapp):
    from nudge.ui.orb import Orb

    with pytest.raises(ValueError):
        Orb().set_mode("dancing")


def test_orb_level_rises_fast_and_falls_slowly(qapp):
    from nudge.ui.orb import Orb

    orb = Orb()
    orb.set_level(1.0)
    orb._step()
    risen = orb.level
    orb.set_level(0.0)
    orb._step()
    assert risen == pytest.approx(0.5)
    assert orb.level == pytest.approx(0.5 - 0.5 * 0.15)


def test_orb_level_is_clamped(qapp):
    from nudge.ui.orb import Orb

    orb = Orb()
    orb.set_level(7.0)
    assert orb._target == 1.0
    orb.set_level(-1.0)
    assert orb._target == 0.0


def test_feed_shows_rows_and_updates_in_place(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    assert not feed.isVisible()
    timeline.add(Entry("you", "turn on Live Caption"))
    i = timeline.add(Entry("jev", "Choosing the next step", state="running"))
    assert feed.isVisible() and len(feed.rows) == 2
    row = feed.rows[i]
    assert row.spinner.isVisibleTo(row) and row.shimmer.isVisibleTo(row) and not row.text.isVisibleTo(row)
    timeline.set(i, Entry("jev", "Picked", "Settings", detail="92% · 130 ms"))
    assert len(feed.rows) == 2
    assert not row.spinner.isVisibleTo(row) and row.text.text() == "Picked <b>Settings</b>"
    assert row.mark.text() == "✓" and row.detail.text() == "92% · 130 ms"


def test_feed_marks_failures_and_waits(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    timeline.add(Entry("app", "Pressed", "Play", state="failed", detail="nothing changed"))
    timeline.add(Entry("nudge", "Waiting for your OK", state="waiting"))
    assert [r.mark.text() for r in feed.rows] == ["✕", "•"]


def test_feed_clears_and_hides(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    feed.show()
    timeline.add(Entry("you", "x"))
    timeline.clear()
    assert feed.rows == [] and not feed.isVisible()


def test_feed_stops_growing_and_scrolls(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    feed.show()
    for n in range(30):
        timeline.add(Entry("jev", "Picked", f"Option {n}"))
    assert feed.height() <= Feed.MAX_HEIGHT


def test_feed_paints_every_state(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    for state in ("running", "done", "failed", "waiting"):
        timeline.add(Entry("jev", "Picked", "Settings", state=state))
    for row in feed.rows:
        row.spinner.grab()
        row.shimmer.grab()
    assert not feed.grab().isNull()


def test_feed_grows_with_each_row(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    timeline.add(Entry("jev", "Picked", "One"))
    one = feed.height()
    timeline.add(Entry("jev", "Picked", "Two"))
    assert feed.height() > one


def test_jev_and_gemini_icons_explain_what_they_receive(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    timeline.add(Entry("jev", "Picked", "Settings"))
    timeline.add(Entry("gemini", "Wrote the text"))
    assert "labels" in feed.rows[0].icon.toolTip()
    assert "goal" in feed.rows[1].icon.toolTip()


def test_bundled_svgs_render(qapp):
    from nudge.ui.icons import ASSETS, svg_pixmap

    for path in ASSETS.glob("*.svg"):
        image = svg_pixmap(path.stem, 24).toImage()
        assert any(image.pixelColor(x, y).alpha() for x in range(image.width()) for y in range(image.height())), path.name
