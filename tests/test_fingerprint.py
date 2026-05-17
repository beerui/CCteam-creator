"""Tests for arms_lib.fingerprint."""
from arms_lib.fingerprint import extract_top_frame, compute_fingerprint, normalize_for_fingerprint
from fixtures.stack_traces import (
    CHROME_V8, FIREFOX, PLAIN_PATH, VENDOR_FIRST, MIN_JS_FIRST, EMPTY, GARBLED,
    WINDOWS_PATH, URL_QUERY, URL_QUERY_FIREFOX, URL_QUERY_PLAIN,
)


class TestExtractTopFrame:
    def test_chrome_v8_format(self):
        assert extract_top_frame(CHROME_V8) == "agent.abc123.js:onResponse"

    def test_firefox_format(self):
        assert extract_top_frame(FIREFOX) == "agent.abc123.js:onResponse"

    def test_plain_path(self):
        assert extract_top_frame(PLAIN_PATH) == "conv.js:42"

    def test_skip_vendor_chunks(self):
        assert extract_top_frame(VENDOR_FIRST) == "agent.abc.js:onResponse"

    def test_skip_min_js(self):
        assert extract_top_frame(MIN_JS_FIRST) == "agent.js:onResponse"

    def test_empty_stack(self):
        assert extract_top_frame(EMPTY) == "<no-stack>"

    def test_garbled_stack(self):
        assert extract_top_frame(GARBLED) == "<unparseable>"

    def test_windows_path_basename(self):
        assert extract_top_frame(WINDOWS_PATH) == "main.js:onResponse"

    def test_url_query_stripped_chrome(self):
        assert extract_top_frame(URL_QUERY) == "agent.js:onResponse"

    def test_url_query_stripped_firefox(self):
        assert extract_top_frame(URL_QUERY_FIREFOX) == "agent.js:onResponse"

    def test_url_query_stripped_plain(self):
        assert extract_top_frame(URL_QUERY_PLAIN) == "conv.js:42"


class TestSentinelConstants:
    def test_no_stack_constant_exported(self):
        from arms_lib.fingerprint import NO_STACK
        assert NO_STACK == "<no-stack>"

    def test_unparseable_constant_exported(self):
        from arms_lib.fingerprint import UNPARSEABLE
        assert UNPARSEABLE == "<unparseable>"


class TestComputeFingerprint:
    def test_returns_40char_hex(self):
        fp = compute_fingerprint("conv list failed", "conv.js:onResponse")
        assert len(fp) == 40
        assert all(c in "0123456789abcdef" for c in fp)

    def test_deterministic(self):
        assert compute_fingerprint("err", "f:n") == compute_fingerprint("err", "f:n")

    def test_different_inputs_differ(self):
        assert compute_fingerprint("A", "f:n") != compute_fingerprint("B", "f:n")
        assert compute_fingerprint("X", "f:1") != compute_fingerprint("X", "f:2")

    def test_normalizes_chunk_hash_so_same_fp(self):
        """同根因不同 build hash → 同一 fingerprint (vite/webpack contenthash)"""
        fp1 = compute_fingerprint(
            "css preload failed",
            "goods-card-C9Ijfs5t.js:loadStyle",
        )
        fp2 = compute_fingerprint(
            "css preload failed",
            "goods-card-D_JIDRp3.js:loadStyle",
        )
        assert fp1 == fp2

    def test_normalizes_ms_timestamp_so_same_fp(self):
        """conv_message 含 ISO 时间戳的毫秒尾巴, 不同毫秒 → 同一 fingerprint"""
        fp1 = compute_fingerprint(
            "[ARMS 测试错误] 2026-05-17T10:30:45.453Z",
            "test.js:fire",
        )
        fp2 = compute_fingerprint(
            "[ARMS 测试错误] 2026-05-17T10:30:45.217Z",
            "test.js:fire",
        )
        assert fp1 == fp2


class TestNormalizeForFingerprint:
    """归一化规则: 让"语义同一、字面量不同"的字符串塌缩到同一指纹."""

    def test_chunk_hash_js(self):
        result = normalize_for_fingerprint("/dist/goods-card-C9Ijfs5t.js")
        assert result == "/dist/goods-card-{HASH}.js"

    def test_chunk_hash_css(self):
        result = normalize_for_fingerprint("/assets/style-AbCd1234.css")
        assert result == "/assets/style-{HASH}.css"

    def test_chunk_hash_mjs(self):
        result = normalize_for_fingerprint("/m/chunk-abcd5678.mjs")
        assert result == "/m/chunk-{HASH}.mjs"

    def test_chunk_hash_long_hash(self):
        """vite/webpack 可配 16/20 位 hash, 上限 32 应覆盖"""
        result = normalize_for_fingerprint(
            "/dist/x-aBcD1234efGH5678ijKL90.js"
        )
        assert result == "/dist/x-{HASH}.js"

    def test_chunk_hash_preserves_name_with_underscore_dash(self):
        result = normalize_for_fingerprint("/d/uni-icons_v2-AbCd1234.js")
        assert result == "/d/uni-icons_v2-{HASH}.js"

    def test_iso_ms_three_digits(self):
        result = normalize_for_fingerprint("2026-05-17T10:30:45.453Z")
        assert result == "2026-05-17T10:30:45.{MS}Z"

    def test_iso_ms_one_digit(self):
        result = normalize_for_fingerprint("2026-05-17T10:30:45.5Z")
        assert result == "2026-05-17T10:30:45.{MS}Z"

    def test_idempotent(self):
        once = normalize_for_fingerprint("/d/x-Ab12345678.js @ T.453Z")
        twice = normalize_for_fingerprint(once)
        assert once == twice

    def test_plain_text_unchanged(self):
        assert normalize_for_fingerprint("conv list failed: 33001") == "conv list failed: 33001"

    def test_empty_string(self):
        assert normalize_for_fingerprint("") == ""

    def test_does_not_touch_short_version_suffix(self):
        """3 位版本号不应被误归一化为 hash (例: chart-3.2.1.js)"""
        # `3.2` 只有 3 字符且含点, 不匹配 [A-Za-z0-9]{6,32}
        result = normalize_for_fingerprint("/lib/chart-3.2.1.js")
        assert result == "/lib/chart-3.2.1.js"
