from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planificado"
        IN_PROGRESS = "in_progress", "En progreso"
        COMPLETED = "completed", "Completado"

    name = models.CharField("nombre", max_length=200)
    description = models.TextField("descripcion", blank=True)
    planned_start_date = models.DateField("fecha de inicio")
    delivery_date = models.DateField("fecha de entrega", blank=True, null=True)
    requested_by = models.ManyToManyField(
        User,
        related_name="requested_projects",
        verbose_name="solicitado por",
        blank=True,
    )
    assigned_users = models.ManyToManyField(
        User,
        related_name="assigned_projects",
        verbose_name="usuarios asignados",
        blank=True,
    )
    color = models.CharField("color", max_length=7, default="#6b7280")
    is_visible = models.BooleanField("visible en calendario", default=True)
    estimated_hours = models.DecimalField(
        "horas estimadas",
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        "estado",
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    notes = models.TextField("observaciones", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["planned_start_date", "name"]
        verbose_name = "proyecto"
        verbose_name_plural = "proyectos"

    def __str__(self):
        return self.name


class ProjectTask(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planificada"
        IN_PROGRESS = "in_progress", "En progreso"
        BLOCKED = "blocked", "Bloqueada"
        COMPLETED = "completed", "Completada"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="proyecto",
    )
    name = models.CharField("nombre", max_length=200)
    description = models.TextField("descripcion", blank=True)
    order = models.PositiveIntegerField("orden", default=1)
    estimated_hours = models.DecimalField(
        "tiempo estimado (horas)",
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    planned_start_date = models.DateField("fecha prevista de inicio", blank=True, null=True)
    planned_end_date = models.DateField("fecha prevista de fin", blank=True, null=True)
    status = models.CharField(
        "estado",
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project__planned_start_date", "order", "id"]
        verbose_name = "parte de proyecto"
        verbose_name_plural = "partes de proyecto"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "order"],
                name="unique_project_task_order",
            )
        ]

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class WorkLog(models.Model):
    class WorkType(models.TextChoices):
        PROJECT = "project_work", "Trabajo de proyecto"
        OTHER = "other_work", "Trabajo no asociado a proyecto"

    date = models.DateField("fecha")
    requested_by = models.ManyToManyField(
        User,
        related_name="requested_work_logs",
        verbose_name="solicitado por",
        blank=True,
    )
    assigned_users = models.ManyToManyField(
        User,
        related_name="assigned_work_logs",
        verbose_name="usuarios que realizan",
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        related_name="work_logs",
        verbose_name="proyecto",
        blank=True,
        null=True,
    )
    task = models.ForeignKey(
        ProjectTask,
        on_delete=models.SET_NULL,
        related_name="work_logs",
        verbose_name="parte del proyecto",
        blank=True,
        null=True,
    )
    description = models.TextField("descripcion de lo realizado")
    actual_hours = models.DecimalField(
        "horas dedicadas",
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    work_type = models.CharField(
        "tipo de trabajo",
        max_length=20,
        choices=WorkType.choices,
        default=WorkType.PROJECT,
    )
    notes = models.TextField("observaciones", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "registro diario"
        verbose_name_plural = "registros diarios"

    def __str__(self):
        return f"{self.date} - {self.get_work_type_display()} ({self.actual_hours} h)"

    def clean(self):
        errors = {}

        if self.work_type == self.WorkType.PROJECT and not self.project:
            errors["project"] = "Selecciona un proyecto para el trabajo de proyecto."

        if self.work_type == self.WorkType.OTHER and self.project:
            errors["project"] = "El trabajo no asociado a proyecto debe guardarse sin proyecto."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.task and not self.project:
            self.project = self.task.project
        super().save(*args, **kwargs)


class PlannerSettings(models.Model):
    show_other_work = models.BooleanField("mostrar trabajo fuera de proyecto", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuracion del planificador"
        verbose_name_plural = "configuracion del planificador"

    def __str__(self):
        return "Configuracion del planificador"

    @classmethod
    def get_solo(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
