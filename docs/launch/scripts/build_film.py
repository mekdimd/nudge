"""Build the launch film from recorded browser actions and Qt decisions."""

import json
import math
import subprocess
import wave
from pathlib import Path

P = Path(__file__).resolve().parents[1]
A = P / "assets" / "browser"
SOUND_CUES = []


def encode(source, destination, start, duration, filters="fps=60"):
    assert start >= 0 and duration > 0, (source, start, duration)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            str(start),
            "-i",
            str(source),
            "-t",
            str(duration),
            "-vf",
            filters,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(destination),
        ],
        check=True,
    )


def timed_video(id, source, start, duration, cls):
    return (
        f'<video id="{id}" class="clip {cls}" src="assets/browser/{source}" muted playsinline '
        f'data-start="{start}" data-duration="{duration}" data-track-index="1" data-beat="{id}" data-hf-media-start-basis="local"></video>'
    )


def actor(id, human=False, start=None, duration=None):
    timing = (
        f' data-start="{start}" data-duration="{duration}"' if start is not None else ""
    )
    trail = (
        ""
        if human
        else (
            '<svg class="cursor-trail" aria-hidden="true" data-layout-ignore>'
            + "".join(f'<path id="{id}-trail-{i}"/>' for i in range(4))
            + "</svg>"
        )
    )
    return (
        trail
        + f'<img id="{id}" class="{"clip " if timing else ""}actor{" human" if human else ""}" src="assets/{"human-cursor.svg" if human else "pointer.png"}" alt="" data-layout-ignore{timing}>'
    )


def ring(id, miss=False):
    return f'<div id="{id}" class="ring{" miss" if miss else ""}" data-layout-ignore></div>'


def scene(name, duration, body, script, styles=""):
    (P / "compositions" / f"{name}.html").write_text(f'''<template>
<style>#root{{position:absolute;inset:0}}{styles}</style>
<div id="root" class="scene" data-composition-id="{name}" data-width="1920" data-height="1080" data-duration="{duration}">{body}</div>
<script>{{const tl=gsap.timeline({{paused:true}});{script}window.__timelines["{name}"]=tl;}}</script>
</template>
''')


def cue(name, at, volume=0.4, duration=None):
    SOUND_CUES.append((name, at, volume, duration))


def caption(ident, text, start, duration):
    return (
        f'<div id="{ident}-caption" class="clip" data-start="{start}" data-duration="{duration}" '
        f'data-track-index="7" data-beat="{ident}"><p class="guidance" data-hold>{text}</p></div>'
    )


def focus_shot(ident, content, start, duration, width, height, kind, top=None):
    top = round((1080 - height) / 2 + 36, 3) if top is None else top
    body = (
        f'<div id="{ident}-host" style="position:absolute;inset:0"><div id="{ident}-window" class="guided-window {kind}" '
        f'style="opacity:0;left:{(1920 - width) / 2}px;top:{top}px;width:{width}px;height:{height}px" '
        f'data-layout-allow-overflow><div id="{ident}-stage" class="guided-stage">{content}</div></div></div>'
    )
    script = (
        f'tl.fromTo("#{ident}-window",{{opacity:0,x:{60 if kind == "ui" else -60}}},'
        f'{{opacity:1,x:0,duration:.3,ease:"power2.out"}},{start});'
    )
    script += (
        f'tl.to("#{ident}-window",{{opacity:0,duration:.2}},{start + duration - 0.4});'
    )
    return body, script


def mask_script(ident, path, crop_h, width, start, background=0):
    # Follow the encoded bar boundary as its recorded height changes.
    import numpy as np

    pixels = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            f"crop=10:{crop_h}:450:0,format=gray",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    rows = np.frombuffer(pixels, dtype=np.uint8).reshape(-1, crop_h, 10).mean(axis=2)
    visible = np.abs(rows - background) > (8 if background == 0 else 3)
    heights = crop_h - np.argmax(visible[:, ::-1], axis=1)
    script = ""
    previous = None
    for frame, height in enumerate(heights):
        bottom = round(max(0, crop_h - int(height)) * width / 910, 3)
        if bottom != previous:
            script += f'tl.set("#{ident}-mask",{{clipPath:"inset(0 0 {bottom}px 0 round 44px)"}},{round(start + frame / 60, 4)});'
            previous = bottom
    return script


