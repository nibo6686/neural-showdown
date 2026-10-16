"""Run one explicitly selected workload with a process-tree deadline."""
import argparse
import os
from pathlib import Path
import signal
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=180)
    parser.add_argument('--cwd', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.seconds < 1:
        parser.error('Supply a positive deadline and a command after --.')
    settings = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen(command, cwd=args.cwd, **settings)
    try:
        return process.wait(timeout=args.seconds)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        if process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               check=False, timeout=20)
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=20)
        print('Owned workload stopped; timed out or interrupted.', flush=True)
        return 124


if __name__ == '__main__':
    raise SystemExit(main())
