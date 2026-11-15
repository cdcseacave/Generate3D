#!/bin/zsh
cd /Users/dancostin/Downloads/Generate3D
for v in kitchen_01 kitchen_02 bathroom_01 bathroom_02 hallway_02; do
  echo "{\"view\": \"$v\"}" > scratch/final.json
  ./tools/bx exec scratch/final.py 2>&1 | grep -E '"secs"|status|Error|error' | tr '\n' ' '
  echo " <- $v"
done
./tools/bx code 'import sys
sys.path.insert(0, "/Users/dancostin/Downloads/Generate3D")
import apartment.build as B
result = {"refinished": len(B.refinish())}' 2>&1 | grep -E "refinished|status|rror" | tr '\n' ' '
