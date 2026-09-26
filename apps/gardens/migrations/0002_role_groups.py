"""角色组：主管（可删）与萎凋工（可建改、不可删）。

幂等：可重复执行（upgrade 场景由 post_migrate 信号补齐权限）。
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

# 与 apps.gardens.permissions 保持一致的组名常量
SUPERVISOR_GROUP = "主管"
WITHERER_GROUP = "萎凋工"

MODELS = ("garden", "trough", "witherbatch")
ACTIONS = ("add", "change", "view", "delete")


def _model_permissions(apps, using):
    """返回 {(model, action): Permission}。"""
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    cts = {
        m: ContentType.objects.using(using).get(
            app_label="gardens", model=m
        )
        for m in MODELS
    }
    return {
        (m, a): Permission.objects.using(using).get(
            content_type=cts[m], codename=f"{a}_{m}"
        )
        for m in MODELS
        for a in ACTIONS
    }


def sync_groups(apps, schema_editor):
    using = schema_editor.connection.alias

    # 全新 migrate 时本迁移在 post_migrate 之前执行，
    # 模型权限可能尚未生成，先强制补齐。
    app_config = global_apps.get_app_config("gardens")
    create_permissions(app_config, apps=apps, verbosity=0, using=using)

    Group = apps.get_model("auth", "Group")
    perms = _model_permissions(apps, using)

    supervisor, _ = Group.objects.using(using).get_or_create(
        name=SUPERVISOR_GROUP
    )
    witherer, _ = Group.objects.using(using).get_or_create(
        name=WITHERER_GROUP
    )

    # 主管：茶园/槽位/批次的增删改查全部权限
    supervisor.permissions.set(
        [perms[(m, a)] for m in MODELS for a in ACTIONS]
    )

    # 萎凋工：可新建、可编辑、可查看；明确不授 delete
    witherer.permissions.set(
        [perms[(m, a)] for m in MODELS for a in ("add", "change", "view")]
    )


def remove_groups(apps, schema_editor):
    using = schema_editor.connection.alias
    Group = apps.get_model("auth", "Group")
    Group.objects.using(using).filter(
        name__in=[SUPERVISOR_GROUP, WITHERER_GROUP]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gardens", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(sync_groups, remove_groups),
    ]
