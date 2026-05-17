"""SLS query + aggregation. Query function is thin wrapper around aliyun SDK."""
import os
from typing import Optional

from arms_lib.fingerprint import extract_top_frame, normalize_for_fingerprint


def aggregate_exceptions(logs: list[dict]) -> list[dict]:
    """按 (conv_message + stack_top_frame) 聚合, 返回每个指纹一条.

    conv_message / stack_top_frame 在入口经 normalize_for_fingerprint 归一化,
    使 chunk hash / 毫秒时间戳等"字面量噪音"不拆 bucket. 写入 dict 的也是
    归一化版本, 与 SQLite 存储和 select_fingerprint_match 的匹配键一致.

    每条聚合结果 schema:
      conv_message, stack_top_frame, view_name, env, app, pid, count,
      first_event_id, first_session_id, first_timestamp
    """
    buckets: dict[tuple, dict] = {}
    for log in logs:
        raw_conv = log.get("exception.message.convergence") or log.get("exception.message", "")
        stack = log.get("exception.stack", "")
        raw_frame = extract_top_frame(stack)
        conv_msg = normalize_for_fingerprint(raw_conv)
        top_frame = normalize_for_fingerprint(raw_frame)
        key = (conv_msg, top_frame)

        if key not in buckets:
            buckets[key] = {
                "conv_message": conv_msg,
                "stack_top_frame": top_frame,
                "view_name": log.get("view.name.convergence") or log.get("view.name", ""),
                "env": log.get("app.env", ""),
                "app": log.get("app.name", ""),
                "pid": log.get("app.id", ""),
                "count": 0,
                "first_event_id": log.get("event_id", ""),
                "first_session_id": log.get("session.id", ""),
                "first_timestamp": int(log.get("__time__", 0)),
            }
        buckets[key]["count"] += 1

    return list(buckets.values())


def _build_query(pid: str, env: Optional[str], keywords: Optional[str]) -> str:
    """构造 SLS query 字符串. 拒绝 keywords 中的控制字符, 转义 \\ 和 "."""
    parts = [f"app.id:{pid}", "event_type:exception"]
    if env:
        parts.append(f"app.env:{env}")
    if keywords:
        if any(c in keywords for c in "\n\r\t\x00"):
            raise ValueError(
                "keywords contains control character (\\n / \\r / \\t / NUL); rejected"
            )
        # 反斜杠先转, 否则后续转义的 \" 会被反向消解
        escaped = keywords.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'exception.message:"{escaped}"')
    return " AND ".join(parts)


def query_exceptions(  # pragma: no cover
    *,
    pid: str,
    env: Optional[str] = None,
    days: int = 1,
    keywords: Optional[str] = None,
    line: int = 500,
) -> list[dict]:
    """从 SLS 拉异常日志.

    依赖 .env / 环境变量:
      ARMS_AK_ID, ARMS_AK_SECRET, SLS_REGION, SLS_PROJECT, SLS_LOGSTORE

    返回原始 log dict 列表 (未聚合).
    """
    from aliyun.log import LogClient, GetLogsRequest
    import time

    ak_id = os.environ["ARMS_AK_ID"]
    ak_secret = os.environ["ARMS_AK_SECRET"]
    region = os.environ["SLS_REGION"]
    project = os.environ["SLS_PROJECT"]
    logstore = os.environ["SLS_LOGSTORE"]

    endpoint = f"{region}.log.aliyuncs.com"
    client = LogClient(endpoint, ak_id, ak_secret)

    now = int(time.time())
    from_time = now - days * 86400

    query = _build_query(pid=pid, env=env, keywords=keywords)

    req = GetLogsRequest(
        project=project,
        logstore=logstore,
        fromTime=from_time,
        toTime=now,
        query=query,
        line=line,
        offset=0,
    )
    resp = client.get_logs(req)
    return [log.get_contents() for log in resp.get_logs()]
