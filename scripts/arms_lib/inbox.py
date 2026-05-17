"""Render inbox.md from SQLite query results."""
from typing import Iterable


def render_inbox(
    *,
    last_scan_iso: str,
    new: Iterable[dict],
    recurring: Iterable[dict],
    in_progress: Iterable[dict],
) -> str:
    """渲染 inbox.md markdown.

    输入项的 dict schema 见 test_inbox.py 用例。
    """
    new = list(new)
    recurring = list(recurring)
    in_progress = list(in_progress)

    lines = [
        f"# ARMS Inbox · last_scan: {last_scan_iso}",
        "",
        f"## 🆕 新增 ({len(new)})",
        "",
    ]
    for item in new:
        lines.extend([
            f"- **[{item['severity']}] {item['conv_message']}**",
            f"  - 位置: {item['stack_top_frame']}",
            f"  - 环境: {item['env']}, {item['count']} 次",
            f"  - 任务: [{item['task_id']}](./{item['task_id']}/)",
            f"  - 深挖: `/arms task={item['task_id']}`",
            "",
        ])

    lines.extend([
        f"## 🔁 复发 ({len(recurring)})",
        "",
    ])
    for item in recurring:
        lines.extend([
            f"- **[{item['severity']}] {item['conv_message']}**",
            f"  - 上次: {item['task_id']}, commit `{item['last_commit_hash']}`, "
            f"{item['last_resolved_at']} 标 resolved",
            f"  - 复发: {item['current_date']} 新增 {item['current_count']} 次",
            f"  - 建议: `/arms task={item['task_id']}` 复审",
            "",
        ])

    lines.extend([
        f"## ⏳ 进行中 ({len(in_progress)})",
        "",
    ])
    for item in in_progress:
        lines.append(
            f"- {item['task_id']} — {item['assignee']} 处理中, 分支 `{item['branch']}`"
        )
    lines.append("")
    lines.extend([
        "---",
        "_24h 内打开 Claude Code 不会重新扫描; 强制重扫: `/arms env=prod days=1`_",
    ])

    return "\n".join(lines) + "\n"
