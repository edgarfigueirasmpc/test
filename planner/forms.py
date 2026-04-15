from django import forms
from django.contrib.auth import get_user_model

from .models import Project, ProjectAttachment, WorkLog, WorkLogAttachment

User = get_user_model()


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return [single_file_clean(data, initial)]


class ProjectForm(forms.ModelForm):
    attachments = MultipleFileField(required=False, label="adjuntos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ordered_users = User.objects.order_by("username")
        self.fields["requested_by"].queryset = ordered_users
        self.fields["assigned_users"].queryset = ordered_users

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        planned_start_date = cleaned_data.get("planned_start_date")

        if name and planned_start_date:
            duplicate_qs = Project.objects.filter(
                name__iexact=name.strip(),
                planned_start_date=planned_start_date,
            )
            if self.instance.pk:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
            if duplicate_qs.exists():
                raise forms.ValidationError(
                    "Ya existe un proyecto con ese nombre y fecha de inicio."
                )

        return cleaned_data

    def save_attachments(self, project):
        for uploaded_file in self.cleaned_data.get("attachments", []):
            ProjectAttachment.create_from_upload(project, uploaded_file)

    class Meta:
        model = Project
        fields = [
            "name",
            "description",
            "planned_start_date",
            "delivery_date",
            "requested_by",
            "assigned_users",
            "is_visible",
            "estimated_hours",
            "color",
            "status",
            "notes",
            "attachments",
        ]
        widgets = {
            "planned_start_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "delivery_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "color": forms.TextInput(attrs={"type": "color"}),
            "requested_by": forms.CheckboxSelectMultiple(),
            "assigned_users": forms.CheckboxSelectMultiple(),
        }


class WorkLogForm(forms.ModelForm):
    attachments = MultipleFileField(required=False, label="adjuntos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ordered_users = User.objects.order_by("username")
        self.fields["requested_by"].queryset = ordered_users
        self.fields["assigned_users"].queryset = ordered_users

    def save_attachments(self, work_log):
        for uploaded_file in self.cleaned_data.get("attachments", []):
            WorkLogAttachment.create_from_upload(work_log, uploaded_file)

    class Meta:
        model = WorkLog
        fields = [
            "date",
            "requested_by",
            "assigned_users",
            "work_type",
            "project",
            "description",
            "actual_hours",
            "notes",
            "attachments",
        ]
        widgets = {
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "requested_by": forms.CheckboxSelectMultiple(),
            "assigned_users": forms.CheckboxSelectMultiple(),
        }
