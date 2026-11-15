#!/bin/zsh
cd /Users/dancostin/Downloads/Generate3D
for v in living_room_01 living_room_02 kitchen_01 hallway_01 hallway_02 bedroom_01 bedroom_02 office_01 bathroom_01; do
  echo "{\"view\": \"$v\"}" > scratch/final.json
  ./tools/bx exec scratch/final.py 2>&1 | grep -E '"secs"|status|Error|error' | tr '\n' ' '
  echo " <- $v"
done
