from datetime import datetime, timezone

from fastapi import HTTPException
from core.audit import record
from core.db import transaction
from core.queueing import result,submit
from domain.catalog import calibration,one,same_slot
from domain.evidence import codes,line_slot
from domain.interventions import findings
from domain.serial import lock_patch
from domain.soundboard import points,windows
from domain.states import FindingState,Patch


def stamp():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sound_snapshot(conn,focus):
    simultaneous=same_slot(conn,focus)
    return {"focus":focus,"baseline":calibration(conn),"simultaneous":simultaneous,
            "evidence":codes(simultaneous)}


def diagnose(form,user):
    with transaction() as conn:
        focus=one(conn,windows,form.window)
        point=one(conn,points,focus["point"])
        if focus["purpose"]!="live" or point["patch"]!=Patch.LIVE:
            raise HTTPException(409,"仅在播窗口用于判别；隔离后的试音须到复线页")
        return submit(user,{"kind":"diagnosis",**sound_snapshot(conn,focus)})


def save(form,user):
    computation=result(user,form.token)
    captured=computation["input"]
    rating=computation["result"]
    if captured["kind"]!="diagnosis":
        raise HTTPException(409,"请使用原始诊断凭证签入发现")
    focus=captured["focus"]
    with transaction() as conn:
        lock_patch(conn)
        point=one(conn,points,focus["point"],lock=True)
        if point["patch"]!=Patch.LIVE or point["revision"]!=focus["revision"]:
            raise HTTPException(409,"该声检窗口属于旧接线版本")
        if one(conn,windows,focus["code"])["purpose"]!="live":
            raise HTTPException(409,"该声检窗口已不是主路试听")
        # 补录一旦提交，锁内看到的证据集合就已改变；旧凭证不能再签发。
        current=codes(line_slot(conn,focus))
        if current!=codes(captured.get("evidence",[])):
            raise HTTPException(409,"同期同频证据有新增，请重新判别")
        history=[dict(row) for row in conn.execute(
            findings.select().where(findings.c.focus_window==focus["code"])
            .with_for_update()).mappings()]
        live=[row for row in history if row["state"]!=FindingState.SUPERSEDED]
        if any(row["state"]!=FindingState.PENDING for row in live):
            raise HTTPException(409,"该声检窗口已有有效的当前结论，请刷新后处理")
        replaces=live[0]["code"] if live else None
        if replaces:
            conn.execute(findings.update().where(findings.c.code==replaces)
                         .values(state=FindingState.SUPERSEDED))
        conn.execute(findings.insert().values(code=form.code,focus_window=focus["code"],category=rating["category"],
                    score=rating["score"],neighbors=rating["neighbors"],shared_points=rating["shared_points"],
                    evidence=current,state=FindingState.CURRENT,replaces=replaces,signed_at=stamp(),
                    reviewed_by=user["sub"],compute_token=form.token))
        record(conn,user,f"finding:{form.code}:{rating['category']}"+(f":rejudge:{replaces}" if replaces else ""))
        return one(conn,findings,form.code)
