// Cursor arcs and click feedback follow a paused, seekable GSAP timeline.
function launchMove(tl, selector, from, to, at, duration) {
  const mid = [
    (from[0] + to[0]) / 2 - (to[1] - from[1]) * 0.045,
    (from[1] + to[1]) / 2 + (to[0] - from[0]) * 0.045,
  ];
  tl.set(
    selector,
    { x: from[0], y: from[1], scale: 1, rotation: 0, opacity: 1 },
    at,
  );
  tl.to(
    selector,
    {
      x: mid[0],
      y: mid[1],
      rotation: 7,
      duration: duration * 0.42,
      ease: "power2.in",
    },
    at,
  );
  tl.to(
    selector,
    {
      x: to[0],
      y: to[1],
      rotation: 0,
      duration: duration * 0.58,
      ease: "power3.out",
    },
    at + duration * 0.42,
  );
  // Adapt the registry's SVG trail to the same path and easing as the pointer.
  const counts = (tl.launchTrailCounts ||= {});
  const index = counts[selector] || 0;
  const trail = selector + "-trail-" + index;
  if (document.querySelector(trail)) {
    counts[selector] = index + 1;
    const first = Math.hypot(mid[0] - from[0], mid[1] - from[1]);
    const total = first + Math.hypot(to[0] - mid[0], to[1] - mid[1]);
    tl.set(
      trail,
      {
        attr: { d: `M${from.join(" ")} L${mid.join(" ")} L${to.join(" ")}` },
        strokeDasharray: total,
        strokeDashoffset: total,
        opacity: 0.4,
      },
      at,
    );
    tl.to(
      trail,
      {
        strokeDashoffset: total - first,
        duration: duration * 0.42,
        ease: "power2.in",
      },
      at,
    );
    tl.to(
      trail,
      { strokeDashoffset: 0, duration: duration * 0.58, ease: "power3.out" },
      at + duration * 0.42,
    );
    tl.to(
      trail,
      { opacity: 0, duration: 0.24, ease: "power2.out" },
      at + duration,
    );
  }
}
function launchClick(tl, selector, ring, point, at) {
  tl.set(ring, { x: point[0], y: point[1], scale: 0.38, opacity: 1 }, at);
  if (ring.startsWith("#miss-")) {
    tl.to(
      ring,
      { scale: 1, opacity: 0.8, duration: 0.22, ease: "power2.out" },
      at,
    );
    tl.to(ring, { opacity: 0, duration: 0.16 }, 2.4);
  } else
    tl.to(
      ring,
      { scale: 1.12, opacity: 0, duration: 0.42, ease: "power2.out" },
      at,
    );
  tl.to(selector, { scale: 0.79, duration: 0.07, ease: "power2.in" }, at);
  tl.to(selector, { scale: 1, duration: 0.16, ease: "back.out(2)" }, at + 0.07);
}

// Ease the camera onto a target and keep it there until released.
function launchFocus(tl, stage, point, at, width, height, scale, duration) {
  scale = scale || 1.3;
  const x = Math.max(
    width * (1 - scale),
    Math.min(0, width / 2 - point[0] * scale),
  );
  const y = Math.max(
    height * (1 - scale),
    Math.min(0, height / 2 - point[1] * scale),
  );
  tl.to(
    stage,
    { scale, x, y, duration: duration || 0.55, ease: "power2.inOut" },
    at,
  );
}
function launchRelease(tl, stage, at, duration) {
  tl.to(
    stage,
    { scale: 1, x: 0, y: 0, duration: duration || 0.5, ease: "power2.inOut" },
    at,
  );
}
// Follow the target during a flight, then return to the complete browser view.
function launchCamera(tl, stage, point, at, width, height, hold) {
  launchFocus(tl, stage, point, at, width, height);
  launchRelease(tl, stage, at + 0.55 + (hold === undefined ? 1.1 : hold));
}
// Pop the green check and the closing line that marks a finished task.
function launchDone(tl, title, at) {
  tl.fromTo(
    title,
    { opacity: 0, y: 26 },
    { opacity: 1, y: 0, duration: 0.35, ease: "power3.out" },
    at,
  );
  tl.fromTo(
    title + " .done-badge",
    { scale: 0.2 },
    { scale: 1, duration: 0.45, ease: "back.out(2.4)" },
    at,
  );
  tl.fromTo(
    title + " path",
    { strokeDashoffset: 60 },
    { strokeDashoffset: 0, duration: 0.35, ease: "power2.out" },
    at + 0.18,
  );
}
