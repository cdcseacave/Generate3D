#!/bin/zsh
# Render the 2K fly-through and encode it. Safe to stop and run again: finished frames are kept.
cd /Users/dancostin/Downloads/Generate3D
/Applications/Blender.app/Contents/MacOS/Blender -b out/apartment_scene.blend -P apartment/flythrough.py -- final >> logs/fly_final.log 2>&1
n=$(ls out/flythrough/frames | wc -l | tr -d ' ')
if [ "$n" -ge 2220 ]; then
  ~/Applications/Ffmpeg/ffmpeg -y -loglevel error -framerate 24 -i out/flythrough/frames/f_%04d.png -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p out/flythrough/apartment_2k.mp4
fi
