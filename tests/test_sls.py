"""Tests for arms_lib.sls (pure-logic only, no network)."""
from arms_lib.sls import aggregate_exceptions
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
