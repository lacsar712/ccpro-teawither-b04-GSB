"""角色与删除权限集中定义。

角色矩阵（详见 README）：

| 操作                | 萎凋工 (witherer) | 主管 (supervisor) |
|---------------------|-------------------|-------------------|
| 查看                | ✔                 | ✔                 |
| 新建茶园/槽位/批次  | ✔                 | ✔                 |
| 编辑茶园/槽位/批次  | ✔                 | ✔                 |
| 删除茶园/槽位/批次  | ✘                 | ✔                 |

删除约束（后端强制，前端仅展示）：

- 茶园下仍有萎凋槽时，禁止删除茶园（views.ProtectedDeleteView）；
- 萎凋槽下仍有批次时，禁止删除槽位（须先删除其全部批次）；
- 批次为最末端记录，可直接删除。
"""

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.http import HttpResponseForbidden
from django.shortcuts import render

#: 组名
SUPERVISOR_GROUP = "主管"
WITHERER_GROUP = "萎凋工"

#: 萎凋工访问删除入口时的统一中文说明
DELETE_DENIED_MESSAGE = (
    "权限不足：仅主管可以删除茶园、萎凋槽和萎凋批次。"
    "萎凋工可以新建和编辑这些记录，但不能删除；如需删除，请联系主管操作。"
)


def is_supervisor(user):
    """超级用户或属于「主管」组视为可删除数据。"""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=SUPERVISOR_GROUP).exists()


def render_denied(request, message=DELETE_DENIED_MESSAGE):
    """渲染中文 403 页。

    不依赖 ``handler403``——DEBUG 模式下 Django 不会使用自定义错误页，
    故由视图直接返回本响应，保证任何环境下都显示中文说明。
    """
    return HttpResponseForbidden(
        render(
            request,
            "403.html",
            {"message": message},
        ).content
    )


class DeletePermissionRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """删除类视图统一入口：登录 + 仅主管（含超级用户）可访问。

    - 未登录：跳转登录页（登录鉴权保持，不绕过）；
    - 萎凋工无论 GET 确认页还是 POST 提交删除，都得到 403 中文页，
      避免“只藏按钮、后端仍可删”。
    """

    def test_func(self):
        return is_supervisor(self.request.user)

    def get_permission_denied_message(self):
        return DELETE_DENIED_MESSAGE

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            # 已登录但角色不够：中文 403 页（不用 raise，避免 DEBUG 调试页）
            return render_denied(
                self.request, self.get_permission_denied_message()
            )
        # 未登录：走 AccessMixin 默认逻辑，重定向到 LOGIN_URL（?next=...）
        return super().handle_no_permission()