def ui_shot(case, ident, source_start, source_duration, start, duration, title):
    trace = json.loads((A / f"{case}-trace.json").read_text())
    first = trace["ui_frames"][0]
    samples = [
        (t - first, size[1] * 0.65)
        for t, size in zip(trace["ui_frames"], trace["ui_sizes"])
    ]
    before = [x for x in samples if x[0] <= source_start]
    selected = [before[-1]] + [
        x for x in samples if source_start < x[0] < source_start + source_duration
    ]
    crop_h = min(1000, math.ceil(max(h for _, h in selected) / 2) * 2)
    stretch = duration / source_duration
    encode(
        A / f"{case}-nudge.mp4",
        A / f"{ident}.mp4",
        source_start,
        duration,
        f"crop=910:{crop_h}:0:0,trim=duration={source_duration},setpts=(PTS-STARTPTS)*{stretch},fps=60",
    )
    width = 1372
    scale = width / 910
    content = (
        f'<div id="{ident}-mask" class="ui-mask">'
        + timed_video(ident + "-video", ident + ".mp4", start, duration, "guided-media")
        + "</div>"
    )
    body, script = focus_shot(
        ident, content, start, duration, width, crop_h * scale, "ui"
    )
    script += mask_script(ident, A / f"{ident}.mp4", crop_h, width, start)
    return body + caption(ident, title, start, duration), script


def still_ui(case, tag, ident, start, duration, title):
    from PySide6.QtGui import QImage

    size = QImage(str(A / f"{case}-{tag}.png"))
    width = 1372
    height = size.height() * width / size.width()
    body, script = focus_shot(
        ident,
        f'<img class="guided-media" src="assets/browser/{case}-{tag}.png" alt="Actual Nudge interface">',
        start,
        duration,
        width,
        height,
        "ui",
    )
    return body + caption(ident, title, start, duration), script


def screen_shot(
    case,
    ident,
    source_start,
    start,
    duration,
    title,
    action=None,
    action_at=None,
    source_duration=None,
):
    source_duration = source_duration or duration
    tail = max(0, duration - source_duration)
    encode(
        A / f"{case}.webm",
        A / f"{ident}.mp4",
        source_start,
        duration,
        f"crop=1280:712:0:0,trim=duration={source_duration},tpad=stop_mode=clone:stop_duration={tail},fps=60",
    )
    width = 1376
    height = width * 712 / 1280
    content = timed_video(
        ident + "-video", ident + ".mp4", start, duration, "guided-media"
    )
    content += actor(ident + "-cursor", False, start, duration) + ring(ident + "-ring")
    body, script = focus_shot(
        ident, content, start, duration, width, height, "browser", top=200
    )
    if action is not None:
        point = [round(v * width / 1280, 3) for v in action["center"]]
        when = start + action_at - (0.08 if action["operation"] == "click" else 0)
        script += f'launchMove(tl,"#{ident}-cursor",[860,270],{point},{when - 0.3},.3);'
        if ident != "jev-action":
            script += f'launchCamera(tl,"#{ident}-stage",{point},{when - 0.3},{width},{height});'
        if action["operation"] == "click":
            script += (
                f'launchClick(tl,"#{ident}-cursor","#{ident}-ring",{point},{when});'
            )
            cue("click-soft.mp3", ABS_START + when, 0.65)
        else:
            cue("typing.mp3", ABS_START + when, 0.32, 2.92)
        script += f'tl.to("#{ident}-cursor",{{opacity:0,duration:.15}},{when + (0.65 if action["operation"] == "click" else 2.3)});'
    return body + caption(ident, title, start, duration), script


def build_task(case, absolute_start):
    global ABS_START
    ABS_START = absolute_start
    data = json.loads((A / f"{case}-actions.json").read_text())
    trace = json.loads((A / f"{case}-trace.json").read_text())
    body = script = ""
    phases = []

    def add(result, name, start, duration):
        nonlocal body, script
        b, s = result
        body += b
        script += s
        phases.append([name, start, duration])

    title = (
        "Download a bank statement."
        if case == "bank"
        else "Find an Excel tutorial on YouTube."
    )
    add(still_ui(case, "idle", case + "-request", 0, 1.8, title), "request", 0, 1.8)
    thought = next(
        e["at"]
        for e in trace["events"]
        if e["kind"] == "status" and e["text"].startswith("Jev is choosing")
    )
    source = thought - trace["ui_frames"][0] + 0.04
    add(
        ui_shot(
            case,
            case + "-thinking",
            source,
            1.08,
            1.8,
            2.0,
            "Nudge finds the next control.",
        ),
        "thinking",
        1.8,
        2.0,
    )
    clock = 3.8
    actions = data["actions"]
    intervals = []
    for i, a in enumerate(actions):
        duration = (
            4.7
            if a["operation"] == "type"
            else 4.2
            if case == "youtube"
            else 3.0
            if i == len(actions) - 1
            else 2.4
        )
        before = 0.95
        # Decoded page changes align the cursor with the recorded action.
        source_click = [8.76, 12.44, 15.92][i] if case == "bank" else [9.72, 15.60][i]
        source_start = source_click - before
        content_title = (
            "Nudge types the search for you."
            if a["operation"] == "type"
            else "Nudge handles the clicks."
        )
        add(
            screen_shot(
                case,
                f"{case}-action-{i}",
                source_start,
                clock,
                duration,
                content_title,
                a,
                before,
            ),
            f"action-{i}",
            clock,
            duration,
        )
        intervals.append([source_start, clock, duration])
        clock += duration
    add(
        still_ui(
            case,
            "done",
            case + "-completed",
            clock,
            1.6,
            "Statement downloaded." if case == "bank" else "Search complete.",
        ),
        "completed",
        clock,
        1.6,
    )
    clock = round(clock + 1.6, 3)
    scene(case, clock, body, script)
    cue("start.wav", absolute_start + 0.15, 0.38)
    cue("success.wav", absolute_start + clock - 1.55, 0.42)
    return {"duration": clock, "phases": phases, "browser_intervals": intervals}


