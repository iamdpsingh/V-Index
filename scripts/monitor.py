"""Read-only operator health snapshot; nonzero exit enables timer/runner alerts."""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from vindex.db import Session
from vindex.operations import snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    if not 15 <= args.interval <= 3600:
        parser.error("Interval must be 15 to 3600 seconds")
    previous = None
    while True:
        with Session() as session:
            report = snapshot(session)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", dir=args.output.parent, delete=False
            ) as target:
                json.dump(report, target, indent=2)
                target.write("\n")
            os.replace(target.name, args.output)
        state = {
            "counts": report["counts"],
            "alerts": report["alerts"],
            "live_workers": report["workers"]["live"],
            "redis_available": report["redis_available"],
        }
        if state != previous:
            print(json.dumps({"checked_at": report["checked_at"], **state}), flush=True)
            previous = state
        if not args.watch:
            raise SystemExit(1 if report["alerts"] else 0)
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
