from fastapi import HTTPException
from sqlalchemy import select
from core.audit import record
from core.db import transaction
from domain.catalog import one
from domain.evidence import reconcile
from domain.serial import lock_patch
from domain.soundboard import points,windows
from domain.states import Patch


def capture(form,user):
    with transaction() as conn:
        lock_patch(conn)
        point=one(conn,points,form.point,lock=True)
        purpose="reline" if point["patch"]==Patch.ISOLATED else "live"
        duplicate=conn.execute(select(windows.c.code).where(
            windows.c.point==point["code"],windows.c.slot==form.slot,
            windows.c.revision==point["revision"])).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(409,"该麦位在此接线版本和刻度上已有声检窗")
        # 同一接线版本内允许补录早于最新窗的迟到记录：不比较时刻大小，
        # 只保证麦位、版本与刻度三元组唯一。
        item=dict(form.model_dump(),channel=point["channel"],revision=point["revision"],purpose=purpose)
        conn.execute(windows.insert().values(**item))
        later=conn.execute(select(windows.c.slot).where(
            windows.c.point==point["code"],windows.c.revision==point["revision"],
            windows.c.slot>form.slot)).first()
        # 只有主路试听会改变同期同频证据；复线试音不参与主路判别。
        changed=reconcile(conn,item) if purpose=="live" else []
        record(conn,user,f"audio:{form.code}:{purpose}"+(":late" if later is not None else ""))
        return {**one(conn,windows,form.code),"late":later is not None,"reconciled":changed}
