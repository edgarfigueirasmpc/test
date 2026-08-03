from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

from .models import Project, ProjectAttachment, ProjectTask, WorkLog, WorkLogAttachment

User = get_user_model()


def build_user_choices():
    """Lista de opciones de usuario lista para reutilizar entre formularios.

    Cada campo con CheckboxSelectMultiple evalua su queryset al renderizarse, asi
    que sin esto la portada lanza una consulta a auth_user por cada uno de los
    cuatro campos de usuario.
    """
    return [(user.pk, str(user)) for user in User.objects.order_by("username")]


def _apply_user_choices(form, field_names, user_choices):
    ordered_users = User.objects.order_by("username")
    for field_name in field_names:
        field = form.fields[field_name]
        # El queryset sigue haciendo falta para validar el POST; es perezoso y no
        # consulta nada mientras nadie lo recorra.
        field.queryset = ordered_users
        if user_choices is not None:
            field.choices = user_choices


class StaffLoginForm(forms.Form):
    username = forms.CharField(label="Usuario", max_length=150)
    password = forms.CharField(label="Contrasena", widget=forms.PasswordInput)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if username and password:
            self.user = authenticate(
                self.request,
                username=username,
                password=password,
            )
            if self.user is None:
                raise forms.ValidationError("Usuario o contrasena incorrectos.")
            if not self.user.is_active or not self.user.is_staff:
                raise forms.ValidationError("Este usuario no tiene acceso a la aplicacion.")

        return cleaned_data


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

    def __init__(self, *args, user_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_user_choices(self, ("requested_by", "assigned_users"), user_choices)

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

    def __init__(self, *args, user_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_user_choices(self, ("requested_by", "assigned_users"), user_choices)
        self.fields["task"].queryset = ProjectTask.objects.select_related("project").order_by(
            "project__planned_start_date",
            "project__name",
            "order",
            "name",
        )

    def clean(self):
        cleaned_data = super().clean()
        task = cleaned_data.get("task")
        project = cleaned_data.get("project")

        if task and not project:
            cleaned_data["project"] = task.project
            self.instance.project = task.project
        elif task and project and task.project_id != project.id:
            self.add_error(
                "task",
                "La parte seleccionada pertenece a otro proyecto.",
            )

        return cleaned_data

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
            "task",
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
