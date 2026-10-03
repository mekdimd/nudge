import json

import httpx
import pytest

from nudge.core import safety
from nudge.core.actions import NONE_KEY, build_options, to_action
from nudge.core.jev import JevClient, JevDecision, JevError, build_request, parse_decision
from nudge.core.models import AppRef, Control, Rect, Snapshot
from nudge.core.verify import fingerprint, wait_for_change
from nudge.core.writer import validate_fill, validate_url
from nudge.platform.fake import FakeAdapter


def snap(controls, app="Google Chrome"):
    return Snapshot(app=AppRef(app, 1), window_title="w", controls=controls)


def ctl(id, label, role="button", y=0, x=0, **kw):
    return Control(id=id, label=label, role=role, bounds=Rect(x, y, 10, 10), **kw)


# actions


def test_options_are_reading_ordered_deduped_and_end_with_none():
    s = snap([ctl("a", "Lower", y=100), ctl("b", "Upper", y=0), ctl("c", "Upper", y=0)])
    options = build_options(s)
    press = [k for k in options.keys if k.startswith("press:")]
    assert press == ["press:b", "press:a"]
    assert options.keys[-1] == NONE_KEY


def test_fill_only_offered_with_empty_fields_and_never_disabled_ones():
    s = snap([ctl("t", "Subject", role="text field", is_text_field=True, value="")])
    assert "fill" in build_options(s).criteria
    s2 = snap([ctl("t", "Subject", role="text field", is_text_field=True, value="hi")])
    assert "fill" not in build_options(s2).criteria
    s3 = snap([ctl("t", "Subject", role="text field", is_text_field=True, value="", enabled=False)])
    assert "fill" not in build_options(s3).criteria


def test_browser_only_options():
    assert "go_to_url" in build_options(snap([], app="Google Chrome")).criteria
    criteria = build_options(snap([], app="Finder")).criteria
    assert "go_to_url" not in criteria and "key:address_bar" not in criteria


def test_excluded_descriptions_and_keys_are_dropped():
    c = ctl("a", "Reload")
    options = build_options(snap([c]), excluded={c.describe(), "scroll:up"})
    assert "press:a" not in options.criteria and "scroll:up" not in options.criteria


def test_to_action_maps_every_kind():
    s = snap([ctl("a", "Send")])
    assert to_action("press:a", s).label == "Send"
    assert to_action("scroll:down", s).direction == "down"
    assert to_action("key:enter", s).key == "enter"
    assert to_action("go_to_url", s).kind == "go_to_url"
    with pytest.raises(ValueError):
        to_action("press:missing", s)
    with pytest.raises(ValueError):
        to_action("key:rm -rf", s)


# jev


def options_and_answers(choice="press:a", probs=None):
    s = snap([ctl("a", "Settings"), ctl("b", "History", y=20)])
    options = build_options(s)
    probs = probs or {"press:a": 0.8, "press:b": 0.15, NONE_KEY: 0.05}
    answers = {
        "pick": {"type": "choice", "choice": choice, "confidence": 0.7, "probabilities": probs},
        "done": {"type": "noul", "noul": 0.1},
        "absent": {"type": "noul", "noul": 0.05},
    }
    return s, options, answers


def test_parse_decision_ranks_and_reports_margin():
    _, options, answers = options_and_answers()
    d = parse_decision(answers, options, 90)
    assert d.choice == "press:a" and d.ranked[0] == ("press:a", 0.8)
    assert d.margin == pytest.approx(0.65)


@pytest.mark.parametrize(
    "choice,probs",
    [
        ("press:zzz", None),
        ("press:b", None),
        ("press:a", {"press:a": 1.5}),
        ("press:a", {"press:a": 0.9, "press:ghost": 0.1}),
    ],
)
def test_parse_decision_rejects_invalid(choice, probs):
    _, options, answers = options_and_answers(choice, probs)
    with pytest.raises(JevError):
        parse_decision(answers, options, 90)


