"""Fingerprint extraction and computation."""
import hashlib
import re

NO_STACK = "<no-stack>"
UNPARSEABLE = "<unparseable>"

# 顶帧提取正则: 兼容 Chrome V8 / Firefox / 纯路径
_CHROME_FRAME = re.compile(r"at\s+(\S+)\s+\((?:https?://[^/]+)?([^)]+?):(\d+):\d+\)")
_FIREFOX_FRAME = re.compile(r"(\S+)@(?:https?://[^/]+)?([^:]+?):(\d+):\d+")
_PLAIN_FRAME = re.compile(r"([^\s:]+\.[a-z]+(?:\?[^\s:]*)?):(\d+)(?::\d+)?")

# Fingerprint 归一化规则: 让"语义同一、字面量不同"的子串塌缩到同一指纹.
# 上限 32 覆盖 vite/webpack 常见 8 位 + 可配 16/20 位 contenthash.
# 前缀 `(^|[/\s])` 兼容两种使用场景: 完整路径 (`/dist/x-AbCd1234.js`) 和
# 经 _basename 提取后的裸文件名 (`x-AbCd1234.js`).
# hash 字符集 `[A-Za-z0-9_-]`: vite 用 RFC 4648 base64url alphabet 含 `_-`,
# 例 `D_JIDRp3`; webpack 默认 hex 但可配 base64. 用 `-` 切分 name/hash, 贪婪+回溯.
_CHUNK_HASH_RE = re.compile(r"(^|[/\s])([A-Za-z0-9_-]+)-[A-Za-z0-9_-]{6,32}\.(js|css|mjs)")
_ISO_MS_RE = re.compile(r"\.\d{1,3}Z")

_SKIP_PATTERNS = (
    "node_modules/",
    "chunk-vendors",
    "webpack-internal:",
    ".min.js",
)


def normalize_for_fingerprint(text: str) -> str:
    """对参与聚合/指纹的字符串做归一化.

    Why: ARMS 上报的字符串里有两类"语义同一、字面量不同"的子串, 不归一化
    会导致同一根因被拆成多条 fingerprint, 撑大 inbox / 绕过 24h 节流匹配:
      1. 前端构建产物 chunk hash (vite/webpack contenthash, 每次 build 变)
      2. ISO 时间戳的毫秒尾巴 (.453Z 这种, 每次报错不同)
    幂等: normalize(normalize(x)) == normalize(x).
    """
    if not text:
        return text
    text = _CHUNK_HASH_RE.sub(r"\1\2-{HASH}.\3", text)
    text = _ISO_MS_RE.sub(".{MS}Z", text)
    return text


def _basename(path: str) -> str:
    """Normalize Windows separators and strip query strings before taking basename.

    Without this, `C:\\Users\\jane\\src\\main.js` leaks usernames into the
    fingerprint hash, and `agent.js?v=1.2.3` produces a fresh fingerprint on
    every deploy — both defeating cross-machine / cross-release dedup.
    """
    normalized = path.replace("\\", "/")
    no_query = normalized.split("?", 1)[0]
    return no_query.rsplit("/", 1)[-1]


def _is_business_frame(file_path: str) -> bool:
    return not any(p in file_path for p in _SKIP_PATTERNS)


def extract_top_frame(stack: str) -> str:
    """从 stack trace 提取顶帧 → 'file.js:fn' 或 'file.js:lineno'.

    返回 sentinel:
    - NO_STACK ('<no-stack>') 当 stack 为空
    - UNPARSEABLE ('<unparseable>') 当无法解析
    """
    if not stack or not stack.strip():
        return NO_STACK

    for line in stack.splitlines():
        line = line.strip()
        if not line:
            continue

        # Chrome V8: at fn (path:L:C)
        m = _CHROME_FRAME.search(line)
        if m:
            fn, path, _line_no = m.groups()
            if _is_business_frame(path):
                return f"{_basename(path)}:{fn}"
            continue

        # Firefox: fn@path:L:C
        m = _FIREFOX_FRAME.search(line)
        if m:
            fn, path, _line_no = m.groups()
            if _is_business_frame(path):
                return f"{_basename(path)}:{fn}"
            continue

        # 纯路径: file.js:L
        m = _PLAIN_FRAME.search(line)
        if m:
            path, line_no = m.groups()
            if _is_business_frame(path):
                return f"{_basename(path)}:{line_no}"
            continue

    return UNPARSEABLE


def compute_fingerprint(conv_message: str, stack_top_frame: str) -> str:
    """计算 SHA1(conv_message + ' @ ' + stack_top_frame) 十六进制.

    入口对两个参数都 normalize_for_fingerprint, 保证 chunk hash / 毫秒戳
    等"字面量噪音"不会拆指纹.
    """
    conv = normalize_for_fingerprint(conv_message)
    frame = normalize_for_fingerprint(stack_top_frame)
    key = f"{conv} @ {frame}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()
