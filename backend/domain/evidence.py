from sqlalchemy import select
from domain.catalog import same_slot
from domain.interventions import findings,tickets
from domain.soundboard import windows
from domain.states import FindingState


def line_slot(conn,focus):
    """同一接线版本、同一线路、同一刻度的在播声检窗。"""
    return same_slot(conn,focus)


def codes(rows):
    """声检窗记录或已编码的编号列表，一律归并为排序后的编号集合。"""
    return sorted({row["code"] if isinstance(row,dict) else row for row in rows})


def ticket_of(conn,code):
    return conn.execute(select(tickets.c.code).where(tickets.c.finding==code)).scalar_one_or_none()


def affected(conn,focus):
    stmt=(select(findings).join(windows,windows.c.code==findings.c.focus_window)
          .where(windows.c.slot==focus["slot"],windows.c.channel==focus["channel"],
                 windows.c.revision==focus["revision"],windows.c.purpose=="live"))
    return [dict(row) for row in conn.execute(stmt).mappings()]


def reconcile(conn,focus):
    """补录后复判同线同刻已签诊断：未隔离转待复判，已隔离保留为改线依据。"""
    current=codes(line_slot(conn,focus))
    changed=[]
    for note in affected(conn,focus):
        if note["state"]!=FindingState.CURRENT or codes(note["evidence"] or [])==current:
            continue
        state=FindingState.RETAINED if ticket_of(conn,note["code"]) else FindingState.PENDING
        conn.execute(findings.update().where(findings.c.code==note["code"]).values(state=state))
        changed.append({"code":note["code"],"state":str(state)})
    return changed
