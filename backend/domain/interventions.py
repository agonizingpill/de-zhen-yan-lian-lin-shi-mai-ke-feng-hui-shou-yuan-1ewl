from sqlalchemy import CheckConstraint,Column,DateTime,Float,ForeignKey,Integer,JSON,String,Table
from core.db import metadata

findings = Table(
    "feedback_findings",metadata,
    Column("code",String(24),primary_key=True),
    Column("focus_window",String(24),ForeignKey("sound_windows.code"),nullable=False),
    Column("category",String(16),nullable=False),
    Column("score",Float,nullable=False),
    Column("neighbors",Integer,nullable=False),
    Column("shared_points",JSON,nullable=False),
    # 签发时的同期同频证据快照。补录使证据集合改变后，旧快照不再匹配，
    # 该诊断既不能再次签发，也不能用于隔离。
    Column("evidence",JSON,nullable=False),
    Column("state",String(16),nullable=False,default="current"),
    # 复判重签的新发现指向它所替代的旧结论，保留完整沿革。
    Column("replaces",String(24),ForeignKey("feedback_findings.code"),unique=True),
    Column("signed_at",DateTime,nullable=False),
    Column("reviewed_by",String(80),nullable=False),
    Column("compute_token",String(32),nullable=False,unique=True),
    CheckConstraint("category IN ('local','coordinated','normal')"),
    CheckConstraint("state IN ('current','pending','superseded','retained')"),
)

tickets = Table(
    "channel_tickets",metadata,
    Column("code",String(24),primary_key=True),
    Column("point",String(20),ForeignKey("microphone_points.code"),nullable=False),
    Column("finding",String(24),ForeignKey("feedback_findings.code"),nullable=False,unique=True),
    Column("old_channel",String(12),nullable=False),
    Column("new_channel",String(12),nullable=False),
    Column("reline_window",String(24),ForeignKey("sound_windows.code"),unique=True),
    Column("test_score",Float),
    Column("state",String(16),nullable=False),
    Column("isolated_by",String(80),nullable=False),
    Column("restored_by",String(80)),
    CheckConstraint("old_channel <> new_channel"),
    CheckConstraint("state IN ('isolated','restored')"),
)
