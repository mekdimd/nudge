"""Create the static README poster from the delivery MP4."""
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parents[2] / 'assets'

if __name__ == '__main__':
    video = OUT / 'nudge-launch.mp4'
    if not video.is_file():
        raise SystemExit('Render the launch MP4 first.')
    subprocess.run(['ffmpeg','-y','-v','error','-ss','10.1','-i',str(video),
                    '-frames:v','1','-update','1',str(OUT/'nudge-launch-poster.png')],check=True)
    print('Created the static launch poster.')
