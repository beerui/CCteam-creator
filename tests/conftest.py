"""Shared pytest fixtures."""
import sqlite3
import pytest


@pytest.fixture
def tmp_db_path(tmp_path):
    """临时 sqlite db 路径 (测试完自动清理)"""
    return tmp_path / "test_archive.db"


@pytest.fixture
def empty_db_conn(tmp_db_path):
    """已 init_schema 过的空 db 连接"""
    from arms_lib.db import init_schema
    conn = sqlite3.connect(tmp_db_path)
    init_schema(conn)
    yield conn
    conn.close()
