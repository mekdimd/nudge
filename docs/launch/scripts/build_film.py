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
                elif a["operation"] == "type":
                    cue(
                        "typing.mp3",
                        absolute_start + local,
                        0.30,
                        a["endedAt"] - a["at"],
                    )
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
    browser_clip("mail-compose", 5.12, 2.0)
    # Page changes, rather than the browser recorder's wall-clock offset, locate typing.
    browser_clip("mail-fill", 15.78, 6.2, 1.32)
    browser_clip("mail-send", 22.50, 2.8)
    body = '<h1 id="mail-headline" class="headline">Draft. Edit. Send.</h1><div id="mail-input-caption" class="clip" data-start="10.5" data-duration="6.0" data-track-index="5" data-beat="mail-input"><p class="headline" data-hold>Nudge types it for you.</p></div>'
    script = ""
    phases = [
        ("compose", 0, 2.0, "browser"),
        ("writing", 1.8, 3.9, "writing"),
        ("review", 5.5, 5.2, "draft"),
        ("fill", 10.5, 6.2, "browser"),
        ("approval", 16.5, 2.4, "confirm"),
        ("send", 18.7, 3.9, "browser"),
    ]
    for name, start, duration, kind in phases:
        ident = f"mail-{name}"
        cls = "focus-browser" if kind == "browser" else f"focus-nudge {kind}"
        content = ""
        if kind == "browser":
            media_duration = 2.8 if name == "send" else duration
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
    script += 'tl.set("#mail-headline",{opacity:0},10.5);tl.set("#mail-headline",{opacity:1},16.5);tl.fromTo("#mail-input-caption p",{opacity:0,y:12},{opacity:1,y:0,duration:.2,ease:"power2.out"},10.5);'

    def draft_time(at):
        return 5.5 + (at - first - draft_source) * draft_stretch

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
    approve_at = 10.30
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
        at = 10.5 + (source_at - 15.78) * 1.32
        target = [round(v * scale, 3) for v in point]
        script += (
            f'launchMove(tl,"#mail-fill-cursor",{previous},{target},{at - 0.25},.25);'
        )
        script += f'launchCamera(tl,"#mail-fill-stage",{target},{at - 0.25},1424,890);'
        cue("typing.mp3", absolute_start + at, 0.30, (source_end - source_at) * 1.32)
        previous = target
    script += 'tl.to("#mail-fill-cursor",{opacity:0,duration:.1},15.8);'
    send_approval = panel_point(confirm, approvals["confirm"]["center"])
    # Keep the source panel before it closes; the visible approval marks its actual action.
    yes_at = 18.55
    script += f'launchMove(tl,"#mail-approval-cursor",[1030,190],{send_approval},{yes_at - 0.32},.28);launchClick(tl,"#mail-approval-cursor","#mail-approval-ring",{send_approval},{yes_at});tl.to("#mail-approval-cursor",{{opacity:0,duration:.07}},{yes_at + 0.07});'
    cue("attention.wav", absolute_start + 16.7, 0.3)
    cue("click-soft.mp3", absolute_start + yes_at, 0.65)
    send_point = [340.5625 * scale, 646 * scale]
    script += f'launchMove(tl,"#mail-send-cursor",[780,535],{send_point},18.93,.3);launchCamera(tl,"#mail-send-stage",{send_point},18.93,1424,890);launchClick(tl,"#mail-send-cursor","#mail-send-ring",{send_point},19.24);tl.to("#mail-send-cursor",{{opacity:0,duration:.1}},19.65);'
    cue("click-soft.mp3", absolute_start + 19.24, 0.65)
    cue("success.wav", absolute_start + 19.47, 0.42)
    styles = ".focus-window{position:absolute;overflow:hidden;border-radius:14px;border:1px solid #d4dce4}.focus-browser{left:248px;top:160px;width:1424px;height:890px;background:#f5f5fb}.focus-nudge{left:300px;top:154px;width:1320px;background:#10151d;border:1px solid #333943}.focus-nudge.draft{height:880px}.focus-nudge.confirm{top:385px;height:326px}.focus-nudge.writing{top:290px;height:508px}.focus-stage{position:absolute;inset:0;transform-origin:0 0}.focus-media{position:absolute;inset:0;width:100%;height:100%;object-fit:fill}.focus-header{position:absolute;inset:auto;left:0;top:0;width:1320px;height:90px;object-fit:fill}.focus-panel{position:absolute;inset:auto;left:0;top:90px;width:1320px;height:790px;object-fit:fill}.confirm .focus-panel{height:236px}"
    scene("mail", 22.6, body, script, styles)
    return {
        "duration": 22.6,
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
    trace = json.loads((A / "jev-trace.json").read_text())
    encode(
        A / "jev-nudge.mp4",
        A / "jev-feed.mp4",
        0.65,
        5.6,
        "crop=910:304:0:0,trim=duration=3.8,tpad=stop_mode=clone:stop_duration=1.8,fps=60",
    )
    encode(
        A / "jev.webm",
        A / "jev-result.mp4",
        6.08,
        1.84,
        "crop=1280:712:0:0,pad=1280:800:0:0:color=white,fps=60",
    )
    body = '<h1 class="headline">Meet Jev, Nudge&apos;s action model.</h1><div class="screen"><div id="jev-stage" class="screen-stage" data-layout-allow-overflow><img class="screen-media" src="assets/browser/jev-page-idle.png" alt="VS Code issue list on GitHub">'
    for name, at, duration in [("peek", 0.4, 2.9), ("choice", 2.0, 1.76)]:
        body += f'<div id="jev-{name}" class="clip" data-start="{at}" data-duration="{duration}" data-track-index="3" data-beat="jev-{name}"><img class="screen-media" src="assets/browser/jev-{name}.png" alt="Actual Peek outlines over available controls"></div>'
    body += '<div id="jev-selected-control" class="clip" data-start="2.0" data-duration="1.76" data-track-index="4"><div class="selected-control" data-layout-ignore></div></div>'
    body += timed_video("jev-result", "jev-result.mp4", 3.76, 1.84, "screen-media")
    body += actor("jev-cursor") + ring("jev-ring") + "</div></div>"
    body += (
        '<div class="nudge-screen" style="top:390px;height:198.4px"><div class="nudge-stage">'
        + timed_video("jev-feed", "jev-feed.mp4", 0, 5.6, "nudge-media")
        + "</div></div>"
    )
    body += '<div id="jev-decision" class="clip" data-start="2.0" data-duration="3.6" data-track-index="5" data-beat="jev-decision"><p class="decision-caption" data-hold>Jev chooses Labels.</p></div>'
    point = [127.5 * SCALE, 497 * SCALE]
    script = 'tl.fromTo("#jev-peek img",{clipPath:"inset(0 100% 0 0)"},{clipPath:"inset(0 0% 0 0)",duration:.75,ease:"power2.inOut"},.4);tl.fromTo("#jev-choice img",{opacity:0},{opacity:1,duration:.18},2.0);'
    script += f'launchMove(tl,"#jev-cursor",[780,300],{point},3.27,.30);launchCamera(tl,"#jev-stage",{point},3.27,1100,687.5);launchClick(tl,"#jev-cursor","#jev-ring",{point},3.64);tl.to("#jev-cursor",{{opacity:0,duration:.12}},4.15);'
    cue("start.wav", absolute_start + 0.10, 0.38)
    cue("tick.wav", absolute_start + 2.0, 0.36)
    cue("click-soft.mp3", absolute_start + 3.64, 0.65)
    cue("success.wav", absolute_start + 4.32, 0.4)
    script += 'tl.fromTo("#jev-decision p",{opacity:0,y:12},{opacity:1,y:0,duration:.18,ease:"power2.out"},2.0);tl.fromTo("#jev-selected-control div",{opacity:0},{opacity:1,duration:.18},2.0);'
    styles = ".decision-caption{position:absolute;left:1230px;top:620px;font-size:64px;line-height:1.08;font-weight:550;letter-spacing:-1.6px;color:var(--ink);width:594px}.selected-control{position:absolute;left:27.5px;top:413.36px;width:164.14px;height:27.5px;border:5px solid #3576ec;border-radius:5px;background:#4f8ef71a}"
    scene("jev", 5.6, body, script, styles)
    return {
        "duration": 5.6,
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
        (clicks[0]["at"] - 0.85, 1.8),
        (clicks[1]["at"] - 0.75, 1.8),
        (clicks[2]["at"] - 0.85, 3.0),
    ]
    yt_type = next(a for a in youtube["actions"] if a["operation"] == "type")
    yt_click = next(a for a in youtube["actions"] if a["operation"] == "click")
    yt_segments = [
        (yt_type["at"] - 0.55, 3.55),
        (yt_click["at"] - 0.70, 4.15),
    ]
    cut = {}
    cut["bank"] = build_task(
        "bank", "Download a statement.", bank_segments, 6.2, video_offsets=[1.56] * 3
    )
    cut["youtube"] = build_task(
        "youtube",
        "Find an Excel tutorial.",
        yt_segments,
        12.8,
        video_offsets=[2.54, 2.7],
    )
    cut["jev"] = build_jev(20.5)
    cut["mail"] = build_mail(26.1)
    (A / "edit-points-v5.json").write_text(json.dumps(cut, indent=2) + "\n")

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
        'data-duration="2.2"',
        (P / "compositions/reveal.html").read_text(),
    )
    (P / "compositions/reveal.html").write_text(reveal)
    slots = [
        ("hook", 0, 4),
        ("reveal", 4, 2.2),
        ("bank", 6.2, 6.6),
        ("youtube", 12.8, 7.7),
        ("jev", 20.5, 5.6),
        ("mail", 26.1, 22.6),
        ("outro", 48.7, 4.2),
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
    audio = '<audio id="music" class="clip" src="assets/inspired.mp3" data-start="0" data-duration="52.9" data-track-index="2" data-volume="1"></audio>'
    for i, (name, at, volume, duration) in enumerate(SOUND_CUES):
        if duration is None and name.endswith(".mp3"):
            duration = 0.4
        elif duration is None:
            with wave.open(str(P / "assets" / "sounds" / name)) as sound:
                duration = sound.getnframes() / sound.getframerate()
        audio += f'<audio id="cue-{i}" class="clip" src="assets/sounds/{name}" data-start="{round(at, 4)}" data-duration="{duration}" data-track-index="{3 + i % 6}" data-volume="{volume}"></audio>'
    (P / "index.html").write_text(
        """<!doctype html><html lang="en" data-composition-variables='[{"id":"tagline","type":"string","label":"Closing line","default":"Assisted computer control."},{"id":"repository","type":"string","label":"Repository","default":"github.com/mekdimd/nudge"}]'><head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>Nudge launch film</title><link rel="stylesheet" href="assets/film.css"><script src="assets/vendor/gsap.min.js"></script><script src="assets/motion.js"></script><style>html,body{width:1920px;height:1080px;overflow:hidden}#root{position:relative;width:1920px;height:1080px}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="52.9" data-width="1920" data-height="1080" data-fps="60">"""
        + hosts
        + audio
        + """</div><script>window.__timelines=window.__timelines||{};window.__timelines.main=gsap.timeline({paused:true});</script></body></html>"""
    )
    (P / "audio-cues.json").write_text(json.dumps(SOUND_CUES, indent=2) + "\n")


if __name__ == "__main__":
    main()
