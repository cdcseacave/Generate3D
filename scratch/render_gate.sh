#!/bin/zsh
# Let the fly-through render use the machine only when nobody else does.
# macOS has no user control over GPU priority, so instead of sharing the GPU the render is
# paused (SIGSTOP) while the Mac is in use and resumed (SIGCONT) once it has been idle:
#   in use = keyboard/mouse touched in the last RENDER_IDLE_SECS seconds (default 120), or
#            other processes using more than RENDER_BUSY_CPU % CPU (default 150 = 1.5 cores).
# Exits by itself when the render ends. Log: logs/render_gate.log
cd /Users/dancostin/Downloads/Generate3D
IDLE=${RENDER_IDLE_SECS:-120}
BUSY=${RENDER_BUSY_CPU:-150}
PAT="apartment/flythrough.py"
state=run
trap 'pkill -CONT -f "$PAT"; exit' INT TERM EXIT
sleep 10                                   # give the render a moment to start
while pgrep -f "$PAT" >/dev/null; do
  idle=$(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}')
  other=$(ps -A -o %cpu=,command= | grep -v -e "$PAT" -e render_gate -e "ps -A" | awk '{s+=$1} END {print int(s)}')
  if (( idle < IDLE || other > BUSY )); then want=stop; else want=run; fi
  if [[ $want != $state ]]; then
    if [[ $want == stop ]]; then pkill -STOP -f "$PAT"; else pkill -CONT -f "$PAT"; fi
    state=$want
    echo "$(date '+%F %T') $want (idle ${idle}s, other cpu ${other}%)" >> logs/render_gate.log
  fi
  sleep 15
done
