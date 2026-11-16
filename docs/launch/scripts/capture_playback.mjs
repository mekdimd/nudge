export function tutorialIsPlaying() {
  const video = document.querySelector("#movie_player video");
  return location.pathname === "/watch" &&
    Boolean(video && video.currentTime > 0 && !video.paused);
}
