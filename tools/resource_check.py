"""How much does Hours N Silence cost while it runs?

    python tools/resource_check.py [seconds]

Samples the app's CPU share, memory and GPU use (via nvidia-smi when
present) for a few seconds and prints averages and peaks. Run it once with
the full window open and once with the mini player showing (sparks on) to
see the difference.
"""
import subprocess
import sys
import time

import psutil


def find_app():
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            if (p.info["name"] or "").lower().startswith("python") and "appleview" in " ".join(p.info["cmdline"] or []).lower():
                return p
        except Exception:
            continue
    return None


def gpu_for(pid):
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 2 and parts[0] == str(pid):
                return int(parts[1])
        util = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
        return f"not a GPU process (whole GPU at {util}% busy)"
    except Exception:
        return "nvidia-smi not available"


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    p = find_app()
    if p is None:
        print("Hours N Silence is not running")
        return 1
    cores = psutil.cpu_count() or 1
    p.cpu_percent(None)
    cpu, rss = [], []
    t0 = time.time()
    while time.time() - t0 < seconds:
        time.sleep(0.5)
        cpu.append(p.cpu_percent(None) / cores)     # share of the whole machine
        rss.append(p.memory_info().rss / (1024 * 1024))
    print(f"pid {p.pid} | threads {p.num_threads()} | samples {len(cpu)} over {seconds}s")
    print(f"CPU of whole machine: avg {sum(cpu)/len(cpu):.1f}%  peak {max(cpu):.1f}%")
    print(f"memory: avg {sum(rss)/len(rss):.0f} MB  peak {max(rss):.0f} MB")
    print("GPU:", gpu_for(p.pid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
