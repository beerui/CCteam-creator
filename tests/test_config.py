"""Tests for arms_lib.config (load .plans/<project>/arms/config.json)."""
import json
from pathlib import Path

from arms_lib.config import load_config


def test_load_config_returns_default_env_from_file(tmp_path):
    """config.json 含 default_env → load_config 读出"""
    (tmp_path / "config.json").write_text(
        json.dumps({"default_env": "test"}), encoding="utf-8"
    )
    cfg = load_config(tmp_path)
    assert cfg.get("default_env") == "test"


def test_load_config_missing_file_returns_empty(tmp_path):
    """文件不存在 → 返回 {} 而不抛异常"""
    cfg = load_config(tmp_path)
    assert cfg == {}


def test_load_config_malformed_json_returns_empty(tmp_path, capsys):
    """JSON 解析失败 → 返回 {} + stderr warning, 不抛异常"""
    (tmp_path / "config.json").write_text("{invalid json", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg == {}
    captured = capsys.readouterr()
    assert "config.json" in captured.err.lower() or "warning" in captured.err.lower()


def test_load_config_passes_through_unknown_keys(tmp_path):
    """未知键应保留, 供未来扩展 (retention_days 等)"""
    (tmp_path / "config.json").write_text(
        json.dumps({"default_env": "daily", "future_key": 42}), encoding="utf-8"
    )
    cfg = load_config(tmp_path)
    assert cfg["future_key"] == 42
