from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from .forms import GardenForm, TroughForm, WitherBatchForm
from .models import Garden, Trough, WitherBatch


def _wants_htmx(request):
    return request.headers.get("HX-Request") == "true"


class SupervisorDeleteMixin:
    """删除操作仅主管可用。

    萎凋工（无 delete 权限）访问任一删除入口（GET 确认页或 POST）都会被
    拒绝并收到中文说明，重定向回对应列表页。三个删除入口共用此 mixin，
    保证规则一致。需与 LoginRequiredMixin 连用（登录鉴权不关闭）。
    """

    delete_permission = None
    list_url_name = None

    def dispatch(self, request, *args, **kwargs):
        if self.delete_permission and not request.user.has_perm(
            self.delete_permission
        ):
            messages.error(
                request,
                "仅主管可执行删除操作；萎凋工可新建和修改，"
                "但不能删除茶园、萎凋槽与批次。",
            )
            return redirect(self.list_url_name)
        return super().dispatch(request, *args, **kwargs)


@login_required
def home(request):
    context = {
        "garden_count": Garden.objects.count(),
        "trough_count": Trough.objects.count(),
        "batch_count": WitherBatch.objects.count(),
        "ready_count": Trough.objects.filter(status=Trough.STATUS_READY).count(),
        "withering_count": Trough.objects.filter(
            status=Trough.STATUS_WITHERING
        ).count(),
        "loading_count": Trough.objects.filter(
            status=Trough.STATUS_LOADING
        ).count(),
    }
    return render(request, "home.html", context)


# ---- Garden ----


class GardenListView(LoginRequiredMixin, ListView):
    model = Garden
    template_name = "gardens/list.html"
    context_object_name = "gardens"

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        if _wants_htmx(request):
            html = render_to_string(
                "gardens/_table.html",
                {"gardens": self.object_list},
                request=request,
            )
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)


class GardenCreateView(LoginRequiredMixin, CreateView):
    model = Garden
    form_class = GardenForm
    template_name = "gardens/form.html"
    success_url = reverse_lazy("garden_list")

    def form_valid(self, form):
        messages.success(self.request, "茶园已创建")
        response = super().form_valid(form)
        if _wants_htmx(self.request):
            return redirect("garden_list")
        return response


class GardenUpdateView(LoginRequiredMixin, UpdateView):
    model = Garden
    form_class = GardenForm
    template_name = "gardens/form.html"
    success_url = reverse_lazy("garden_list")

    def form_valid(self, form):
        messages.success(self.request, "茶园已更新")
        return super().form_valid(form)


class GardenDeleteView(LoginRequiredMixin, SupervisorDeleteMixin, DeleteView):
    model = Garden
    template_name = "gardens/confirm_delete.html"
    success_url = reverse_lazy("garden_list")
    delete_permission = "gardens.delete_garden"
    list_url_name = "garden_list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["child_count"] = self.object.troughs.count()
        return context

    def form_valid(self, form):
        # 删除茶园前必须检查槽位：仍有槽则拒绝，不做级联删除。
        trough_count = self.object.troughs.count()
        if trough_count:
            messages.error(
                self.request,
                f"无法删除茶园「{self.object.name}」：其下仍有 "
                f"{trough_count} 个萎凋槽，请先删除全部槽位后再删除茶园。",
            )
            return redirect("garden_list")
        messages.success(self.request, "茶园已删除")
        return super().form_valid(form)


# ---- Trough ----


class TroughListView(LoginRequiredMixin, ListView):
    model = Trough
    template_name = "troughs/list.html"
    context_object_name = "troughs"

    def get_queryset(self):
        return Trough.objects.select_related("garden").all()

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        if _wants_htmx(request):
            html = render_to_string(
                "troughs/_table.html",
                {"troughs": self.object_list},
                request=request,
            )
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)


class TroughCreateView(LoginRequiredMixin, CreateView):
    model = Trough
    form_class = TroughForm
    template_name = "troughs/form.html"
    success_url = reverse_lazy("trough_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋槽已创建")
        return super().form_valid(form)


class TroughUpdateView(LoginRequiredMixin, UpdateView):
    model = Trough
    form_class = TroughForm
    template_name = "troughs/form.html"
    success_url = reverse_lazy("trough_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋槽已更新")
        return super().form_valid(form)


class TroughDeleteView(LoginRequiredMixin, SupervisorDeleteMixin, DeleteView):
    model = Trough
    template_name = "troughs/confirm_delete.html"
    success_url = reverse_lazy("trough_list")
    delete_permission = "gardens.delete_trough"
    list_url_name = "trough_list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["child_count"] = self.object.batches.count()
        return context

    def form_valid(self, form):
        # 删除槽位前必须检查批次：仍有批次则拒绝，不做级联删除。
        batch_count = self.object.batches.count()
        if batch_count:
            messages.error(
                self.request,
                f"无法删除萎凋槽「{self.object}」：其下仍有 "
                f"{batch_count} 个萎凋批次，请先删除全部批次后再删除槽位。",
            )
            return redirect("trough_list")
        messages.success(self.request, "萎凋槽已删除")
        return super().form_valid(form)


# ---- WitherBatch ----


class BatchListView(LoginRequiredMixin, ListView):
    model = WitherBatch
    template_name = "batches/list.html"
    context_object_name = "batches"

    def get_queryset(self):
        return WitherBatch.objects.select_related("trough", "trough__garden").all()

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        if _wants_htmx(request):
            html = render_to_string(
                "batches/_table.html",
                {"batches": self.object_list},
                request=request,
            )
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)


class BatchCreateView(LoginRequiredMixin, CreateView):
    model = WitherBatch
    form_class = WitherBatchForm
    template_name = "batches/form.html"
    success_url = reverse_lazy("batch_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋批次已创建")
        return super().form_valid(form)


class BatchUpdateView(LoginRequiredMixin, UpdateView):
    model = WitherBatch
    form_class = WitherBatchForm
    template_name = "batches/form.html"
    success_url = reverse_lazy("batch_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋批次已更新")
        return super().form_valid(form)


class BatchDeleteView(LoginRequiredMixin, SupervisorDeleteMixin, DeleteView):
    model = WitherBatch
    template_name = "batches/confirm_delete.html"
    success_url = reverse_lazy("batch_list")
    delete_permission = "gardens.delete_witherbatch"
    list_url_name = "batch_list"

    def form_valid(self, form):
        messages.success(self.request, "萎凋批次已删除")
        return super().form_valid(form)
