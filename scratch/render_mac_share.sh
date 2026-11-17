#!/bin/zsh
# Render fly-through frames on this Mac from the top down while Windows renders from 950 up
# (see claim_frame.py), at normal priority. Stop with: pkill -f render_mac_share.sh; pkill -f apartment/flythrough.py
# then run: python3 -I scratch/claim_frame.py release
cd /Users/dancostin/Downloads/Generate3D
trap 'python3 -I scratch/claim_frame.py release' EXIT
FLY_CLAIM="python3 -I scratch/claim_frame.py" /Applications/Blender.app/Contents/MacOS/Blender \
  -b out/apartment_scene.blend -P apartment/flythrough.py -- final >> logs/fly_share.log 2>&1
