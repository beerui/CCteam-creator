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
