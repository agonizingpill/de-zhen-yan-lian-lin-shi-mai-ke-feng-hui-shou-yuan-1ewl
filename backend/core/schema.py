"""幂等的旧库升级。

`metadata.create_all` 只建新表、不会修改已有表。演示环境的 MySQL 数据卷会跨
重启保留，因此这里补上复判所需的列、去掉旧的单窗口唯一约束，并回填证据快照。
升级只针对 MySQL；其他方言（测试用 SQLite）直接跳过。
"""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import inspect, select, text

from core.db import engine
from domain.serial import patch_mutex

log = logging.getLogger("uvicorn.error")

ADDED = (
    ("evidence", "JSON NULL"),
    ("state", "VARCHAR(16) NOT NULL DEFAULT 'current'"),
    ("replaces", "VARCHAR(24) NULL"),
    ("signed_at", "DATETIME NULL"),
)


def _columns(conn, table):
    return {row[0] for row in conn.execute(text(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:t"), {"t": table})}


def _indexes(conn, table):
    return conn.execute(text(
        "SELECT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) cols "
        "FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:t "
        "UNIQUE AND NON_UNIQUE=0 GROUP BY INDEX_NAME"), {"t": table}).mappings().all()


def _upgrade_findings(conn):
    columns = _columns(conn, "feedback_findings")
    for name, ddl in ADDED:
        if name not in columns:
            conn.execute(text(f"ALTER TABLE feedback_findings ADD COLUMN {name} {ddl}"))
            log.info("schema: added feedback_findings.%s", name)
    for index in _indexes(conn, "feedback_findings"):
        if index["cols"] == "focus_window":
            conn.execute(text(f"ALTER TABLE feedback_findings DROP INDEX {index['INDEX_NAME']}"))
            log.info("schema: dropped unique index on focus_window")
    rows = conn.execute(text(
        "SELECT code, focus_window FROM feedback_findings WHERE evidence IS NULL OR signed_at IS NULL")).mappings().all()
    for row in rows:
        focus = conn.execute(text("SELECT * FROM sound_windows WHERE code=:c"),
                             {"c": row["focus_window"]}).mappings().first()
        evidence = []
        if focus:
            evidence = [r[0] for r in conn.execute(text(
                "SELECT code FROM sound_windows WHERE slot=:s AND channel=:ch AND revision=:r AND purpose='live'"),
                {"s": focus["slot"], "ch": focus["channel"], "r": focus["revision"]})]
        conn.execute(text("UPDATE feedback_findings SET evidence=:e, signed_at=COALESCE(signed_at,:n) WHERE code=:c"),
                     {"e": json.dumps(sorted(evidence)), "n": datetime.now(timezone.utc).replace(tzinfo=None),
                      "c": row["code"]})


def upgrade():
    with engine.begin() as conn:
        # 串行锁依赖这一行始终存在；SEED_DEMO 关闭时也要补上。
        if conn.execute(select(patch_mutex.c.code)).first() is None:
            conn.execute(patch_mutex.insert().values(code=1))
        if engine.dialect.name != "mysql":
            return
        inspector = inspect(engine)
        if "feedback_findings" not in inspector.get_table_names():
            return
        _upgrade_findings(conn)
