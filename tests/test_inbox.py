"""Tests for arms_lib.inbox."""
from arms_lib.inbox import render_inbox


def test_empty_sections():
    md = render_inbox(
        last_scan_iso="2026-05-17 09:03",
        new=[],
        recurring=[],
        in_progress=[],
    )
    assert "## 🆕 新增 (0)" in md
    assert "## 🔁 复发 (0)" in md
    assert "## ⏳ 进行中 (0)" in md
    assert "last_scan: 2026-05-17 09:03" in md


def test_new_section_rendering():
    md = render_inbox(
        last_scan_iso="2026-05-17 09:03",
        new=[{
            "task_id": "arms-20260517-001",
            "severity": "P2",
            "conv_message": "conv list failed: 33001",
            "stack_top_frame": "conv.js:onResponse",
            "env": "daily",
            "count": 8,
        }],
        recurring=[],
        in_progress=[],
    )
    assert "🆕 新增 (1)" in md
    assert "[P2] conv list failed: 33001" in md
    assert "conv.js:onResponse" in md
    assert "daily, 8 次" in md
    assert "arms-20260517-001" in md


def test_recurring_section_rendering():
    md = render_inbox(
        last_scan_iso="2026-05-17 09:03",
        new=[],
        recurring=[{
            "task_id": "arms-20260430-002",
            "severity": "P3",
            "conv_message": "token 无效或已过期",
            "last_commit_hash": "abc1234",
            "last_resolved_at": "2026-04-30",
            "current_count": 5,
            "current_date": "2026-05-15",
        }],
        in_progress=[],
    )
    assert "🔁 复发 (1)" in md
    assert "commit `abc1234`" in md
    assert "2026-04-30" in md
    assert "2026-05-15" in md
    assert "5 次" in md


def test_in_progress_section_rendering():
    md = render_inbox(
        last_scan_iso="2026-05-17 09:03",
        new=[],
        recurring=[],
        in_progress=[{
            "task_id": "arms-20260516-003",
            "assignee": "frontend-dev",
            "branch": "fix/arms-20260516-003",
        }],
    )
    assert "⏳ 进行中 (1)" in md
    assert "arms-20260516-003" in md
    assert "frontend-dev" in md
    assert "fix/arms-20260516-003" in md
