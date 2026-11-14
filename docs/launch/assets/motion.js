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
}
function launchClick(tl, selector, ring, point, at) {
  tl.set(ring, { x: point[0], y: point[1], scale: 0.38, opacity: 1 }, at);
  if (ring.startsWith("#miss-")) {
    tl.to(
      ring,
      { scale: 1, opacity: 0.8, duration: 0.22, ease: "power2.out" },
      at,
    );
    tl.to(ring, { opacity: 0, duration: 0.16 }, 3.1);
  } else
    tl.to(
      ring,
      { scale: 1.12, opacity: 0, duration: 0.42, ease: "power2.out" },
      at,
    );
  tl.to(selector, { scale: 0.79, duration: 0.07, ease: "power2.in" }, at);
  tl.to(selector, { scale: 1, duration: 0.16, ease: "back.out(2)" }, at + 0.07);
}