def test_request_state_matches_criteria():
    s, options, _ = options_and_answers()
    state, questions = build_request("open settings", s, [], options)
    assert [e["id"] for e in state["screen_elements"]] == ["a", "b"]
    assert questions["pick"]["criteria"] is options.criteria
    assert state["already_done"] == ["nothing yet"]


def test_client_sends_bearer_and_parses():
    s, options, answers = options_and_answers()

    def handler(request: httpx.Request):
        assert request.headers["authorization"] == "Bearer k"
        body = json.loads(request.content)
        assert body["model"] == "jev-latest" and "pick" in body["questions"]
        return httpx.Response(200, json={"answers": answers, "usage": {"input_tokens": 321}})

    client = JevClient("k", client=httpx.Client(transport=httpx.MockTransport(handler)))
    d = client.decide("open settings", s, [], options)
    assert d.choice == "press:a" and d.input_tokens == 321


def test_client_surfaces_http_errors():
    s, options, _ = options_and_answers()
    client = JevClient("k", client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, text="bad key"))))
    with pytest.raises(JevError, match="401"):
        client.decide("x", s, [], options)


def test_client_requires_key():
    with pytest.raises(JevError):
        JevClient("")


# safety


@pytest.mark.parametrize("label", ["Send \u202a(⌘Enter)\u202c", "Delete browsing data… ⇧⌘⌫", "Place order", "Sign out"])
def test_consequential_labels(label):
    assert safety.consequential_word(label)


@pytest.mark.parametrize("label", ["Live Caption", "Settings", "Sender info", "Resend code", "Clearly"])
def test_ordinary_labels(label):
    assert safety.consequential_word(label) is None


def test_unsure_thresholds():
    sure = JevDecision("a", [("a", 0.8), ("b", 0.1)], 0, 0, 1)
    close = JevDecision("a", [("a", 0.62), ("b", 0.5)], 0, 0, 1)
    weak = JevDecision("a", [("a", 0.5), ("b", 0.1)], 0, 0, 1)
    assert not safety.is_unsure(sure)
    assert safety.is_unsure(close) and safety.is_unsure(weak)


# writer validation


def test_fill_blanks_invented_addresses():
    fields = [ctl("to", "To", role="combo box", is_text_field=True), ctl("body", "Body", is_text_field=True)]
    values, rejected = validate_fill(
        "email prof.lee@sfu.ca that I'm sick",
        fields,
        {"to": "prof.lee@sfu.ca", "body": "cc dean@sfu.ca please", "ghost": "x"},
    )
    assert values["to"] == "prof.lee@sfu.ca"
    assert values["body"] == "" and "dean@sfu.ca" in rejected["body"]
    assert "ghost" not in values


def test_url_validation():
    assert validate_url({"url": "sfu.ca/students", "confident": True}) == "https://sfu.ca/students"
    assert validate_url({"url": "https://x.com", "confident": False}) is None
    assert validate_url({"url": "javascript:alert(1)", "confident": True}) is None
    assert validate_url({"url": "not a url", "confident": True}) is None


# verify


def test_fingerprint_sees_toggle_value_changes():
    adapter = FakeAdapter.from_fixture("live_caption")
    adapter.screen = "accessibility"
    before = fingerprint(adapter.snapshot(adapter.app))
    adapter.press(adapter.snapshot(adapter.app).by_id("a1"))
    assert fingerprint(adapter.snapshot(adapter.app)) != before


def test_wait_for_change_waits_for_stability():
    a = snap([ctl("a", "A")])
    b = snap([ctl("b", "B")])
    reads = iter([a, a, b, b, b])
    result, changed = wait_for_change(lambda: next(reads), fingerprint(a), timeout=5, interval=0, sleep=lambda s: None)
    assert changed and result.controls[0].id == "b"


def test_wait_for_change_times_out_unchanged():
    a = snap([ctl("a", "A")])
    result, changed = wait_for_change(lambda: a, fingerprint(a), timeout=0.05, interval=0.01)
    assert not changed
