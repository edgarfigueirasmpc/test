from django import forms

from .models import ProjectTask, WorkLog


class TaskChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.project.name} / {obj.order}. {obj.name}"


class WorkLogForm(forms.ModelForm):
    task = TaskChoiceField(
        queryset=ProjectTask.objects.select_related("project").order_by(
            "project__planned_start_date",
            "project__name",
            "order",
        ),
        required=False,
        label="Parte del proyecto",
    )

    class Meta:
        model = WorkLog
        fields = [
            "date",
            "project",
            "task",
            "description",
            "actual_hours",
            "work_type",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        task = cleaned_data.get("task")
        project = cleaned_data.get("project")

        if task and not project:
            cleaned_data["project"] = task.project
            self.instance.project = task.project

        return cleaned_data
