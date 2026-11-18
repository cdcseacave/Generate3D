#!/bin/sh
# Render the frames still missing (skips existing ones), then encode the video when all 2220 are there.
cd /Users/dancostin/Downloads/Generate3D
/Applications/Blender.app/Contents/MacOS/Blender -b out/apartment_scene.blend -P apartment/flythrough.py -- final 950 2220 >> logs/fly_rest.log 2>&1
n=$(ls out/flythrough/frames | grep -c '^f_.*png$')
if [ "$n" -ge 2220 ]; then
  ~/Applications/Ffmpeg/ffmpeg -y -loglevel error -framerate 24 -i out/flythrough/frames/f_%04d.png -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p out/flythrough/apartment_2k.mp4 >> logs/fly_rest.log 2>&1
fi
