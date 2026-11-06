"""Keep this PC from idle-sleeping until a set time, so overnight data queues and checks keep running.
It only asks Windows not to sleep while this script runs (SetThreadExecutionState); no setting is changed,
and the request ends when the script exits. Run: python tools/stay_awake.py 15:05"""
import ctypes
import sys
import time
from datetime import datetime

ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001


def main() -> None:
    hour, minute = (int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "15:05").split(":"))
    end = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    while datetime.now() < end:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        time.sleep(60)
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


if __name__ == "__main__":
    main()
