from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import WorkLogForm
from .models import WorkLog
from .services import build_timeline_context


@require_http_methods(["GET", "POST"])
def index(request):
    edit_entry = None
    edit_id = request.GET.get("edit")
    if edit_id:
        edit_entry = get_object_or_404(WorkLog.objects.select_related("project", "task"), pk=edit_id)

    if request.method == "POST":
        entry_id = request.POST.get("entry_id")
        instance = None
        if entry_id:
            instance = get_object_or_404(WorkLog, pk=entry_id)
        form = WorkLogForm(request.POST, instance=instance)
        if form.is_valid():
            work_log = form.save()
            messages.success(request, "Registro guardado correctamente.")
            return redirect("planner:index")
        edit_entry = instance
    else:
        form = WorkLogForm(instance=edit_entry)

    context = build_timeline_context()
    context.update(
        {
            "form": form,
            "edit_entry": edit_entry,
            "show_form_modal": bool(edit_entry or form.errors),
            "recent_logs": WorkLog.objects.select_related("project", "task")[:15],
        }
    )
    return render(request, "planner/index.html", context)
