"""Tests for arms_lib.fingerprint."""
from arms_lib.fingerprint import extract_top_frame, compute_fingerprint
from fixtures.stack_traces import (
    CHROME_V8, FIREFOX, PLAIN_PATH, VENDOR_FIRST, MIN_JS_FIRST, EMPTY, GARBLED
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
