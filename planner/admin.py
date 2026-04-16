from django.contrib import admin
from django import forms
from django.utils.html import format_html, format_html_join

from .models import (
    PlannerSettings,
    Project,
    ProjectAttachment,
    WorkLog,
    WorkLogAttachment,
)


class ProjectAdminForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = "__all__"
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
        }


class AttachmentAdminForm(forms.ModelForm):
    upload = forms.FileField(label="archivo", required=False)

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk and not cleaned_data.get("upload"):
            raise forms.ValidationError("Selecciona un archivo para crear el adjunto.")
        return cleaned_data


class ProjectAttachmentAdminForm(AttachmentAdminForm):
    class Meta:
        model = ProjectAttachment
        fields = ("project", "upload")

    def save(self, commit=True):
        upload = self.cleaned_data.get("upload")
        if upload:
            if self.instance.pk:
                raise forms.ValidationError(
                    "Edita los metadatos desde Cloudinary o crea un nuevo adjunto."
                )
            return ProjectAttachment.create_from_upload(self.cleaned_data["project"], upload)
        return super().save(commit=commit)


class WorkLogAttachmentAdminForm(AttachmentAdminForm):
    class Meta:
        model = WorkLogAttachment
        fields = ("work_log", "upload")

    def save(self, commit=True):
        upload = self.cleaned_data.get("upload")
        if upload:
            if self.instance.pk:
                raise forms.ValidationError(
                    "Edita los metadatos desde Cloudinary o crea un nuevo adjunto."
                )
            return WorkLogAttachment.create_from_upload(self.cleaned_data["work_log"], upload)
        return super().save(commit=commit)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    form = ProjectAdminForm
    list_display = ("name", "planned_start_date", "delivery_date", "estimated_hours", "status", "is_visible", "attachments_total", "color")
    list_filter = ("status", "is_visible")
    search_fields = ("name", "description", "notes")
    filter_horizontal = ("requested_by", "assigned_users")
    readonly_fields = ("attachments_preview",)

    def attachments_total(self, obj):
        return obj.attachments.count()

    attachments_total.short_description = "adjuntos"

    def attachments_preview(self, obj):
        if not obj.pk:
            return "Guarda el proyecto para poder ver o anadir adjuntos."
        attachments = obj.attachments.all()
        if not attachments:
            return "Sin adjuntos"
        return format_html_join(
            "<br>",
            '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
            ((attachment.file_url, attachment.original_filename) for attachment in attachments),
        )

    attachments_preview.short_description = "adjuntos"


@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ("date", "project", "work_type", "actual_hours", "attachments_total")
    list_filter = ("work_type", "date", "project")
    search_fields = ("description", "notes", "project__name", "requested_by__username")
    autocomplete_fields = ("project",)
    filter_horizontal = ("requested_by", "assigned_users")
    date_hierarchy = "date"
    readonly_fields = ("attachments_preview",)

    def attachments_total(self, obj):
        return obj.attachments.count()

    attachments_total.short_description = "adjuntos"

    def attachments_preview(self, obj):
        if not obj.pk:
            return "Guarda el registro para poder ver o anadir adjuntos."
        attachments = obj.attachments.all()
        if not attachments:
            return "Sin adjuntos"
        return format_html_join(
            "<br>",
            '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
            ((attachment.file_url, attachment.original_filename) for attachment in attachments),
        )

    attachments_preview.short_description = "adjuntos"


@admin.register(ProjectAttachment)
class ProjectAttachmentAdmin(admin.ModelAdmin):
    form = ProjectAttachmentAdminForm
    list_display = ("original_filename", "project", "file_size", "created_at", "open_file")
    list_filter = ("created_at", "project")
    search_fields = ("original_filename", "project__name", "cloudinary_public_id")
    readonly_fields = (
        "original_filename",
        "cloudinary_public_id",
        "cloudinary_resource_type",
        "file_format",
        "file_size",
        "file_url",
        "created_at",
    )

    def get_fields(self, request, obj=None):
        base_fields = ["project", "upload"]
        if obj:
            base_fields.extend(self.readonly_fields)
        return base_fields

    def open_file(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">Abrir</a>',
            obj.file_url,
        )

    open_file.short_description = "archivo"


@admin.register(WorkLogAttachment)
class WorkLogAttachmentAdmin(admin.ModelAdmin):
    form = WorkLogAttachmentAdminForm
    list_display = ("original_filename", "work_log", "file_size", "created_at", "open_file")
    list_filter = ("created_at",)
    search_fields = ("original_filename", "work_log__description", "cloudinary_public_id")
    readonly_fields = (
        "original_filename",
        "cloudinary_public_id",
        "cloudinary_resource_type",
        "file_format",
        "file_size",
        "file_url",
        "created_at",
    )

    def get_fields(self, request, obj=None):
        base_fields = ["work_log", "upload"]
        if obj:
            base_fields.extend(self.readonly_fields)
        return base_fields

    def open_file(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">Abrir</a>',
            obj.file_url,
        )

    open_file.short_description = "archivo"


@admin.register(PlannerSettings)
class PlannerSettingsAdmin(admin.ModelAdmin):
    list_display = ("show_other_work", "updated_at")
