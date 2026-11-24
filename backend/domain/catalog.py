from fastapi import HTTPException
from sqlalchemy import select
from core.db import transaction
from domain.interventions import findings,tickets
from domain.soundboard import points,windows


def one(conn,table,code,lock=False):
    query=select(table).where(table.c.code==code)
    row=conn.execute(query.with_for_update() if lock else query).mappings().first()
    if row is None:
        raise HTTPException(404,f"没有编号为 {code} 的记录")
    return dict(row)


def query(conn,table,*filters):
    stmt=select(table).where(*filters).order_by(table.c.code.desc()).limit(160)
    return [dict(row) for row in conn.execute(stmt).mappings()]


def calibration(conn):
    return query(conn,windows,windows.c.purpose=="baseline")


def same_slot(conn,focus):
    """同一接线版本、同一线路、同一刻度的在播声检窗，用于证据快照。"""
    stmt=(select(windows).where(windows.c.slot==focus["slot"],windows.c.channel==focus["channel"],
          windows.c.revision==focus["revision"],windows.c.purpose=="live").order_by(windows.c.code))
    return [dict(row) for row in conn.execute(stmt).mappings()]


def latest(conn,point,purpose):
    stmt=select(windows).where(windows.c.point==point["code"],windows.c.revision==point["revision"],
                               windows.c.purpose==purpose).order_by(windows.c.slot.desc()).limit(1)
    row=conn.execute(stmt).mappings().first()
    return dict(row) if row else None


def patchboard():
    with transaction() as conn:
        return {"points":query(conn,points),"tickets":query(conn,tickets)}


def audio():
    with transaction() as conn:
        return query(conn,windows,windows.c.purpose!="baseline")


def diagnosis():
    with transaction() as conn:
        stmt=(select(findings,windows.c.point,windows.c.channel,windows.c.revision,windows.c.slot)
              .join(windows,windows.c.code==findings.c.focus_window)
              .order_by(windows.c.slot.desc(),findings.c.code.desc()).limit(160))
        return [dict(row) for row in conn.execute(stmt).mappings()]
