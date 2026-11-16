#!/bin/zsh
# Render every final still; a view whose call outlives the bridge timeout is tried once more
# (the metering it already did is cached, so the second call is shorter).
cd /Users/dancostin/Downloads/Generate3D
for v in living_room_01 living_room_02 kitchen_01 kitchen_02 hallway_01 hallway_02 hallway_03 bedroom_01 bedroom_02 bedroom_03 office_01 bathroom_01 bathroom_02; do
  for try in 1 2; do
    echo "{\"view\": \"$v\"}" > scratch/final.json
    out=$(./tools/bx exec scratch/final.py 2>&1 | grep -E '"secs"|status|Error|error' | tr '\n' ' ')
    echo "$out <- $v (try $try)"
    [[ "$out" == *"status: ok"* ]] && break
    sleep 240
  done
done
