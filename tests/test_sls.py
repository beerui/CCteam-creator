"""Tests for arms_lib.sls (pure-logic only, no network)."""
import pytest

from arms_lib.sls import _build_query, aggregate_exceptions
from fixtures.sls_responses import SAMPLE_LOGS


def test_aggregate_groups_by_fingerprint():
    """同一 fingerprint (conv_msg + stack_top_frame) 应合并计数"""
    aggregated = aggregate_exceptions(SAMPLE_LOGS)
    assert len(aggregated) == 2

    fps = {a["conv_message"]: a for a in aggregated}
    assert "conv list failed: 33001" in fps
    assert fps["conv list failed: 33001"]["count"] == 2
    assert fps["conv list failed: 33001"]["stack_top_frame"] == "agent.abc.js:onResponse"

    assert "token 无效" in fps
    assert fps["token 无效"]["count"] == 1
    assert fps["token 无效"]["stack_top_frame"] == "auth.def.js:verify"


def test_aggregate_keeps_first_view():
    """聚合时取第一条 log 的 view_name"""
    aggregated = aggregate_exceptions(SAMPLE_LOGS)
    fps = {a["conv_message"]: a for a in aggregated}
    assert fps["conv list failed: 33001"]["view_name"] == "/agent"


def test_aggregate_empty_input():
    assert aggregate_exceptions([]) == []


def _mk_log(conv_msg: str, stack_url: str, idx: int) -> dict:
    """Helper: 造一条 SLS log dict, 仅 conv_msg / stack 不同."""
    return {
        "__time__": f"171600010{idx}",
        "app.id": "p",
        "app.name": "app",
        "app.env": "prod",
        "view.name": "/v",
        "view.name.convergence": "/v",
        "exception.message": conv_msg,
        "exception.message.convergence": conv_msg,
        "exception.stack": (
            "TypeError: x\n"
            f"    at loadStyle ({stack_url}:1:1)"
        ),
        "event_id": f"e-{idx}",
        "session.id": f"s-{idx}",
    }


def test_aggregate_collapses_chunk_hash_variants():
    """5 条仅 chunk hash 不同的 log → 1 个 bucket (count=5).

    复现真 e2e 现场: 当前 prod 7 条指纹里有 4 条是 CSS preload 失败,
    因 goods-card-C9Ijfs5t / uni-icons-D_JIDRp3 等 build hash 不同被拆.
    """
    logs = [
        _mk_log(
            "css preload failed",
            f"https://cdn.example.com/dist/goods-card-{h}.js",
            i,
        )
        for i, h in enumerate(
            ["C9Ijfs5t", "D_JIDRp3", "Ab12CdEf", "qrst5678", "uvwx9012"]
        )
    ]
    aggregated = aggregate_exceptions(logs)
    assert len(aggregated) == 1
    assert aggregated[0]["count"] == 5
    assert "{HASH}" in aggregated[0]["stack_top_frame"]


def test_aggregate_collapses_iso_ms_variants():
    """5 条仅 conv_msg 毫秒时间戳不同 → 1 个 bucket (count=5).

    复现真 e2e 现场: daji 测试服 5 条 [ARMS 测试错误] 因 .453Z/.424Z/.217Z 拆开.
    """
    logs = [
        _mk_log(
            f"[ARMS 测试错误] 2026-05-17T10:30:45.{ms}Z",
            "https://cdn.example.com/test.js",
            i,
        )
        for i, ms in enumerate(["453", "424", "217", "5", "42"])
    ]
    aggregated = aggregate_exceptions(logs)
    assert len(aggregated) == 1
    assert aggregated[0]["count"] == 5
    assert "{MS}" in aggregated[0]["conv_message"]


class TestBuildQuery:
    def test_pid_only(self):
        q = _build_query(pid="c67xxx", env=None, keywords=None)
        assert q == "app.id:c67xxx AND event_type:exception"

    def test_pid_and_env(self):
        q = _build_query(pid="c67xxx", env="prod", keywords=None)
        assert q == "app.id:c67xxx AND event_type:exception AND app.env:prod"

    def test_with_keywords(self):
        q = _build_query(pid="c67xxx", env="daily", keywords="conv list")
        assert q == 'app.id:c67xxx AND event_type:exception AND app.env:daily AND exception.message:"conv list"'

    def test_keywords_quote_escaped(self):
        """keywords 含 " 必须被转义, 防止 query 提前结束"""
        q = _build_query(pid="P", env=None, keywords='evil" AND app.env:prod')
        # 内层的 " 应该被 \"  转义
        assert 'exception.message:"evil\\" AND app.env:prod"' in q

    def test_keywords_backslash_escaped(self):
        """反斜杠先于引号转义 (避免 '\\"' 被反向消解)"""
        q = _build_query(pid="P", env=None, keywords='path\\\\file')
        # Python 字符串 path\\file → escape 后 path\\\\file
        assert 'exception.message:"path\\\\\\\\file"' in q

    def test_keywords_newline_rejected(self):
        with pytest.raises(ValueError, match="control character"):
            _build_query(pid="P", env=None, keywords="line1\nline2")

    def test_keywords_carriage_return_rejected(self):
        with pytest.raises(ValueError, match="control character"):
            _build_query(pid="P", env=None, keywords="bad\rkeyword")