def browser_clip(name, source_start, duration, stretch=1):
    encode(
        A / "mail.webm",
        A / f"{name}.mp4",
        source_start,
        duration,
        f"crop=1280:712:0:0,setpts=(PTS-STARTPTS)*{stretch},fps=60",
    )


def panel_clip(name, prompt, source_start, duration, stretch=1, hold=0):
    x, y, w, h = prompt["panel_rect"]
    # The recording encoder scales Qt's device-pixel image by 0.65.
    crop = [round(v * 0.65 / 2) * 2 for v in (w, h, x, y)]
    tail = (
        f",trim=duration={duration - hold},tpad=stop_mode=clone:stop_duration={hold}"
        if hold
        else ""
    )
    encode(
        A / "mail-nudge.mp4",
        A / f"{name}-panel.mp4",
        source_start,
        duration,
        f"crop={':'.join(map(str, crop))},setpts=(PTS-STARTPTS)*{stretch}{tail},fps=60",
    )
    encode(
        A / "mail-nudge.mp4",
        A / f"{name}-header.mp4",
        source_start,
        duration,
        f"crop=910:62:0:0,setpts=(PTS-STARTPTS)*{stretch}{tail},fps=60",
    )


def build_mail(absolute_start):
    trace = json.loads((A / "mail-trace.json").read_text())
    draft, confirm = trace["prompts"]
    first = trace["ui_frames"][0]
    events = {e["kind"]: e for e in trace["events"] if e["kind"].startswith("edit-")}
    approvals = {e["prompt"]: e for e in trace["events"] if e["kind"] == "approve"}
    draft_source = draft["at"] - first + 0.10
    draft_stretch = 1
    panel_clip("mail-review", draft, draft_source, 5.2, draft_stretch, hold=1.2)
    encode(
        A / "mail-nudge.mp4",
        A / "mail-writing.mp4",
        4.20,
        3.9,
        "crop=910:350:0:0,trim=duration=3.7,tpad=stop_mode=clone:stop_duration=0.2,fps=60",
    )
    confirm_source = confirm["at"] - first + 0.05
    panel_clip("mail-approval", confirm, confirm_source, 2.4, hold=0.6)
    browser_clip("mail-compose", 4.55, 2.6)
    # Page changes, rather than the browser recorder's wall-clock offset, locate typing.
    browser_clip("mail-fill", 15.78, 6.2, 1.32)
    browser_clip("mail-send", 22.50, 2.8)
    body = ""
    script = ""
    phases = [
        ("compose", 0, 2.6, "browser"),
        ("writing", 2.4, 3.9, "writing"),
        ("review", 6.1, 5.2, "draft"),
        ("fill", 11.1, 6.2, "browser"),
        ("approval", 17.1, 2.4, "confirm"),
        ("send", 19.3, 3.9, "browser"),
    ]
    for name, start, duration, kind in phases:
        ident = f"mail-{name}"
        titles = {
            "compose": "Write an email to my professor.",
            "writing": "Nudge works out the next steps.",
            "review": "Edit the draft before Nudge types it.",
            "fill": "Nudge types it for you.",
            "approval": "Approve sending the email.",
            "send": "Then Nudge clicks Send.",
        }
        body += caption(
            ident, titles[name], start, duration if name == "send" else duration - 0.2
        )
        cls = "focus-browser" if kind == "browser" else f"focus-nudge {kind}"
        content = ""
        if kind == "browser":
            media_duration = 2.8 if name == "send" else duration
            content += timed_video(
                ident + "-video", ident + ".mp4", start, media_duration, "focus-media"
            )
            if name == "send":
                content += f'<div id="mail-result-hold" class="clip" data-start="{round(start + media_duration, 3)}" data-duration="{round(duration - media_duration, 3)}" data-track-index="2" data-hold><img class="focus-media" src="assets/browser/mail-page-done-viewport.png" alt="Edited email sent to Professor Lee"></div>'
        elif kind == "writing":
            content += (
                '<div id="mail-writing-mask" class="ui-mask">'
                + timed_video(
                    ident + "-video", ident + ".mp4", start, duration, "focus-media"
                )
                + "</div>"
            )
            script += mask_script(
                "mail-writing", A / "mail-writing.mp4", 350, 1372, start, 37
            )
        else:
            content += timed_video(
                ident + "-header",
                ident + "-header.mp4",
                start,
                duration,
                "focus-header",
            )
            content += timed_video(
                ident + "-panel", ident + "-panel.mp4", start, duration, "focus-panel"
            )
        content += actor(ident + "-cursor", kind != "browser", start, duration)
        if name in ["compose", "review", "approval", "send"]:
            content += ring(ident + "-ring")
        body += f'<div id="{ident}-window" style="position:absolute;inset:0;z-index:{2 + phases.index((name, start, duration, kind))}"><div class="{cls} focus-window" data-layout-allow-overflow><div id="{ident}-stage" class="focus-stage">{content}</div></div></div>'
        # Crossfades carry only one cursor. Actions begin after the new window lands.
        if start:
            script += f'tl.fromTo("#{ident}-window .focus-window",{{x:{-70 if kind == "browser" else 70},opacity:0}},{{x:0,opacity:1,duration:.2,ease:"power2.out"}},{start});'
        else:
            script += f'tl.set("#{ident}-window .focus-window",{{opacity:1}},0);'
        if name != "send":
            script += f'tl.to("#{ident}-window .focus-window",{{x:{70 if kind == "browser" else -70},opacity:0,duration:.2,ease:"power2.in"}},{start + duration - 0.4});'
    scale = 1376 / 1280
    compose_point = [110.5 * scale, 138 * scale]
    script += f'launchMove(tl,"#mail-compose-cursor",[600,250],{compose_point},.53,.28);launchClick(tl,"#mail-compose-cursor","#mail-compose-ring",{compose_point},.85);tl.to("#mail-compose-cursor",{{opacity:0,duration:.1}},1.35);'
    cue("start.wav", absolute_start + 0.05, 0.38)
    cue("click-soft.mp3", absolute_start + 0.85, 0.65)

    def draft_time(at):
        return 6.1 + (at - first - draft_source) * draft_stretch

    def panel_point(prompt, point):
        x, y, w, _ = prompt["panel_rect"]
        return [
            round((point[0] * 2 - x) * 1240 / w, 3),
            round(84.545 + (point[1] * 2 - y) * 1240 / w, 3),
        ]

    selection = events["edit-select"]
    left, right = [panel_point(draft, selection[p]) for p in ["start", "end"]]
    select_at = draft_time(selection["at"])
    script += f'launchMove(tl,"#mail-review-cursor",[740,245],{left},{select_at - 0.35},.28);tl.to("#mail-review-cursor",{{x:{right[0]},y:{right[1]},duration:.2,ease:"power1.inOut"}},{select_at - 0.20});'
    typed_at = draft_time(events["edit-typing"]["at"])
    typed_end = draft_time(events["edit-subject"]["at"])
    cue("typing.mp3", absolute_start + typed_at, 0.42, typed_end - typed_at)
    detail_start, detail_duration = 7.25, 2.7
    encode(
        A / "mail-review-panel.mp4",
        A / "mail-subject-detail.mp4",
        detail_start - 6.1,
        detail_duration,
        "crop=432:100:16:164,fps=60",
    )
    content = timed_video(
        "mail-subject-video", "mail-subject-detail.mp4",
        detail_start, detail_duration, "guided-media"
    ) + actor("mail-subject-cursor", True, detail_start, detail_duration)
    b, t = focus_shot(
        "mail-subject", content, detail_start, detail_duration,
        1376, 318.52, "ui", 400
    )
    body += b
    script += t
    script += 'tl.to("#mail-review-window .focus-window",{opacity:0,duration:.18},7.25);tl.to("#mail-review-window .focus-window",{opacity:1,duration:.2},9.75);'
    def subject_point(point):
        x, y, _, _ = draft["panel_rect"]
        return [
            round(((point[0] * 2 - x) * .65 - 16) * 1376 / 432, 3),
            round(((point[1] * 2 - y) * .65 - 164) * 1376 / 432, 3),
        ]
    detail_left, detail_right = [
        subject_point(selection[p]) for p in ["start", "end"]
    ]
    script += f'launchMove(tl,"#mail-subject-cursor",[490,80],{detail_left},{select_at - .35},.28);tl.to("#mail-subject-cursor",{{x:{detail_right[0]},y:{detail_right[1]},duration:.2,ease:"power1.inOut"}},{select_at - .2});'
    approval = panel_point(draft, approvals["draft"]["center"])
    approve_at = 10.90
    script += f'launchMove(tl,"#mail-review-cursor",{right},{approval},{approve_at - 0.32},.28);launchClick(tl,"#mail-review-cursor","#mail-review-ring",{approval},{approve_at});tl.to("#mail-review-cursor",{{opacity:0,duration:.07}},{approve_at + 0.07});'
    cue("click-soft.mp3", absolute_start + approve_at, 0.65)
    # These field starts were checked in decoded browser frames at 25 fps.
    previous = [850, 210]
    for j, (source_at, source_end, point) in enumerate(
        [
            (16.12, 16.52, [743.5, 272]),
            (16.56, 17.12, [743.5, 337]),
            (17.16, 18.52, [701, 487.5]),
        ]
    ):
        at = 11.1 + (source_at - 15.78) * 1.32
        target = [round(v * scale, 3) for v in point]
        script += (
            f'launchMove(tl,"#mail-fill-cursor",{previous},{target},{at - 0.25},.25);'
        )
        script += (
            f'launchCamera(tl,"#mail-fill-stage",{target},{at - 0.25},1376,765.4);'
        )
        cue("typing.mp3", absolute_start + at, 0.30, (source_end - source_at) * 1.32)
        previous = target
    script += 'tl.to("#mail-fill-cursor",{opacity:0,duration:.1},16.4);'
    send_approval = panel_point(confirm, approvals["confirm"]["center"])
    # Keep the source panel before it closes; the visible approval marks its actual action.
    yes_at = 19.15
    script += f'launchMove(tl,"#mail-approval-cursor",[1030,190],{send_approval},{yes_at - 0.32},.28);launchClick(tl,"#mail-approval-cursor","#mail-approval-ring",{send_approval},{yes_at});tl.to("#mail-approval-cursor",{{opacity:0,duration:.07}},{yes_at + 0.07});'
    cue("attention.wav", absolute_start + 17.3, 0.3)
    cue("click-soft.mp3", absolute_start + yes_at, 0.65)
    send_point = [340.5625 * scale, 646 * scale]
    script += f'launchMove(tl,"#mail-send-cursor",[780,535],{send_point},19.45,.3);launchClick(tl,"#mail-send-cursor","#mail-send-ring",{send_point},19.76);tl.to("#mail-send-cursor",{{opacity:0,duration:.1}},20.25);'
    cue("click-soft.mp3", absolute_start + 19.76, 0.65)
    cue("success.wav", absolute_start + 20.07, 0.42)
    styles = ".focus-window{position:absolute;overflow:hidden;border-radius:24px}.focus-browser{left:272px;top:200px;width:1376px;height:765.4px;background:#f5f5fb;border:1px solid #d4dce4;border-radius:14px}.focus-nudge{border-radius:44px;left:340px;top:184px;width:1240px;background:transparent}.focus-nudge.draft{height:826.67px}.focus-nudge.confirm{top:422px;height:306.25px}.focus-nudge.writing{left:274px;top:312px;width:1372px;height:527.69px}.focus-stage{position:absolute;inset:0;transform-origin:0 0}.focus-media{position:absolute;inset:0;width:100%;height:100%;object-fit:fill}.focus-header{position:absolute;inset:auto;left:0;top:0;width:1240px;height:84.545px;object-fit:fill}.focus-panel{position:absolute;inset:auto;left:0;top:84.545px;width:1240px;height:742.12px;object-fit:fill}.confirm .focus-panel{height:221.7px}"

    scene("mail", 23.2, body, script, styles)
    return {
        "duration": 23.2,
        "phases": phases,
        "draft_source": draft_source,
        "draft_stretch": draft_stretch,
        "fill_source": [15.78, 6.2, 1.32],
        "field_starts": [16.12, 16.56, 17.16],
        "send_source": 22.50,
        "processing_source": [4.2, 3.7],
        "processing_hold_seconds": trace["processing_hold_seconds"],
    }


