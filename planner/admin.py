from django.contrib import admin
from django import forms

from .models import PlannerSettings, Project, WorkLog


class ProjectAdminForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = "__all__"
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
        }


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    form = ProjectAdminForm
    list_display = ("name", "planned_start_date", "delivery_date", "estimated_hours", "status", "is_visible", "color")
    list_filter = ("status", "is_visible")
    search_fields = ("name", "description", "notes")
    filter_horizontal = ("requested_by", "assigned_users")


@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ("date", "project", "work_type", "actual_hours")
    list_filter = ("work_type", "date", "project")
    search_fields = ("description", "notes", "project__name", "requested_by__username")
    autocomplete_fields = ("project",)
    filter_horizontal = ("requested_by", "assigned_users")
    date_hierarchy = "date"


@admin.register(PlannerSettings)
class PlannerSettingsAdmin(admin.ModelAdmin):
    list_display = ("show_other_work", "updated_at")
