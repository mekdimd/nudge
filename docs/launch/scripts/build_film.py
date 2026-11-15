"""Build the launch film from recorded browser actions and Qt decisions."""

from pathlib import Path
import json
import math
import subprocess
import wave

P = Path(__file__).resolve().parents[1]
A = P / "assets" / "browser"
SCREEN_W = 1100
SCREEN_H = 687.5
SCALE = SCREEN_W / 1280
SIDE_W = 594
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
    return f'<img id="{id}" class="{"clip " if timing else ""}actor{" human" if human else ""}" src="assets/{"human-cursor.svg" if human else "pointer.png"}" alt="" data-layout-ignore{timing}>'


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


def build_task(case, title, segments, absolute_start, video_offsets=None):
    data = json.loads((A / f"{case}-actions.json").read_text())
    trace = json.loads((A / f"{case}-trace.json").read_text())
    offset = trace["epoch_started"] - data["epochStarted"]
    max_height = max(
        trace["idle"]["height"],
        trace["done"]["height"],
        *[p["bar"]["height"] for p in trace["prompts"]],
    )
    crop_h = min(1000, math.ceil(max_height * 0.65 / 2) * 2 + 12)
    side_height = crop_h * SIDE_W / 910
    side_top = 170 + (SCREEN_H - side_height) / 2
    screen = ""
    side = ""
    script = ""
    clock = 0
    emitted = []
    for i, (source_start, duration) in enumerate(segments):
        name = f"{case}-{i}"
        video_offset = video_offsets[i] if video_offsets else data["recordingOffset"]
        background = {"bank": "0xf5f7f6", "mail": "0xf5f5fb", "youtube": "white"}[case]
        encode(
            A / f"{case}.webm",
            A / f"{name}-screen.mp4",
            video_offset + source_start,
            duration,
            f"crop=1280:712:0:0,pad=1280:800:0:0:color={background},fps=60",
        )
        encode(
            A / f"{case}-nudge.mp4",
            A / f"{name}-nudge.mp4",
            source_start - offset - trace["ui_frames"][0],
            duration,
            f"crop=910:{crop_h}:0:0,fps=60",
        )
        screen += timed_video(
            name + "-screen", name + "-screen.mp4", clock, duration, "screen-media"
        )
        side += timed_video(
            name + "-nudge", name + "-nudge.mp4", clock, duration, "nudge-media"
        )
        for j, a in enumerate(data["actions"]):
            if (
                case == "mail"
                and a["operation"] == "type"
                and a["label"] != "To recipients"
            ):
                continue
            if (
                source_start <= a["at"] < source_start + duration
                and "center" in a
                and j not in emitted
            ):
                emitted.append(j)
                local = clock + a["at"] - source_start
                point = [round(v * SCALE, 3) for v in a["center"]]
                origin = (
                    [SCREEN_W * 0.62, SCREEN_H * 0.30]
                    if len(emitted) == 1
                    else previous
                )
                before = max(clock + 0.04, local - 0.34)
                script += (
                    f'launchMove(tl,"#{case}-cursor",{origin},{point},{before},.30);'
                )
                script += f'launchClick(tl,"#{case}-cursor","#{case}-ring-{j}",{point},{local});'
                script += f'launchCamera(tl,"#{case}-stage",{point},{before},{SCREEN_W},{SCREEN_H});'
                screen += ring(f"{case}-ring-{j}")
                if a["operation"] == "click":
                    cue("click-soft.mp3", absolute_start + local, 0.65)
                cue("tick.wav", absolute_start + local + 0.32, 0.38)
                previous = point
        for event in trace["events"]:
            if event["kind"] == "approve":
                host_at = offset + event["at"]
                if source_start <= host_at < source_start + duration:
                    local = clock + host_at - source_start
                    point = [round(v * SIDE_W / 700, 3) for v in event["center"]]
                    script += f'launchMove(tl,"#{case}-human",[520,{point[1] - 90}],{point},{max(clock + 0.02, local - 0.32)},.28);'
                    script += f'launchClick(tl,"#{case}-human","#{case}-approval-ring-{i}",{point},{local});'
                    script += f'tl.to("#{case}-human",{{opacity:0,duration:.15}},{local + 0.3});'
                    side += ring(f"{case}-approval-ring-{i}")
                    cue("click-soft.mp3", absolute_start + local, 0.65)
        clock += duration
    screen += actor(case + "-cursor")
    side += actor(case + "-human", True)
    done = A / f"{case}-side-done.png"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(A / f"{case}-done.png"),
            "-vf",
            f"scale=910:-1,pad=910:{crop_h}:0:0:color=0x20252c",
            "-frames:v",
            "1",
            str(done),
        ],
        check=True,
    )
    side += f'<div id="{case}-done-hold" class="clip" data-start="{clock - 0.55}" data-duration=".55" data-track-index="3" data-beat="{case}-finished"><img class="nudge-media" src="assets/browser/{done.name}" alt="Nudge completed the task"></div>'
    body = f'<h1 class="headline">{title}</h1><div class="screen"><div id="{case}-stage" class="screen-stage" data-layout-allow-overflow>{screen}</div></div>'
    body += f'<div class="nudge-screen" style="top:{side_top}px;height:{side_height}px"><div id="{case}-nudge-stage" class="nudge-stage" data-layout-allow-overflow>{side}</div></div>'
    script += 'tl.set(".headline",{opacity:1});'
    cue("start.wav", absolute_start + 0.08, 0.38)
    cue("success.wav", absolute_start + clock - 0.5, 0.42)
    scene(case, clock, body, script)
    return {
        "segments": segments,
        "video_offsets": video_offsets or [data["recordingOffset"]] * len(segments),
        "duration": clock,
        "side_top": side_top,
        "side_height": side_height,
    }


