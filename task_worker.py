"""
Poll scheduled_posts and execute due tasks using Dashboard settings.
Run directly:  python task_worker.py
Or as part of the unified backend:  python api_server.py
"""
import traceback
import threading
from datetime import datetime, timezone

from supabase_logger import (
    seed_devices,
    get_bot_settings,
    fetch_scheduled_tasks,
    update_scheduled_task,
    reset_stuck_running_tasks,
)
from task_executor import execute_scheduled_post

POLL_INTERVAL_SECONDS = 10

def _parse_iso(iso_string: str) -> datetime:
    return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))

def _get_schedule_times(task: dict) -> list[str]:
    times = task.get("schedule_times") or []
    if not times and task.get("schedule_at"):
        return [task["schedule_at"]]
    return times

def is_task_due(task: dict, now: datetime | None = None) -> bool:
    """True if this task has a pending slot whose schedule time has passed."""
    if task.get("status") != "pending":
        return False

    times = _get_schedule_times(task)
    slot = task.get("posts_completed") or 0
    content_count = task.get("content_count") or 1

    if slot >= content_count or slot >= len(times):
        return False

    now = now or datetime.now(timezone.utc)
    due_at = _parse_iso(times[slot])
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)

    return due_at <= now

def process_due_tasks() -> int:
    """
    Find and execute all due pending tasks.
    Returns the number of tasks processed.
    """
    seed_devices()
    bot_settings = get_bot_settings()
    tasks = fetch_scheduled_tasks()
    processed = 0

    for task in tasks:
        if not is_task_due(task):
            continue

        task_id = task["id"]
        slot_index = task.get("posts_completed") or 0
        times = _get_schedule_times(task)
        content_count = task.get("content_count") or 1

        print(f"\n⏰ Task #{task_id} is due (slot {slot_index + 1}). Starting...")
        update_scheduled_task(task_id, "running", error=None)

        try:
            execute_scheduled_post(task, bot_settings, slot_index)
            new_completed = slot_index + 1
            has_more = new_completed < content_count and new_completed < len(times)

            if has_more:
                update_scheduled_task(
                    task_id,
                    "pending",
                    error=None,
                    posts_completed=new_completed,
                )
                print(f"📋 Task #{task_id} → pending (next slot {new_completed + 1}/{content_count})")
            else:
                update_scheduled_task(
                    task_id,
                    "completed",
                    error=None,
                    posts_completed=new_completed,
                )
                print(f"📋 Task #{task_id} → completed")

            processed += 1

        except Exception as exc:
            message = str(exc)
            print(f"\n❌ Task #{task_id} failed: {message}")
            traceback.print_exc()
            update_scheduled_task(task_id, "failed", error=message)

    return processed

def run_worker_loop(stop_event: threading.Event | None = None):
    import time

    print("=" * 55)
    print("   GeeLark Task Worker — Starting")
    print(f"   Poll interval: every {POLL_INTERVAL_SECONDS}s")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    reset_stuck_running_tasks()

    while True:
        if stop_event and stop_event.is_set():
            break

        try:
            count = process_due_tasks()
            if count:
                print(f"\n✅ Processed {count} task(s) this cycle.")
        except Exception:
            print("\n❌ Worker cycle error:")
            traceback.print_exc()

        if stop_event:
            if stop_event.wait(POLL_INTERVAL_SECONDS):
                break
        else:
            time.sleep(POLL_INTERVAL_SECONDS)

    print(f"\n🛑 Task worker stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")

if __name__ == "__main__":
    try:
        run_worker_loop()
    except KeyboardInterrupt:
        print(f"\n🛑 Task worker stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
