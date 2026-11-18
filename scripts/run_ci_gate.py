#!/usr/bin/env python3
## @package scripts.run_ci_gate
#  Run one validation gate and record the exact command, result, and revision.

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description='Run one CI gate and save evidence')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('A command is required after --')
    if command[0] == 'python':
        command[0] = sys.executable
    started = datetime.now(timezone.utc).isoformat()
    timer = time.monotonic()
    error = None
    try:
        result = subprocess.run(command, check=False)
        exit_code = result.returncode
    except OSError as exc:
        exit_code = 127
        error = str(exc)
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
    report = dict(command=command, exit_code=exit_code, error=error, started_utc=started,
                  duration_seconds=time.monotonic() - timer,
                  revision=revision.stdout.strip() if revision.returncode == 0 else None,
                  python=sys.version, platform=platform.platform())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
