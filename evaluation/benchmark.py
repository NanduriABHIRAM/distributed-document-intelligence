"""Measure an explicit command, including sampled process-tree CPU/RSS usage."""
import argparse
import json
import subprocess
import time
from pathlib import Path
import psutil

def benchmark(command, items, interval=0.1):
    if not command or items<0: raise ValueError('A command and nonnegative item count are required')
    start=time.perf_counter(); peak=0; cpu=0.0; samples=0
    child=subprocess.Popen(command)
    process=psutil.Process(child.pid)
    while child.poll() is None:
        try:
            tree=[process,*process.children(recursive=True)]
            memory=0; cpu_sample=0.0
            for p in tree:
                try:
                    memory+=p.memory_info().rss
                    times=p.cpu_times(); cpu_sample+=times.user+times.system
                except psutil.NoSuchProcess: pass
            peak=max(peak,memory); cpu=max(cpu,cpu_sample); samples+=1
        except psutil.NoSuchProcess: pass
        time.sleep(interval)
    elapsed=time.perf_counter()-start
    return {'command':command,'returncode':child.returncode,'items':items,'elapsed_seconds':elapsed,
            'items_per_second':items/elapsed if child.returncode==0 else None,
            'peak_sampled_rss_mb':peak/1024**2,'sampled_cpu_seconds':cpu,'samples':samples,
            'gpu_utilization':None,'gpu_note':'Not measured; use vendor telemetry for GPU experiments.'}
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--items',type=int,required=True)
    parser.add_argument('--output',required=True); parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args(); command=args.command[1:] if args.command[:1]==['--'] else args.command
    result=benchmark(command,args.items); Path(args.output).write_text(json.dumps(result,indent=2))
    raise SystemExit(result['returncode'])
