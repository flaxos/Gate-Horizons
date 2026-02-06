"""Module entry point for python -m gate_horizons."""

import sys
import traceback


def main():
    from gate_horizons.main import main as _main
    _main()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Write crash log so the error is visible even if the window closes
        crash_log = traceback.format_exc()
        print(crash_log, file=sys.stderr)
        try:
            with open("gate_horizons_crash.log", "w") as f:
                f.write(crash_log)
            print(f"\nCrash log written to gate_horizons_crash.log", file=sys.stderr)
        except OSError:
            pass
        sys.exit(1)
