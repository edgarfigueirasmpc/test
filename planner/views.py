from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import ProjectForm, WorkLogForm
from .models import PlannerSettings, Project, WorkLog
from .services import build_timeline_context


@require_http_methods(["GET", "POST"])
def index(request):
    scale = request.GET.get("scale", "month")
    if scale not in {"day", "month", "year"}:
        scale = "month"
    selected_date = request.GET.get("date")
    edit_project = None

    edit_entry = None
    edit_id = request.GET.get("edit")
    if edit_id:
        edit_entry = get_object_or_404(WorkLog.objects.select_related("project"), pk=edit_id)
    edit_project_id = request.GET.get("edit_project")
    if edit_project_id:
        edit_project = get_object_or_404(Project, pk=edit_project_id)

    if request.method == "POST":
        scale = request.POST.get("scale", scale)
        form_type = request.POST.get("form_type", "worklog")

        if form_type == "toggle_project_visibility":
            visibility_scope = request.POST.get("visibility_scope", "project")
            visible_value = request.POST.get("is_visible", "true").lower() == "true"

            if visibility_scope == "other_work":
                settings = PlannerSettings.get_solo()
                settings.show_other_work = visible_value
                settings.save(update_fields=["show_other_work", "updated_at"])
                return JsonResponse({"ok": True, "scope": "other_work", "isVisible": settings.show_other_work})

            project = get_object_or_404(Project, pk=request.POST.get("project_id"))
            project.is_visible = visible_value
            project.save(update_fields=["is_visible"])
            return JsonResponse({"ok": True, "scope": "project", "projectId": project.pk, "isVisible": project.is_visible})
        elif form_type == "project":
            project_id = request.POST.get("project_id")
            project_instance = None
            if project_id:
                project_instance = get_object_or_404(Project, pk=project_id)

            project_form = ProjectForm(request.POST, instance=project_instance)
            worklog_initial = {}
            if selected_date:
                worklog_initial["date"] = selected_date
            worklog_form = WorkLogForm(initial=worklog_initial)

            if project_form.is_valid():
                project_form.save()
                messages.success(request, "Proyecto guardado correctamente.")
                if scale == "month":
                    return redirect("planner:index")
                return redirect(f"{reverse('planner:index')}?scale={scale}")
            edit_project = project_instance
        else:
            entry_id = request.POST.get("entry_id")
            instance = None
            if entry_id:
                instance = get_object_or_404(WorkLog, pk=entry_id)
            worklog_form = WorkLogForm(request.POST, instance=instance)
            project_form = ProjectForm(instance=edit_project)
            if worklog_form.is_valid():
                worklog_form.save()
                messages.success(request, "Registro guardado correctamente.")
                if scale == "month":
                    return redirect("planner:index")
                return redirect(f"{reverse('planner:index')}?scale={scale}")
            edit_entry = instance
    else:
        initial = {}
        if selected_date and not edit_entry:
            initial["date"] = selected_date
        worklog_form = WorkLogForm(instance=edit_entry, initial=initial)
        project_form = ProjectForm(instance=edit_project)

    context = build_timeline_context(scale=scale)
    context.update(
        {
            "form": worklog_form,
            "project_form": project_form,
            "edit_entry": edit_entry,
            "edit_project": edit_project,
            "scale": scale,
            "selected_date": selected_date,
            "show_form_modal": bool(edit_entry or worklog_form.errors),
            "show_project_modal": bool(edit_project or project_form.errors),
            "recent_logs": WorkLog.objects.select_related("project").prefetch_related("requested_by", "assigned_users")[:15],
        }
    )
    return render(request, "planner/index.html", context)
