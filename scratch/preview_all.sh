#!/bin/zsh
cd /Users/dancostin/Downloads/Generate3D
for pair in "living_room_01 living_room_02" "kitchen_01 kitchen_02" "hallway_01 hallway_02" "bedroom_01 bedroom_02" "office_01 office_02" "bathroom_01 bathroom_02"; do
  a=${pair% *}; b=${pair#* }
  echo "{\"build\": false, \"shots\": [\"$a\", \"$b\"], \"quality\": \"preview\"}" > scratch/run.json
  ./tools/bx exec scratch/run.py 2>&1 | grep -E '"secs"|status|Error|error' | tr '\n' ' '
  echo " <- $pair"
done
