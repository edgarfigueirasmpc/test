from django.contrib import admin

from .models import Project, ProjectTask, WorkLog


class ProjectTaskInline(admin.TabularInline):
    model = ProjectTask
    extra = 1
    fields = (
        "order",
        "name",
        "estimated_hours",
        "planned_start_date",
        "planned_end_date",
        "status",
    )
    ordering = ("order",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "planned_start_date", "status", "priority")
    list_filter = ("status", "priority")
    search_fields = ("name", "description", "notes")
    inlines = [ProjectTaskInline]


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "order", "estimated_hours", "status")
    list_filter = ("status", "project")
    search_fields = ("name", "description", "project__name")
    ordering = ("project__planned_start_date", "project__name", "order")


@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ("date", "project", "task", "work_type", "actual_hours")
    list_filter = ("work_type", "date", "project")
    search_fields = ("description", "notes", "project__name", "task__name")
    autocomplete_fields = ("project", "task")
    date_hierarchy = "date"