def browser_clip(name, source_start, duration, stretch=1):
    encode(
        A / "mail.webm",
        A / f"{name}.mp4",
        source_start,
        duration,
        f"crop=1280:712:0:0,pad=1280:800:0:0:color=0xf5f5fb,setpts=(PTS-STARTPTS)*{stretch},fps=60",
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
    draft_source = draft["at"] - first + 0.59
    draft_stretch = 1
    panel_clip("mail-review", draft, draft_source, 4.0, draft_stretch, hold=0.4)
    encode(
        A / "mail-nudge.mp4",
        A / "mail-writing.mp4",
        3.45,
        0.8,
        "crop=910:350:0:0,fps=60",
    )
    confirm_source = approvals["confirm"]["at"] - first - 1.24
    panel_clip("mail-approval", confirm, confirm_source, 1.55, hold=0.4)
    browser_clip("mail-compose", 2.68, 1.2)
    # Page changes, rather than the browser recorder's wall-clock offset, locate typing.
    browser_clip("mail-fill", 7.60, 4.8, 1.32)
    browser_clip("mail-send", 12.78, 2.05)
    body = '<h1 class="headline">Draft. Edit. Send.</h1>'
    script = ""
    phases = [
        ("compose", 0, 1.2, "browser"),
        ("writing", 1.0, 0.8, "writing"),
        ("review", 1.6, 4.0, "draft"),
        ("fill", 5.4, 4.8, "browser"),
        ("approval", 10.0, 1.55, "confirm"),
        ("send", 11.35, 2.95, "browser"),
    ]
    for name, start, duration, kind in phases:
        ident = f"mail-{name}"
        cls = "focus-browser" if kind == "browser" else f"focus-nudge {kind}"
        content = ""
        if kind == "browser":
            media_duration = 2.05 if name == "send" else duration
            content += timed_video(
                ident + "-video", ident + ".mp4", start, media_duration, "focus-media"
            )
            if name == "send":
                content += f'<div id="mail-result-hold" class="clip" data-start="{round(start + media_duration, 3)}" data-duration="{round(duration - media_duration, 3)}" data-track-index="2" data-hold><img class="focus-media" src="assets/browser/mail-page-done.png" alt="Edited email sent to Professor Lee"></div>'
        elif kind == "writing":
            content += timed_video(
                ident + "-video", ident + ".mp4", start, duration, "focus-media"
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
            script += f'tl.fromTo("#{ident}-window .focus-window",{{x:{-180 if kind == "browser" else 180},opacity:0}},{{x:0,opacity:1,duration:.2,ease:"power2.out"}},{start});'
        else:
            script += f'tl.set("#{ident}-window .focus-window",{{opacity:1}},0);'
        if name != "send":
            script += f'tl.to("#{ident}-window .focus-window",{{x:{180 if kind == "browser" else -180},opacity:0,duration:.2,ease:"power2.in"}},{start + duration - 0.2});'
    scale = 1424 / 1280
    compose_point = [110.5 * scale, 138 * scale]
    script += f'launchMove(tl,"#mail-compose-cursor",[600,250],{compose_point},.04,.28);launchClick(tl,"#mail-compose-cursor","#mail-compose-ring",{compose_point},.36);tl.to("#mail-compose-cursor",{{opacity:0,duration:.1}},.8);'
    cue("start.wav", absolute_start + 0.05, 0.38)
    cue("click-soft.mp3", absolute_start + 0.36, 0.65)

    def draft_time(at):
        return 1.6 + (at - first - draft_source) * draft_stretch

    def panel_point(prompt, point):
        x, y, w, _ = prompt["panel_rect"]
        return [
            round((point[0] * 2 - x) * 1320 / w, 3),
            round(90 + (point[1] * 2 - y) * 1320 / w, 3),
        ]

    selection = events["edit-select"]
    left, right = [panel_point(draft, selection[p]) for p in ["start", "end"]]
    select_at = draft_time(selection["at"])
    script += f'launchMove(tl,"#mail-review-cursor",[740,245],{left},{select_at - 0.35},.28);tl.to("#mail-review-cursor",{{x:{right[0]},y:{right[1]},duration:.2,ease:"power1.inOut"}},{select_at - 0.20});'
    typed_at = draft_time(events["edit-typing"]["at"])
    typed_end = draft_time(events["edit-subject"]["at"])
    cue("typing.mp3", absolute_start + typed_at, 0.42, typed_end - typed_at)
    approval = panel_point(draft, approvals["draft"]["center"])
    approve_at = draft_time(approvals["draft"]["at"])
    script += f'launchMove(tl,"#mail-review-cursor",{right},{approval},{approve_at - 0.32},.28);launchClick(tl,"#mail-review-cursor","#mail-review-ring",{approval},{approve_at});tl.to("#mail-review-cursor",{{opacity:0,duration:.07}},{approve_at + 0.07});'
    cue("click-soft.mp3", absolute_start + approve_at, 0.65)
    # These field starts were checked in decoded browser frames at 25 fps.
    previous = [850, 210]
    for j, (source_at, source_end, point) in enumerate(
        [
            (7.92, 8.20, [743.5, 272]),
            (8.24, 8.88, [743.5, 337]),
            (8.96, 10.40, [701, 487.5]),
        ]
    ):
        at = 5.4 + (source_at - 7.6) * 1.32
        target = [round(v * scale, 3) for v in point]
        script += (
            f'launchMove(tl,"#mail-fill-cursor",{previous},{target},{at - 0.25},.25);'
        )
        script += f'launchCamera(tl,"#mail-fill-stage",{target},{at - 0.25},1424,890);'
        cue("typing.mp3", absolute_start + at, 0.30, (source_end - source_at) * 1.32)
        previous = target
    script += 'tl.to("#mail-fill-cursor",{opacity:0,duration:.1},9.3);'
    send_approval = panel_point(confirm, approvals["confirm"]["center"])
    yes_at = 10.0 + approvals["confirm"]["at"] - first - confirm_source
    # Keep the source panel before it closes; the visible approval marks its actual action.
    yes_at = min(yes_at, 11.24)
    script += f'launchMove(tl,"#mail-approval-cursor",[1030,190],{send_approval},{yes_at - 0.32},.28);launchClick(tl,"#mail-approval-cursor","#mail-approval-ring",{send_approval},{yes_at});tl.to("#mail-approval-cursor",{{opacity:0,duration:.07}},{yes_at + 0.07});'
    cue("attention.wav", absolute_start + 10.2, 0.3)
    cue("click-soft.mp3", absolute_start + yes_at, 0.65)
    send_point = [340.5625 * scale, 646 * scale]
    script += f'launchMove(tl,"#mail-send-cursor",[780,535],{send_point},11.58,.3);launchCamera(tl,"#mail-send-stage",{send_point},11.58,1424,890);launchClick(tl,"#mail-send-cursor","#mail-send-ring",{send_point},11.89);tl.to("#mail-send-cursor",{{opacity:0,duration:.1}},12.3);'
    cue("click-soft.mp3", absolute_start + 11.89, 0.65)
    cue("success.wav", absolute_start + 12.12, 0.42)
    styles = ".focus-window{position:absolute;overflow:hidden;border-radius:14px;border:1px solid #d4dce4}.focus-browser{left:248px;top:160px;width:1424px;height:890px;background:#f5f5fb}.focus-nudge{left:300px;top:154px;width:1320px;background:#10151d;border:1px solid #333943}.focus-nudge.draft{height:880px}.focus-nudge.confirm{top:385px;height:326px}.focus-nudge.writing{top:290px;height:508px}.focus-stage{position:absolute;inset:0;transform-origin:0 0}.focus-media{position:absolute;inset:0;width:100%;height:100%;object-fit:fill}.focus-header{position:absolute;inset:auto;left:0;top:0;width:1320px;height:90px;object-fit:fill}.focus-panel{position:absolute;inset:auto;left:0;top:90px;width:1320px;height:790px;object-fit:fill}.confirm .focus-panel{height:236px}"
    scene("mail", 14.3, body, script, styles)
    return {
        "duration": 14.3,
        "phases": phases,
        "draft_source": draft_source,
        "draft_stretch": draft_stretch,
        "fill_source": [7.6, 4.8, 1.32],
        "field_starts": [7.92, 8.24, 8.96],
        "send_source": 12.78,
    }


def build_jev(absolute_start):
    trace = json.loads((A / "jev-trace.json").read_text())
    encode(
        A / "jev-nudge.mp4", A / "jev-feed.mp4", 0.65, 3.8, "crop=910:304:0:0,fps=60"
    )
    encode(
        A / "jev.webm",
        A / "jev-result.mp4",
        6.08,
        1.14,
        "crop=1280:712:0:0,pad=1280:800:0:0:color=white,fps=60",
    )
    body = '<h1 class="headline">Meet Jev, Nudge&apos;s action model.</h1><div class="screen"><div id="jev-stage" class="screen-stage" data-layout-allow-overflow><img class="screen-media" src="assets/browser/jev-page-idle.png" alt="VS Code issue list on GitHub">'
    for name, at, duration in [("peek", 0.25, 1.9), ("choice", 1.4, 1.26)]:
        body += f'<div id="jev-{name}" class="clip" data-start="{at}" data-duration="{duration}" data-track-index="3" data-beat="jev-{name}"><img class="screen-media" src="assets/browser/jev-{name}.png" alt="Actual Peek outlines over available controls"></div>'
    body += '<div id="jev-selected-control" class="clip" data-start="1.4" data-duration="1.26" data-track-index="4"><div class="selected-control" data-layout-ignore></div></div>'
    body += timed_video("jev-result", "jev-result.mp4", 2.66, 1.14, "screen-media")
    body += actor("jev-cursor") + ring("jev-ring") + "</div></div>"
    body += (
        '<div class="nudge-screen" style="top:390px;height:198.4px"><div class="nudge-stage">'
        + timed_video("jev-feed", "jev-feed.mp4", 0, 3.8, "nudge-media")
        + "</div></div>"
    )
    body += '<div id="jev-decision" class="clip" data-start="1.4" data-duration="2.4" data-track-index="5" data-beat="jev-decision"><p class="decision-caption">Jev chooses Labels.</p></div>'
    point = [127.5 * SCALE, 497 * SCALE]
    script = 'tl.fromTo("#jev-peek img",{clipPath:"inset(0 100% 0 0)"},{clipPath:"inset(0 0% 0 0)",duration:.75,ease:"power2.inOut"},.25);tl.fromTo("#jev-choice img",{opacity:0},{opacity:1,duration:.18},1.4);'
    script += f'launchMove(tl,"#jev-cursor",[780,300],{point},2.17,.30);launchCamera(tl,"#jev-stage",{point},2.17,1100,687.5);launchClick(tl,"#jev-cursor","#jev-ring",{point},2.54);tl.to("#jev-cursor",{{opacity:0,duration:.12}},3.05);'
    cue("start.wav", absolute_start + 0.10, 0.38)
    cue("tick.wav", absolute_start + 1.4, 0.36)
    cue("click-soft.mp3", absolute_start + 2.54, 0.65)
    cue("success.wav", absolute_start + 3.22, 0.4)
    script += 'tl.fromTo("#jev-decision p",{opacity:0,y:12},{opacity:1,y:0,duration:.18,ease:"power2.out"},1.4);tl.fromTo("#jev-selected-control div",{opacity:0},{opacity:1,duration:.18},1.4);'
    styles = ".decision-caption{position:absolute;left:1230px;top:620px;font-size:64px;line-height:1.08;font-weight:550;letter-spacing:-1.6px;color:var(--ink);width:594px}.selected-control{position:absolute;left:27.5px;top:413.36px;width:164.14px;height:27.5px;border:5px solid #3576ec;border-radius:5px;background:#4f8ef71a}"
    scene("jev", 3.8, body, script, styles)
    return {
        "duration": 3.8,
        "source": "https://github.com/microsoft/vscode/issues",
        "peek_controls": next(
            e["count"] for e in trace["events"] if e["kind"] == "peek"
        ),
    }


def main():
    bank = json.loads((A / "bank-actions.json").read_text())
    youtube = json.loads((A / "youtube-actions.json").read_text())
    clicks = bank["actions"]
    bank_segments = [
        (clicks[0]["at"] - 0.85, 1.2),
        (clicks[1]["at"] - 0.75, 1.2),
        (clicks[2]["at"] - 0.85, 2.2),
    ]
    yt_type = next(a for a in youtube["actions"] if a["operation"] == "type")
    yt_click = next(a for a in youtube["actions"] if a["operation"] == "click")
    scroll = next(a for a in youtube["actions"] if a["operation"] == "scroll")
    yt_segments = [
        (yt_type["at"] - 0.35, 1.85),
        (yt_click["at"] - 0.40, 1.45),
        (scroll["at"] - 0.12, 0.9),
    ]
    cut = {}
    cut["bank"] = build_task(
        "bank", "Download a statement.", bank_segments, 5.4, video_offsets=[1.56] * 3
    )
    cut["youtube"] = build_task(
        "youtube",
        "Find a how-to.",
        yt_segments,
        10.0,
        video_offsets=[2.09, 1.95, 2.09],
    )
    cut["jev"] = build_jev(14.2)
    cut["mail"] = build_mail(18.0)
    (A / "edit-points-v4.json").write_text(json.dumps(cut, indent=2) + "\n")

    misses = [(206, 258), (1220, 340), (770, 214)]
    h = (
        '<div class="hook-screen"><div id="hook-stage" data-layout-allow-overflow><img class="hook-media" src="assets/browser/bank-page-idle.png" alt="Bank website">'
        + actor("hook-cursor", True)
        + "".join(ring("miss-" + str(i), True) for i in range(3))
        + '</div></div><div id="hook-copy"><h1>Hard to click?</h1></div>'
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
    script += 'tl.to("#hook-stage",{opacity:.2,duration:.28},2.42);tl.to("#hook-copy",{opacity:1,duration:.34,ease:"power2.out"},2.5);'
    scene("hook", 4, h, script)
    cue("attention.wav", 2.48, 0.3)

    # Keep the approved pointer reveal and closing card.
    import re

    reveal = re.sub(
        r'data-duration="[0-9.]+"',
        'data-duration="1.4"',
        (P / "compositions/reveal.html").read_text(),
    )
    (P / "compositions/reveal.html").write_text(reveal)
    slots = [
        ("hook", 0, 4),
        ("reveal", 4, 1.4),
        ("bank", 5.4, 4.6),
        ("youtube", 10.0, 4.2),
        ("jev", 14.2, 3.8),
        ("mail", 18.0, 14.3),
        ("outro", 32.3, 3.1),
    ]
    hosts = "".join(
        f'<div id="{name}" class="clip" data-composition-id="{name}" data-composition-src="compositions/{"search" if name == "youtube" else name}.html" data-start="{start}" data-duration="{duration}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>'
        for name, start, duration in slots
    )
    # The search filename stays stable for the editor.
    (P / "compositions/search.html").write_text(
        (P / "compositions/youtube.html").read_text()
    )
    (P / "compositions/youtube.html").unlink()
    audio = '<audio id="music" class="clip" src="assets/inspired.mp3" data-start="0" data-duration="35.4" data-track-index="2" data-volume="1"></audio>'
    for i, (name, at, volume, duration) in enumerate(SOUND_CUES):
        if duration is None and name.endswith(".mp3"):
            duration = 0.4
        elif duration is None:
            with wave.open(str(P / "assets" / "sounds" / name)) as sound:
                duration = sound.getnframes() / sound.getframerate()
        audio += f'<audio id="cue-{i}" class="clip" src="assets/sounds/{name}" data-start="{round(at, 4)}" data-duration="{duration}" data-track-index="{3 + i % 6}" data-volume="{volume}"></audio>'
    (P / "index.html").write_text(
        """<!doctype html><html lang="en" data-composition-variables='[{"id":"tagline","type":"string","label":"Closing line","default":"Fewer precise clicks."},{"id":"repository","type":"string","label":"Repository","default":"github.com/mekdimd/nudge"}]'><head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>Nudge launch film</title><link rel="stylesheet" href="assets/film.css"><script src="assets/vendor/gsap.min.js"></script><script src="assets/motion.js"></script><style>html,body{width:1920px;height:1080px;overflow:hidden}#root{position:relative;width:1920px;height:1080px}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="35.4" data-width="1920" data-height="1080" data-fps="60">"""
        + hosts
        + audio
        + """</div><script>window.__timelines=window.__timelines||{};window.__timelines.main=gsap.timeline({paused:true});</script></body></html>"""
    )
    (P / "audio-cues.json").write_text(json.dumps(SOUND_CUES, indent=2) + "\n")


if __name__ == "__main__":
    main()
