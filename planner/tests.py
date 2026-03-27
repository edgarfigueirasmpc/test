from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Project, ProjectTask, WorkLog
from .services import build_timeline_context


class WorkLogModelTests(TestCase):
    def test_task_must_belong_to_selected_project(self):
        project = Project.objects.create(
            name="Proyecto A",
            planned_start_date="2026-03-23",
        )
        other_project = Project.objects.create(
            name="Proyecto B",
            planned_start_date="2026-03-24",
        )
        task = ProjectTask.objects.create(
            project=project,
            name="Fase 1",
            order=1,
            estimated_hours=Decimal("4.00"),
        )

        work_log = WorkLog(
            date="2026-03-23",
            project=other_project,
            task=task,
            description="Trabajo invalido",
            actual_hours=Decimal("2.00"),
            work_type=WorkLog.WorkType.PROJECT,
        )

        with self.assertRaises(ValidationError):
            work_log.full_clean()


class TimelineServiceTests(TestCase):
    def test_external_work_shifts_projected_schedule(self):
        project = Project.objects.create(
            name="Cronologia",
            planned_start_date="2026-03-23",
        )
        first = ProjectTask.objects.create(
            project=project,
            name="Analisis",
            order=1,
            estimated_hours=Decimal("8.00"),
        )
        ProjectTask.objects.create(
            project=project,
            name="Implementacion",
            order=2,
            estimated_hours=Decimal("8.00"),
        )

        WorkLog.objects.create(
            date="2026-03-23",
            project=project,
            task=first,
            description="Arranque",
            actual_hours=Decimal("8.00"),
            work_type=WorkLog.WorkType.PROJECT,
        )
        WorkLog.objects.create(
            date="2026-03-24",
            description="Soporte urgente",
            actual_hours=Decimal("8.00"),
            work_type=WorkLog.WorkType.EXTERNAL,
        )

        context = build_timeline_context()
        project_summary = context["projects"][0]

        self.assertEqual(project_summary["baseline_end"].isoformat(), "2026-03-24")
        self.assertEqual(project_summary["projected_end"].isoformat(), "2026-03-25")
        self.assertEqual(project_summary["delay_days"], 1)
        self.assertEqual(project_summary["gantt_start"].isoformat(), "2026-03-23")
        self.assertEqual(project_summary["gantt_end"].isoformat(), "2026-03-25")
        self.assertEqual(len(project_summary["gantt_ticks"]), 3)
        self.assertEqual(project_summary["tasks"][0]["gantt"]["baseline_start"], 1)
        self.assertEqual(project_summary["tasks"][0]["gantt"]["baseline_span"], 1)

    def test_gantt_progress_uses_actual_hours_ratio(self):
        project = Project.objects.create(
            name="Seguimiento",
            planned_start_date="2026-03-23",
        )
        task = ProjectTask.objects.create(
            project=project,
            name="Backend",
            order=1,
            estimated_hours=Decimal("10.00"),
        )
        WorkLog.objects.create(
            date="2026-03-23",
            project=project,
            task=task,
            description="Trabajo parcial",
            actual_hours=Decimal("4.00"),
            work_type=WorkLog.WorkType.PROJECT,
        )

        context = build_timeline_context()
        task_summary = context["projects"][0]["tasks"][0]

        self.assertEqual(task_summary["progress_percent"], 40.0)
        self.assertEqual(task_summary["gantt"]["projected_start"], 1)
        self.assertEqual(task_summary["gantt"]["projected_span"], 2)

    def test_completed_task_without_logs_is_inferred_as_done(self):
        project = Project.objects.create(
            name="Migracion",
            planned_start_date="2026-03-23",
        )
        ProjectTask.objects.create(
            project=project,
            name="Preparacion",
            order=1,
            estimated_hours=Decimal("5.00"),
            status=ProjectTask.Status.COMPLETED,
        )

        context = build_timeline_context()
        project_summary = context["projects"][0]
        task_summary = project_summary["tasks"][0]

        self.assertEqual(task_summary["actual_hours"], Decimal("5.00"))
        self.assertEqual(task_summary["remaining_hours"], Decimal("0.00"))
        self.assertEqual(task_summary["progress_percent"], 100)
        self.assertTrue(task_summary["inferred_from_status"])
        self.assertEqual(project_summary["actual_hours"], Decimal("5.00"))

    def test_task_planned_dates_shift_gantt_position(self):
        project = Project.objects.create(
            name="Infraestructura",
            planned_start_date="2026-02-25",
        )
        ProjectTask.objects.create(
            project=project,
            name="Ubuntu",
            order=1,
            estimated_hours=Decimal("8.00"),
            planned_start_date="2026-03-28",
            planned_end_date="2026-03-30",
        )

        context = build_timeline_context()
        task_summary = context["projects"][0]["tasks"][0]

        self.assertEqual(task_summary["baseline_start"].isoformat(), "2026-03-28")
        self.assertEqual(task_summary["baseline_end"].isoformat(), "2026-03-30")
        self.assertEqual(task_summary["projected_start"].isoformat(), "2026-03-28")
        self.assertEqual(task_summary["projected_end"].isoformat(), "2026-03-30")


class IndexViewTests(TestCase):
    def test_can_create_and_update_work_logs_from_index(self):
        project = Project.objects.create(
            name="Proyecto Web",
            planned_start_date="2026-03-23",
        )
        task = ProjectTask.objects.create(
            project=project,
            name="Diseno",
            order=1,
            estimated_hours=Decimal("6.00"),
        )

        response = self.client.post(
            reverse("planner:index"),
            data={
                "date": "2026-03-23",
                "project": project.pk,
                "task": task.pk,
                "description": "Primer bloque",
                "actual_hours": "2.50",
                "work_type": WorkLog.WorkType.PROJECT,
                "notes": "",
            },
        )

        self.assertRedirects(response, reverse("planner:index"))
        work_log = WorkLog.objects.get()
        self.assertEqual(work_log.actual_hours, Decimal("2.50"))

        response = self.client.post(
            reverse("planner:index"),
            data={
                "entry_id": work_log.pk,
                "date": "2026-03-23",
                "project": project.pk,
                "task": task.pk,
                "description": "Primer bloque actualizado",
                "actual_hours": "3.00",
                "work_type": WorkLog.WorkType.PROJECT,
                "notes": "ajuste",
            },
        )

        self.assertRedirects(response, reverse("planner:index"))
        work_log.refresh_from_db()
        self.assertEqual(work_log.description, "Primer bloque actualizado")
        self.assertEqual(work_log.actual_hours, Decimal("3.00"))