def build_jev(absolute_start):
    global ABS_START
    ABS_START = absolute_start
    trace = json.loads((A / "jev-trace.json").read_text())
    actions = json.loads((A / "jev-actions.json").read_text())
    body, script = still_ui(
        "jev", "peek-off", "jev-enable", 0, 2.4, "Enable Peek to see the controls."
    )
    addition = (
        '<div id="jev-peek-on" class="clip" data-start="1.7" data-duration=".7" data-track-index="3">'
        '<img class="guided-media" src="assets/browser/jev-peek-enabled.png" alt="Peek enabled"></div>'
        '<div id="peek-spotlight" class="focus-spotlight" style="--spot-x:89%;--spot-y:18%"></div>'
    )
    body = body.replace("</div></div></div>", addition + "</div></div></div>", 1)
    script += 'tl.to("#peek-spotlight",{opacity:1,duration:.3},.45);tl.to("#peek-spotlight",{opacity:0,duration:.25},1.9);'
    content = (
        '<img class="guided-media" src="assets/browser/jev-peek-button-off.png" alt="Peek button">'
        '<div id="jev-peek-detail-on" class="clip" data-start="1.7" data-duration=".7" data-track-index="3"><img class="guided-media" src="assets/browser/jev-peek-button-on.png" alt="Peek enabled"></div>'
        + actor("peek-human", True, .9, 1.5) + ring("peek-click")
    )
    b, t = focus_shot("jev-peek-detail", content, .9, 1.5, 540, 324, "ui", 380)
    body += b
    script += t + 'tl.to("#jev-enable-window",{opacity:0,duration:.2},.9);'
    script += 'launchMove(tl,"#peek-human",[70,60],[270,162],1.35,.3);launchClick(tl,"#peek-human","#peek-click",[270,162],1.7);tl.to("#peek-human",{opacity:0,duration:.12},2.0);'
    cue("click-soft.mp3", absolute_start + 1.7, 0.65)
    content = (
        '<img class="guided-media" src="assets/browser/jev-page-idle-viewport.png" alt="VS Code issue tracker">'
        '<div id="jev-boxes" class="clip" data-start="2.4" data-duration="3.4" data-track-index="3">'
        '<img class="guided-media" src="assets/browser/jev-peek-viewport.png" alt="Actual Peek control outlines"></div>'
    )
    b, t = focus_shot("jev-controls", content, 2.4, 3.4, 1376, 765.4, "browser", 200)
    body += b + caption("jev-controls", "Peek outlines what Nudge can see.", 2.4, 3.4)
    script += t
    script += 'tl.fromTo("#jev-boxes img",{clipPath:"inset(0 100% 0 0)"},{clipPath:"inset(0 0 0 0)",duration:.8,ease:"power2.inOut"},2.7);'
    thinking = next(
        e["at"]
        for e in trace["events"]
        if e["kind"] == "status" and e["text"].startswith("Jev is choosing")
    )
    b, t = ui_shot(
        "jev",
        "jev-thinking",
        thinking - trace["ui_frames"][0] + 0.1,
        1.22,
        5.8,
        3.4,
        "Jev is TypeSafe AI's decision model.",
    )
    body += b
    script += t
    choice = next(e["at"] for e in trace["events"] if e["kind"] == "choice")
    b, t = ui_shot(
        "jev",
        "jev-deciding",
        choice - trace["ui_frames"][0] + 0.04,
        0.95,
        9.2,
        1.6,
        "Jev chooses Labels.",
    )
    body += b
    script += t
    action = actions["actions"][0]
    source = 9.80 - 0.95
    b, t = screen_shot(
        "jev", "jev-action", source, 10.8, 3.6, "Jev chooses Labels.", action, 0.95
    )
    point = [v * 1376 / 1280 for v in action["center"]]
    overlay = (
        '<div id="jev-chosen-boxes" style="z-index:2" class="clip" data-start="10.8" data-duration=".84" data-track-index="3">'
        '<div id="jev-chosen-layer" style="position:absolute;inset:0">'
        '<img class="guided-media" src="assets/browser/jev-selected-viewport.png" alt="Peek outlines with Labels selected">'
        f'<div class="focus-spotlight" style="opacity:1;--spot-x:{point[0] / 1376 * 100:.3f}%;--spot-y:{point[1] / 765.4 * 100:.3f}%;mask-image:radial-gradient(ellipse 12% 10% at var(--spot-x) var(--spot-y),transparent 0%,transparent 45%,black 85%)"></div>'
        f'<div style="position:absolute;z-index:4;left:{point[0] - 118}px;top:{point[1] - 17}px;width:236px;height:34px;border:3px solid #5087ed;border-radius:6px"></div>'
        '</div></div>'
    )
    b = b.replace(
        '<div id="jev-action-stage" class="guided-stage">',
        '<div id="jev-action-stage" class="guided-stage">' + overlay,
    )
    body += b
    script += t
    script += 'tl.to("#jev-chosen-layer",{opacity:0,duration:.18},11.43);'
    cue("tick.wav", absolute_start + 9.2, 0.38)
    cue("success.wav", absolute_start + 12.3, 0.4)
    scene("jev", 14.4, body, script)
    return {
        "duration": 14.4,
        "source": "https://github.com/microsoft/vscode/issues",
        "peek_controls": next(
            e["count"] for e in trace["events"] if e["kind"] == "peek"
        ),
        "phases": [
            ["enable Peek", 0, 2.4],
            ["control outlines", 2.4, 3.4],
            ["Jev processing", 5.8, 3.4],
            ["Jev decision", 9.2, 1.6],
            ["chosen action", 10.8, 3.6],
        ],
    }


