"""Build the split-screen launch film from synchronized browser and Qt captures."""

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


def actor(id, human=False):
    return f'<img id="{id}" class="actor{" human" if human else ""}" src="assets/{"human-cursor.svg" if human else "pointer.png"}" alt="" data-layout-ignore>'


def ring(id, miss=False):
    return f'<div id="{id}" class="ring{" miss" if miss else ""}" data-layout-ignore></div>'


def scene(name, duration, body, script, styles=""):
    (P / "compositions" / f"{name}.html").write_text(f'''<template>
<style>#root{{position:absolute;inset:0}}{styles}</style>
<div id="root" class="scene" data-composition-id="{name}" data-width="1920" data-height="1080" data-duration="{duration}">{body}</div>
<script>{{const tl=gsap.timeline({{paused:true}});{script}window.__timelines["{name}"]=tl;}}</script>
</template>
''')


def cue(name, at, volume=0.4):
    SOUND_CUES.append((name, at, volume))


def build_task(case, title, segments, absolute_start, peek=False, video_offsets=None):
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
    if peek:
        screen += '<div id="peek-frame" class="clip" data-start=".2" data-duration="1.35" data-track-index="3"><img class="screen-media" src="assets/browser/youtube-peek.png" alt="Nudge Peek outlines the browser controls"></div>'
        script += 'tl.fromTo("#peek-frame img",{opacity:0},{opacity:1,duration:.16},.2);tl.to("#peek-frame img",{opacity:0,duration:.18},1.35);'
    body = f'<h1 class="headline">{title}</h1><div class="screen"><div id="{case}-stage" class="screen-stage" data-layout-allow-overflow>{screen}</div></div>'
    body += f'<div class="nudge-screen" style="top:{side_top}px;height:{side_height}px"><div id="{case}-nudge-stage" class="nudge-stage" data-layout-allow-overflow>{side}</div></div>'
    if case == "mail":
        # Enlarge the actual subject and approval controls while their decisions hold.
        script += 'tl.to("#mail-nudge-stage",{scale:2.5,x:-20,y:-540,duration:.4,ease:"power2.inOut"},1.5);'
        script += 'tl.to("#mail-nudge-stage",{x:-443,y:-850,duration:.38,ease:"power2.inOut"},4.3);'
        script += 'tl.to("#mail-nudge-stage",{scale:1,x:0,y:0,duration:.35,ease:"power2.inOut"},5.07);'
        script += 'tl.to("#mail-nudge-stage",{scale:2.25,x:-20,y:-460,duration:.4,ease:"power2.inOut"},7.3);'
        script += 'tl.to("#mail-nudge-stage",{scale:1,x:0,y:0,duration:.35,ease:"power2.inOut"},9.25);'
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


def main():
    # The same framing continues across trims; only waiting between decisions is removed.
    bank = json.loads((A / "bank-actions.json").read_text())
    youtube = json.loads((A / "youtube-actions.json").read_text())
    mail = json.loads((A / "mail-actions.json").read_text())
    mt = json.loads((A / "mail-trace.json").read_text())
    clicks = bank["actions"]
    bank_segments = [
        (clicks[0]["at"] - 1.5, 1.95),
        (clicks[1]["at"] - 1.25, 1.7),
        (clicks[2]["at"] - 1.15, 2.35),
    ]
    yt_type = next(a for a in youtube["actions"] if a["operation"] == "type")
    yt_click = next(a for a in youtube["actions"] if a["operation"] == "click")
    scroll = next((a for a in youtube["actions"] if a["operation"] == "scroll"), None)
    yt_segments = [
        (yt_type["at"] - 2.4, 2.85),
        (yt_click["at"] - 1.15, 2.05),
        ((scroll["at"] - 0.15) if scroll else (yt_click["at"] + 1.1), 1.1),
    ]
    offset = mt["epoch_started"] - mail["epochStarted"]
    draft = next(p for p in mt["prompts"] if p["kind"] == "draft")["at"] + offset
    approve = (
        next(
            e
            for e in mt["events"]
            if e["kind"] == "approve" and e["prompt"] == "confirm"
        )["at"]
        + offset
    )
    compose = mail["actions"][0]["at"]
    send = mail["actions"][-1]["at"]
    mail_segments = [
        (compose - 0.65, 1.05),
        (draft - 0.3, 4.1),
        (approve + 0.15 - 4.1, 3.4),
        (send - 0.5, 2.75),
    ]
    cut = {}
    cut["bank"] = build_task(
        "bank", "Download a statement.", bank_segments, 4.8, video_offsets=[1.56] * 3
    )
    cut["youtube"] = build_task(
        "youtube", "Find a how-to.", yt_segments, 10.8, peek=True
    )
    cut["mail"] = build_task(
        "mail",
        "Review an email.",
        mail_segments,
        16.8,
        video_offsets=[1.48, 1.48, 1.52, 1.34],
    )
    (A / "edit-points-v3.json").write_text(json.dumps(cut, indent=2) + "\n")

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
    reveal = (
        (P / "compositions/reveal.html")
        .read_text()
        .replace('data-duration="1.1166666666666667"', 'data-duration="0.8"')
    )
    (P / "compositions/reveal.html").write_text(reveal)
    slots = [
        ("hook", 0, 4),
        ("reveal", 4, 0.8),
        ("bank", 4.8, 6),
        ("youtube", 10.8, 6),
        ("mail", 16.8, 11.3),
        ("outro", 28.1, 3.1),
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
    audio = '<audio id="music" class="clip" src="assets/inspired.mp3" data-start="0" data-duration="31.2" data-track-index="2" data-volume="1"></audio>'
    for i, (name, at, volume) in enumerate(SOUND_CUES):
        if name.endswith(".mp3"):
            duration = 0.4
        else:
            with wave.open(str(P / "assets" / "sounds" / name)) as sound:
                duration = sound.getnframes() / sound.getframerate()
        audio += f'<audio id="cue-{i}" class="clip" src="assets/sounds/{name}" data-start="{round(at, 4)}" data-duration="{duration}" data-track-index="{3 + i % 6}" data-volume="{volume}"></audio>'
    (P / "index.html").write_text(
        """<!doctype html><html lang="en" data-composition-variables='[{"id":"tagline","type":"string","label":"Closing line","default":"Fewer precise clicks."},{"id":"repository","type":"string","label":"Repository","default":"github.com/mekdimd/nudge"}]'><head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>Nudge launch film</title><link rel="stylesheet" href="assets/film.css"><script src="assets/vendor/gsap.min.js"></script><script src="assets/motion.js"></script><style>html,body{width:1920px;height:1080px;overflow:hidden}#root{position:relative;width:1920px;height:1080px}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="31.2" data-width="1920" data-height="1080" data-fps="60">"""
        + hosts
        + audio
        + """</div><script>window.__timelines=window.__timelines||{};window.__timelines.main=gsap.timeline({paused:true});</script></body></html>"""
    )
    (P / "audio-cues.json").write_text(json.dumps(SOUND_CUES, indent=2) + "\n")


if __name__ == "__main__":
    main()
