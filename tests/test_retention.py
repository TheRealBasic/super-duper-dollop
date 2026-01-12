from datetime import datetime, timedelta, timezone
from pathlib import Path

from where_did_my_time_go.storage import Database, SessionRecord


def test_cleanup_retention(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.initialize()

    now = datetime.now(timezone.utc)
    old_start = (now - timedelta(days=10)).isoformat()
    old_end = (now - timedelta(days=9)).isoformat()
    new_start = (now - timedelta(days=1)).isoformat()
    new_end = now.isoformat()

    db.add_session(
        SessionRecord(
            start_ts=old_start,
            end_ts=old_end,
            duration_sec=3600,
            process_name="Old",
            exe_path="",
            window_title="",
            category="Work",
            intent_tag=None,
        )
    )
    db.add_session(
        SessionRecord(
            start_ts=new_start,
            end_ts=new_end,
            duration_sec=1800,
            process_name="New",
            exe_path="",
            window_title="",
            category="Work",
            intent_tag=None,
        )
    )

    deleted = db.cleanup_retention(7)
    assert deleted == 1
    remaining = db.fetch_sessions((now - timedelta(days=30)).isoformat(), now.isoformat())
    assert len(remaining) == 1
