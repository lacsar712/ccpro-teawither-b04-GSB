from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils import timezone

from .models import Garden, Trough, WitherBatch

SUPERVISOR_GROUP = "主管"
WITHERER_GROUP = "萎凋工"

_MODEL_PERMS = {
    "garden": ["add", "change", "delete", "view"],
    "trough": ["add", "change", "delete", "view"],
    "witherbatch": ["add", "change", "delete", "view"],
}


def _perms(*codenames):
    return Permission.objects.filter(
        content_type__app_label="gardens", codename__in=codenames
    )


def ensure_roles():
    """创建角色组并授权（幂等）：

    - 主管：茶园/萎凋槽/批次的增删改查全部权限（含删除）。
    - 萎凋工：可新建、修改、查看三者，但没有任何删除权限。
    """
    supervisor, _ = Group.objects.get_or_create(name=SUPERVISOR_GROUP)
    all_perms = [
        f"{action}_{model}"
        for model, actions in _MODEL_PERMS.items()
        for action in actions
    ]
    supervisor.permissions.set(_perms(*all_perms))

    witherer, _ = Group.objects.get_or_create(name=WITHERER_GROUP)
    write_perms = [
        f"{action}_{model}"
        for model, actions in _MODEL_PERMS.items()
        for action in actions
        if action != "delete"
    ]
    witherer.permissions.set(_perms(*write_perms))
    return supervisor, witherer


def ensure_seed_data():
    """Idempotent seed: users + roles + sample gardens/troughs/batches."""
    User = get_user_model()

    supervisor_group, witherer_group = ensure_roles()

    admin = User.objects.filter(username="admin").first()
    if admin is None:
        admin = User.objects.create_superuser(
            "admin", "admin@teawither.local", "123456"
        )
    admin.groups.add(supervisor_group)

    witherer = User.objects.filter(username="witherer").first()
    if witherer is None:
        witherer = User.objects.create_user(
            "witherer", "witherer@teawither.local", "123456"
        )
    witherer.groups.add(witherer_group)

    if Garden.objects.exists():
        return

    # 一园有槽（云雾岭一号园），一园无槽（竹影台二号园），
    # 用于演示「有槽茶园不可删除、无槽茶园可删除」。
    g1 = Garden.objects.create(
        name="云雾岭一号园",
        altitudeBand="800-1000m",
        notes="向阳坡，晨雾较重",
    )
    g2 = Garden.objects.create(
        name="竹影台二号园",
        altitudeBand="600-800m",
        notes="背风缓坡，新垦待配槽",
    )

    t1 = Trough.objects.create(
        garden=g1,
        troughCode="A-01",
        cultivar="福鼎大白",
        loadKg=Decimal("120.50"),
        status=Trough.STATUS_WITHERING,
    )
    t2 = Trough.objects.create(
        garden=g1,
        troughCode="A-02",
        cultivar="铁观音",
        loadKg=Decimal("95.00"),
        status=Trough.STATUS_LOADING,
    )
    t3 = Trough.objects.create(
        garden=g1,
        troughCode="A-03",
        cultivar="黄金芽",
        loadKg=Decimal("88.25"),
        status=Trough.STATUS_WITHERING,
    )

    now = timezone.now()
    WitherBatch.objects.create(
        trough=t1,
        startedAt=now - timezone.timedelta(hours=18),
        targetMoisture=Decimal("38.00"),
        actualMoisture=Decimal("37.50"),
        rollGrade="一级",
    )
    WitherBatch.objects.create(
        trough=t2,
        startedAt=now - timezone.timedelta(hours=2),
        targetMoisture=Decimal("40.00"),
        actualMoisture=None,
        rollGrade="待评",
    )
    WitherBatch.objects.create(
        trough=t3,
        startedAt=now - timezone.timedelta(hours=30),
        targetMoisture=Decimal("36.00"),
        actualMoisture=Decimal("42.00"),
        rollGrade="二级",
    )

    # Ready trough with valid moisture
    t4 = Trough.objects.create(
        garden=g1,
        troughCode="A-04",
        cultivar="龙井43",
        loadKg=Decimal("110.00"),
        status=Trough.STATUS_WITHERING,
    )
    WitherBatch.objects.create(
        trough=t4,
        startedAt=now - timezone.timedelta(hours=24),
        targetMoisture=Decimal("35.00"),
        actualMoisture=Decimal("34.80"),
        rollGrade="特级",
    )
    t4.status = Trough.STATUS_READY
    t4.save()
