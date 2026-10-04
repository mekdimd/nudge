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


def test_bundled_svgs_render(qapp):
    from nudge.ui.icons import ASSETS, svg_pixmap

    for path in ASSETS.glob("*.svg"):
        image = svg_pixmap(path.stem, 24).toImage()
        assert any(image.pixelColor(x, y).alpha() for x in range(image.width()) for y in range(image.height())), path.name
