"""Load per-project ARMS configuration from .plans/<project>/arms/config.json.

Schema (all keys optional, all forward-compatible — unknown keys ignored by readers):
  - default_env: str — env to scan in SessionStart hook (e.g., "prod", "test", "daily")

Future fields (P2+): retention_days, ignore_patterns, severity_thresholds.
"""
import json
import sys
from pathlib import Path


def load_config(arms_dir: Path) -> dict:
    """从 arms_dir/config.json 读配置. 文件不存在或 JSON 错误 → 返回 {}.

    Why: per-project override 比环境变量更结构化 (未来扩 retention 等不用再加 var),
    比 CLAUDE.md 解析更轻量 (JSON 而非 markdown 字段提取).
    """
    config_path = arms_dir / "config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(
            f"arms-on-session: config.json parse warning ({e}), using defaults",
            file=sys.stderr,
        )
        return {}
