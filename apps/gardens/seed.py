from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from .models import Garden, Trough, WitherBatch
from .permissions import SUPERVISOR_GROUP, WITHERER_GROUP

SEED_PASSWORD = "123456"


def _group(name):
    """按名取组；组尚未由迁移创建时返回 None，不阻塞播种。"""
    return Group.objects.filter(name=name).first()


def _ensure_user(username, **extra):
    """取或建用户；新建时正确哈希密码，并补齐/更新属性。"""
    User = get_user_model()
    password = extra.pop("password", SEED_PASSWORD)
    user = User.objects.filter(username=username).first()
    if user is None:
        user = User(username=username, **extra)
        user.set_password(password)
        user.save()
        return user
    changed = False
    for field, value in extra.items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed = True
    if not user.has_usable_password():
        user.set_password(password)
        changed = True
    if changed:
        user.save()
    return user


def ensure_seed_data():
    """幂等种子：账号/角色 + 样例茶园/槽位/批次。

    账号（密码均为 123456）：
    - admin：超级用户，等同主管，可删除茶园/槽位/批次；
    - supervisor：主管，可删除；
    - witherer：萎凋工，可建改、不可删除。

    茶园样例刻意保持“一园有槽、一园无槽”：
    - 云雾岭一号园：有 1 个槽位（带批次），删除须被拒；
    - 竹影台二号园：无槽位，主管可直接删除。
    """
    admin = _ensure_user(
        "admin",
        email="admin@teawither.local",
        password=SEED_PASSWORD,
        is_staff=True,
        is_superuser=True,
    )

    supervisor = _ensure_user(
        "supervisor",
        email="supervisor@teawither.local",
        password=SEED_PASSWORD,
    )
    supervisor_group = _group(SUPERVISOR_GROUP)
    if supervisor_group is not None:
        supervisor.groups.add(supervisor_group)

    witherer = _ensure_user(
        "witherer",
        email="witherer@teawither.local",
        password=SEED_PASSWORD,
    )
    witherer_group = _group(WITHERER_GROUP)
    if witherer_group is not None:
        # 萎凋工绝不能因历史数据而留在主管组
        if supervisor_group is not None:
            witherer.groups.remove(supervisor_group)
        witherer.groups.add(witherer_group)

    if Garden.objects.exists():
        return

    # g1：有槽的茶园
    g1 = Garden.objects.create(
        name="云雾岭一号园",
        altitudeBand="800-1000m",
        notes="向阳坡，晨雾较重",
    )
    # g2：无槽的茶园
    Garden.objects.create(
        name="竹影台二号园",
        altitudeBand="600-800m",
        notes="背风缓坡（暂未布置槽位）",
    )

    t1 = Trough.objects.create(
        garden=g1,
        troughCode="A-01",
        cultivar="福鼎大白",
        loadKg=Decimal("120.50"),
        status=Trough.STATUS_WITHERING,
    )
    WitherBatch.objects.create(
        trough=t1,
        startedAt=timezone.now() - timezone.timedelta(hours=18),
        targetMoisture=Decimal("38.00"),
        actualMoisture=Decimal("37.50"),
        rollGrade="一级",
    )
    t1.status = Trough.STATUS_READY
    t1.save()