def build_brand():
    misses = [(206, 258), (1220, 340), (770, 214)]
    body = (
        '<div class="hook-screen"><div id="hook-stage" data-layout-allow-overflow><img class="hook-media" src="assets/browser/bank-page-idle.png" alt="Bank website">'
        + actor("hook-cursor", True)
        + "".join(ring("miss-" + str(i), True) for i in range(3))
        + '<div id="hook-assisted-page" class="clip" data-start="4.13" data-duration="1.27" data-track-index="3"><img class="hook-media" src="assets/browser/bank-state-1.png" alt="Statements opened"></div></div></div>'
        '<div id="hook-copy"><h1>Hard to click?</h1></div>'
        + actor("bridge-cursor")
        + ring("assist-ring")
    )
    script = 'tl.set("#hook-cursor",{x:850,y:240,opacity:1});'
    source = [650, 180]
    for i, target in enumerate(misses):
        a = [round(x * 1.3125, 3) for x in source]
        b = [round(x * 1.3125, 3) for x in target]
        at = 0.25 + i * 0.72
        script += f'launchMove(tl,"#hook-cursor",{a},{b},{at},.24);launchClick(tl,"#hook-cursor","#miss-{i}",{b},{at + 0.25});'
        cue("click-soft.mp3", at + 0.25, 0.65)
        source = target
    script += 'tl.to("#hook-cursor",{opacity:0,duration:.15},2.4);tl.to("#hook-stage",{opacity:.2,duration:.28},2.42);tl.to("#hook-copy",{opacity:1,duration:.34,ease:"power2.out"},2.5);'
    script += 'tl.to("#hook-copy",{opacity:0,duration:.25},3.7);tl.to("#hook-stage",{opacity:1,duration:.25},3.7);'
    target = [120 + 107.5 * 1.3125, 90 + 258 * 1.3125]
    script += f'launchMove(tl,"#bridge-cursor",[1820,820],{target},3.75,.30);launchClick(tl,"#bridge-cursor","#assist-ring",{target},4.08);'
    script += 'tl.to(".hook-screen",{opacity:0,duration:.55},4.5);tl.to("#bridge-cursor",{x:1240,y:365,scale:2.3,duration:.86,ease:"power3.inOut"},4.5);'
    scene(
        "hook",
        5.4,
        body,
        script,
        ".hook-screen{border:none}#bridge-cursor{width:112px;height:112px;left:-14px;top:-14px}",
    )
    cue("attention.wav", 2.48, 0.3)
    cue("click-soft.mp3", 4.08, 0.65)
    cue("tick.wav", 4.4, 0.38)
    reveal = '<div id="reveal-title" data-hold><p class="reveal-intro">Meet</p><h1 class="wordmark">Nudge</h1></div><img id="reveal-cursor" class="actor" src="assets/pointer.png" alt="" data-layout-ignore>'
    scene(
        "reveal",
        3.0,
        reveal,
        'tl.set("#reveal-cursor",{x:1240,y:365,scale:2.3,opacity:1});tl.fromTo("#reveal-title",{y:45,opacity:0},{y:0,opacity:1,duration:.3,ease:"power3.out"},.06);',
        ".wordmark{left:300px;top:365px;font-size:250px}.reveal-intro{position:absolute;left:314px;top:286px;font-size:76px;font-weight:450;color:var(--ink)}",
    )
    outro = '<h1 id="outro-word" class="wordmark">Nudge</h1><p id="outro-line" class="closing-line" data-var-text="tagline" data-hold>Computer control for<br>limited dexterity</p><p class="repository" data-var-text="repository" data-hold>github.com/mekdimd/nudge</p><img id="outro-cursor" class="actor" src="assets/pointer.png" alt="" data-layout-ignore>'
    scene(
        "outro",
        4.6,
        outro,
        'tl.fromTo("#outro-word",{x:-55,opacity:0},{x:0,opacity:1,duration:.23,ease:"power3.out"},0);tl.fromTo("#outro-line",{y:20,opacity:0},{y:0,opacity:1,duration:.25,ease:"power3.out"},.12);tl.fromTo("#outro-cursor",{x:1510,y:710,scale:1.8,rotation:14},{x:1360,y:390,scale:2.3,rotation:0,opacity:1,duration:.3,ease:"power3.out"},.04);',
        ".closing-line{width:1080px;font-size:78px;line-height:1.08;top:540px;white-space:pre-line}.repository{top:790px;font-size:58px}",
    )


