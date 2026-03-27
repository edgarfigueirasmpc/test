from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planificado"
        IN_PROGRESS = "in_progress", "En progreso"
        BLOCKED = "blocked", "Bloqueado"
        COMPLETED = "completed", "Completado"

    class Priority(models.IntegerChoices):
        LOW = 1, "Baja"
        MEDIUM = 2, "Media"
        HIGH = 3, "Alta"

    name = models.CharField("nombre", max_length=200)
    description = models.TextField("descripcion", blank=True)
    planned_start_date = models.DateField("fecha de inicio prevista")
    status = models.CharField(
        "estado",
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    priority = models.PositiveSmallIntegerField(
        "prioridad",
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    notes = models.TextField("observaciones", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["planned_start_date", "-priority", "name"]
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
        EXTERNAL = "external_task", "Tarea externa"
        INTERRUPTION = "interruption", "Interrupcion"
        MAINTENANCE = "maintenance", "Mantenimiento"
        OTHER = "other", "Otros"

    date = models.DateField("fecha")
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
        "tiempo real invertido (horas)",
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

        if self.task and self.project and self.task.project_id != self.project_id:
            errors["task"] = "La parte seleccionada no pertenece al proyecto indicado."

        if self.task and self.work_type != self.WorkType.PROJECT:
            errors["work_type"] = "Solo se puede asignar una parte a trabajo de proyecto."

        if self.work_type == self.WorkType.PROJECT and not self.project and not self.task:
            errors["project"] = "Indica un proyecto o una parte para el trabajo de proyecto."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.task and not self.project:
            self.project = self.task.project
        super().save(*args, **kwargs)
