import time
import traceback
from datetime import datetime, timedelta
from main import run_pipeline

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
INTERVAL_HOURS = 1      # How many hours between each run

# ─────────────────────────────────────────
# SCHEDULER LOOP
# ─────────────────────────────────────────
def main():
    run_number = 0

    print("=" * 55)
    print("   GeeLark Scheduler — Starting")
    print(f"   Interval : every {INTERVAL_HOURS} hour(s)")
    print(f"   Started  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    print("   Press Ctrl+C at any time to stop.\n")

    while True:
        run_number += 1
        run_start = datetime.now()

        print("\n" + "─" * 55)
        print(f"⏰ Run #{run_number} starting at {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print("─" * 55)

        try:
            success = run_pipeline()
            status  = "✅ Completed" if success else "⏭️  Skipped (no new content)"
        except Exception:
            status = "❌ Failed with error"
            print("\n" + "─" * 55)
            print("❌ Unhandled exception in pipeline — scheduler will continue.")
            traceback.print_exc()

        run_end     = datetime.now()
        elapsed     = run_end - run_start
        next_run    = run_end + timedelta(hours=INTERVAL_HOURS)

        print("\n" + "─" * 55)
        print(f"   Run #{run_number} status  : {status}")
        print(f"   Elapsed          : {str(elapsed).split('.')[0]}")
        print(f"   Next run at      : {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print("─" * 55)

        # Countdown until next run — updates every minute in-place
        sleep_seconds = INTERVAL_HOURS * 1800
        remaining     = sleep_seconds
        while remaining > 0:
            mins, secs = divmod(remaining, 60)
            hrs,  mins = divmod(mins, 60)
            next_str   = next_run.strftime('%H:%M:%S')
            print(
                f"\r⏳ Next run at {next_str} — "
                f"waiting {int(hrs):02d}h {int(mins):02d}m {int(secs):02d}s ...   ",
                end="", flush=True
            )
            tick = min(60, remaining)
            time.sleep(tick)
            remaining -= tick
        print()  # newline after countdown finishes


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n🛑 Scheduler stopped manually at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
