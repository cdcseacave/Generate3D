"""Pause the fly-through render only while other programs make heavy use of the GPU.

macOS has no user control over GPU priority, so the render (already at nice 20 and background
QoS for CPU and disk) is paused with SIGSTOP when other programs need the GPU, and resumed with
SIGCONT when they are done. GPU use per program comes from the accumulatedGPUTime counters the
Apple GPU driver publishes in the I/O registry (no admin rights needed); Blender's own share is
left out, so the everyday background use of the window server and menu bar does not count.

    pause   when the other programs together used more than RENDER_GPU_PAUSE % of the GPU
            over the last 15 s (default 40)
    resume  when they stayed under RENDER_GPU_RESUME % (default 15) for 45 s in a row

Exits by itself when the render ends, resuming it first. Log: logs/render_gate.log"""
import os
import re
import signal
import subprocess
import sys
import time

ROOT = "/Users/dancostin/Downloads/Generate3D"
PAT = "apartment/flythrough.py"
PAUSE = float(os.environ.get("RENDER_GPU_PAUSE", "40"))
RESUME = float(os.environ.get("RENDER_GPU_RESUME", "15"))
STEP, CALM = 15.0, 45.0
LOG = os.path.join(ROOT, "logs", "render_gate.log")


def render_pids():
    out = subprocess.run(["pgrep", "-f", PAT], capture_output=True, text=True).stdout
    return {int(p) for p in out.split()}


def gpu_ns_by_pid():
    """pid -> accumulated GPU time in ns, summed over all of its GPU clients."""
    out = subprocess.run(["ioreg", "-r", "-c", "AGXDeviceUserClient", "-l"], capture_output=True, text=True).stdout
    res = {}
    for node in re.split(r"\n\s*[|\s]*\+-o ", out):          # one block per GPU client; properties come in any order
        m = re.search(r'"IOUserClientCreator" = "pid (\d+),', node)
        if m:
            pid = int(m.group(1))
            res[pid] = res.get(pid, 0) + sum(int(v) for v in re.findall(r'"accumulatedGPUTime"=(\d+)', node))
    return res


def signal_all(sig):
    for p in render_pids():
        try:
            os.kill(p, sig)
        except ProcessLookupError:
            pass


def log(msg):
    with open(LOG, "a") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def main():
    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(s, lambda *_: (signal_all(signal.SIGCONT), sys.exit(0)))
    time.sleep(10)
    paused, calm_since = False, None
    prev, t_prev = gpu_ns_by_pid(), time.time()
    log("gate started (pause > {}%, resume < {}%)".format(PAUSE, RESUME))
    try:
        while render_pids():
            time.sleep(STEP)
            cur, now = gpu_ns_by_pid(), time.time()
            mine = render_pids()
            used = sum(max(0, v - prev.get(p, v)) for p, v in cur.items() if p not in mine)
            pct = 100.0 * used / ((now - t_prev) * 1e9)
            prev, t_prev = cur, now
            if not paused and pct > PAUSE:
                signal_all(signal.SIGSTOP)
                paused, calm_since = True, None
                log("pause  (other programs {:.0f}% GPU)".format(pct))
            elif paused:
                if pct < RESUME:
                    calm_since = calm_since or now
                    if now - calm_since >= CALM:
                        signal_all(signal.SIGCONT)
                        paused = False
                        log("resume (other programs {:.0f}% GPU)".format(pct))
                else:
                    calm_since = None
    finally:
        signal_all(signal.SIGCONT)


main()
