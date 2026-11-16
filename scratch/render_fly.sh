#!/bin/zsh
# Render the 2K fly-through and encode it, at the lowest priority the system offers.
# Safe to stop and run again: finished frames are kept.
#   nice 20                 : CPU yields to everything else (not background QoS: macOS then starves its GPU work)
#   render_gate.py          : pauses the render only while other programs load the GPU
cd /Users/dancostin/Downloads/Generate3D
renice -n 20 -p $$ >/dev/null
nice -n 20 python3 -I scratch/render_gate.py &
nice -n 20 /Applications/Blender.app/Contents/MacOS/Blender -b out/apartment_scene.blend -P apartment/flythrough.py -- final >> logs/fly_final.log 2>&1
n=$(ls out/flythrough/frames | wc -l | tr -d ' ')
if [ "$n" -ge 2220 ]; then
  taskpolicy -b nice -n 20 ~/Applications/Ffmpeg/ffmpeg -y -loglevel error -framerate 24 -i out/flythrough/frames/f_%04d.png -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p out/flythrough/apartment_2k.mp4
fi
