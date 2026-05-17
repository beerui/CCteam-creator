"""Fingerprint extraction and computation."""
import hashlib
import re

# 顶帧提取正则: 兼容 Chrome V8 / Firefox / 纯路径
_CHROME_FRAME = re.compile(r"at\s+(\S+)\s+\((?:https?://[^/]+)?([^)]+?):(\d+):\d+\)")
_FIREFOX_FRAME = re.compile(r"(\S+)@(?:https?://[^/]+)?([^:]+?):(\d+):\d+")
_PLAIN_FRAME = re.compile(r"([^\s]+\.[a-z]+):(\d+)(?::\d+)?")

_SKIP_PATTERNS = (
    "node_modules/",
    "chunk-vendors",
    "webpack-internal:",
    ".min.js",
)


def _is_business_frame(file_path: str) -> bool:
    return not any(p in file_path for p in _SKIP_PATTERNS)


def extract_top_frame(stack: str) -> str:
    """从 stack trace 提取顶帧 → 'file.js:fn' 或 'file.js:lineno'.

    返回 sentinel:
    - '<no-stack>' 当 stack 为空
    - '<unparseable>' 当无法解析
    """
    if not stack or not stack.strip():
        return "<no-stack>"

    for line in stack.splitlines():
        line = line.strip()
        if not line:
            continue

        # Chrome V8: at fn (path:L:C)
        m = _CHROME_FRAME.search(line)
        if m:
            fn, path, _line_no = m.groups()
            if _is_business_frame(path):
                return f"{path.rsplit('/', 1)[-1]}:{fn}"
            continue

        # Firefox: fn@path:L:C
        m = _FIREFOX_FRAME.search(line)
        if m:
            fn, path, _line_no = m.groups()
            if _is_business_frame(path):
                return f"{path.rsplit('/', 1)[-1]}:{fn}"
            continue

        # 纯路径: file.js:L
        m = _PLAIN_FRAME.search(line)
        if m:
            path, line_no = m.groups()
            if _is_business_frame(path):
                return f"{path.rsplit('/', 1)[-1]}:{line_no}"
            continue

    return "<unparseable>"


def compute_fingerprint(conv_message: str, stack_top_frame: str) -> str:
    """计算 SHA1(conv_message + ' @ ' + stack_top_frame) 十六进制."""
    key = f"{conv_message} @ {stack_top_frame}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()