def main():
    import os

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage

    for tag in ["page-idle", "peek", "choice"]:
        img = QImage(str(A / f"jev-{tag}.png"))
        img = img.scaled(
            1280,
            800,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        img.copy(0, 0, 1280, 712).save(str(A / f"jev-{tag}-viewport.png"))
    img = QImage(str(A / "mail-page-done.png"))
    img.copy(0, 0, 1280, 712).save(str(A / "mail-page-done-viewport.png"))
    QImage(str(A / "jev-peek-viewport.png")).save(str(A / "jev-selected-viewport.png"))
    for tag, source in [("off", "off"), ("on", "enabled")]:
        QImage(str(A / f"jev-peek-{source}.png")).copy(1178, 14, 140, 84).save(
            str(A / f"jev-peek-button-{tag}.png")
        )
    build_brand()
    body, script = ui_shot(
        "wake", "wake-listening", 0.12, 5.4, 0, 5.8, 'Say "Hey Nudge" to start.'
    )
    body += caption("wake-request", "Then say what you need.", 2.3, 3.5)
    # One caption replaces the other as the transcript begins.
    body = body.replace(
        'data-duration="5.8" data-track-index="7"',
        'data-duration="2.3" data-track-index="7"',
    )
    scene("wake", 5.8, body, script)
    cue("listen.wav", 8.4 + 0.8, 0.5)
    slots = [("hook", 0, 5.4), ("reveal", 5.4, 3.0), ("wake", 8.4, 5.8)]
    clock = 14.2
    cut = {}
    for name, builder in [
        ("bank", build_task),
        ("youtube", build_task),
        ("jev", build_jev),
        ("mail", build_mail),
    ]:
        result = builder(name, clock) if builder == build_task else builder(clock)
        cut[name] = result
        slots.append((name, clock, result["duration"]))
        clock = round(clock + result["duration"], 3)
    slots.append(("outro", clock, 4.6))
    duration = round(clock + 4.6, 3)
    (A / "edit-points-v6.json").write_text(json.dumps(cut, indent=2) + "\n")
    (P / "shot-slots.json").write_text(json.dumps(slots, indent=2) + "\n")
    (P / "compositions/search.html").write_text(
        (P / "compositions/youtube.html").read_text()
    )
    (P / "compositions/youtube.html").unlink()
    hosts = "".join(
        f'<div id="{name}" class="clip" data-composition-id="{name}" data-composition-src="compositions/{"search" if name == "youtube" else name}.html" data-start="{start}" data-duration="{length}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>'
        for name, start, length in slots
    )
    original = P / "assets/inspired-source.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            "16",
            "-i",
            str(original),
            "-t",
            str(duration),
            "-af",
            f"loudnorm=I=-23:TP=-4:LRA=11,afade=t=in:d=0.45,afade=t=out:st={duration - 2.2}:d=2.2",
            "-ar",
            "48000",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(P / "assets/inspired.mp3"),
        ],
        check=True,
    )
    audio = f'<audio id="music" class="clip" src="assets/inspired.mp3" data-start="0" data-duration="{duration}" data-track-index="2" data-volume="1"></audio>'
    for i, (name, at, volume, length) in enumerate(SOUND_CUES):
        if length is None and name.endswith(".mp3"):
            length = 0.4
        elif length is None:
            with wave.open(str(P / "assets/sounds" / name)) as sound:
                length = sound.getnframes() / sound.getframerate()
        audio += f'<audio id="cue-{i}" class="clip" src="assets/sounds/{name}" data-start="{round(at, 4)}" data-duration="{length}" data-track-index="{3 + i % 6}" data-volume="{volume}"></audio>'
    header = r"""<!doctype html><html lang="en" data-composition-variables='[{"id":"tagline","type":"string","label":"Closing line","default":"Computer control for\nlimited dexterity"},{"id":"repository","type":"string","label":"Repository","default":"github.com/mekdimd/nudge"}]'><head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>Nudge launch film</title><link rel="stylesheet" href="assets/film.css"><script src="assets/vendor/gsap.min.js"></script><script src="assets/motion.js"></script><style>html,body{width:1920px;height:1080px;overflow:hidden}#root{position:relative;width:1920px;height:1080px}</style></head><body>"""
    (P / "index.html").write_text(
        header
        + f'<div id="root" data-composition-id="main" data-start="0" data-duration="{duration}" data-width="1920" data-height="1080" data-fps="60">'
        + hosts
        + audio
        + "</div><script>window.__timelines=window.__timelines||{};window.__timelines.main=gsap.timeline({paused:true});</script></body></html>"
    )
    (P / "audio-cues.json").write_text(json.dumps(SOUND_CUES, indent=2) + "\n")


if __name__ == "__main__":
    main()
