from sqlalchemy import Column,Integer,Table,select
from core.db import metadata

# 补录、签发、隔离与复位共用同一把串行锁：谁先取得锁谁先生效，
# 后到的一方必须在锁内看到前者已提交的同线同刻证据。
patch_mutex=Table("patch_serial",metadata,Column("code",Integer,primary_key=True))


def lock_patch(conn):
    conn.execute(select(patch_mutex).with_for_update()).first()
