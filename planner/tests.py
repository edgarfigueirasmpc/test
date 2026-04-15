from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import PlannerSettings, Project, ProjectAttachment, WorkLog, WorkLogAttachment
from .services import build_timeline_context

User = get_user_model()


class WorkLogModelTests(TestCase):
    def test_project_work_requires_project(self):
        work_log = WorkLog(
            date="2026-03-30",
            description="Trabajo",
            actual_hours=Decimal("2.00"),
            work_type=WorkLog.WorkType.PROJECT,
        )

        with self.assertRaises(ValidationError):
            work_log.full_clean()

    def test_other_work_must_not_have_project(self):
        project = Project.objects.create(
            name="ERP",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("14.00"),
        )
        work_log = WorkLog(
            date="2026-03-30",
            project=project,
            description="Soporte general",
            actual_hours=Decimal("1.00"),
            work_type=WorkLog.WorkType.OTHER,
        )

        with self.assertRaises(ValidationError):
            work_log.full_clean()


class TimelineServiceTests(TestCase):
    def test_project_remaining_hours_and_projected_end_use_seven_hours_per_day(self):
        project = Project.objects.create(
            name="Web nueva",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("20.00"),
        )
        WorkLog.objects.create(
            date="2026-03-30",
            project=project,
            description="Analisis",
            actual_hours=Decimal("9.00"),
            work_type=WorkLog.WorkType.PROJECT,
        )

        context = build_timeline_context(scale="day")
        summary = context["projects"][0]

        self.assertEqual(summary["remaining_hours"], Decimal("11.00"))
        self.assertEqual(summary["baseline_end"].isoformat(), "2026-04-01")
        self.assertEqual(summary["projected_end"].isoformat(), "2026-03-31")
        self.assertEqual(summary["progress_percent"], 45.0)

    def test_other_work_delays_incomplete_projects(self):
        project = Project.objects.create(
            name="Implantacion",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("14.00"),
        )
        WorkLog.objects.create(
            date="2026-03-30",
            description="Urgencia externa",
            actual_hours=Decimal("7.00"),
            work_type=WorkLog.WorkType.OTHER,
        )

        context = build_timeline_context(scale="day")
        summary = context["projects"][0]

        self.assertEqual(summary["baseline_end"].isoformat(), "2026-03-31")
        self.assertEqual(summary["projected_end"].isoformat(), "2026-04-01")

    def test_work_on_another_project_also_delays_pending_project(self):
        delayed_project = Project.objects.create(
            name="Proyecto A",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("14.00"),
        )
        other_project = Project.objects.create(
            name="Proyecto B",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("7.00"),
        )
        WorkLog.objects.create(
            date="2026-03-30",
            project=other_project,
            description="Trabajo en el otro proyecto",
            actual_hours=Decimal("7.00"),
            work_type=WorkLog.WorkType.PROJECT,
        )

        context = build_timeline_context(scale="day")
        summary = next(item for item in context["projects"] if item["project"].id == delayed_project.id)

        self.assertEqual(summary["baseline_end"].isoformat(), "2026-03-31")
        self.assertEqual(summary["projected_end"].isoformat(), "2026-04-01")
        self.assertEqual(summary["blocking_hours"], Decimal("7.00"))

    @patch("planner.services.timezone.localdate", return_value=date(2026, 3, 20))
    def test_projects_can_overlap_in_month_view(self, _mock_localdate):
        Project.objects.create(
            name="Proyecto A",
            planned_start_date="2026-03-01",
            estimated_hours=Decimal("21.00"),
            color="#445566",
        )
        Project.objects.create(
            name="Proyecto B",
            planned_start_date="2026-03-15",
            estimated_hours=Decimal("14.00"),
            color="#778899",
        )

        context = build_timeline_context(scale="month")

        self.assertEqual(context["slot_count"], 1)
        self.assertEqual(len(context["projects"]), 2)
        self.assertEqual(context["projects"][0]["bars"]["baseline_start"], 1)
        self.assertEqual(context["projects"][1]["bars"]["baseline_start"], 1)
        self.assertEqual(context["projects"][0]["accent_color"], "#445566")

    def test_hidden_projects_stay_in_legend_but_not_in_calendar(self):
        visible_project = Project.objects.create(
            name="Visible",
            planned_start_date="2026-03-01",
            estimated_hours=Decimal("7.00"),
            color="#445566",
            is_visible=True,
        )
        hidden_project = Project.objects.create(
            name="Oculto",
            planned_start_date="2026-03-02",
            estimated_hours=Decimal("7.00"),
            color="#778899",
            is_visible=False,
        )

        context = build_timeline_context(scale="month")

        self.assertEqual([item["project"].name for item in context["projects"]], ["Visible"])
        self.assertEqual(
            [item["project"].name for item in context["project_legend"]],
            ["Visible", "Oculto"],
        )
        project_event_ids = {event["id"] for event in context["calendar_events"]}
        self.assertIn(f"project-{visible_project.id}", project_event_ids)
        self.assertNotIn(f"project-{hidden_project.id}", project_event_ids)

    def test_other_work_visibility_can_hide_external_logs_from_calendar(self):
        PlannerSettings.objects.create(show_other_work=False)
        WorkLog.objects.create(
            date="2026-03-30",
            description="Trabajo externo",
            actual_hours=Decimal("3.00"),
            work_type=WorkLog.WorkType.OTHER,
        )

        context = build_timeline_context(scale="month")

        self.assertFalse(context["other_work_visible"])
        self.assertFalse(any(event["extendedProps"]["workType"] == WorkLog.WorkType.OTHER for event in context["calendar_events"] if event["extendedProps"]["eventType"] == "worklog"))

    def test_calendar_events_allow_multiple_items_same_day(self):
        project = Project.objects.create(
            name="Proyecto A",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("14.00"),
            color="#336699",
        )
        WorkLog.objects.create(
            date="2026-03-30",
            project=project,
            description="Trabajo de proyecto",
            actual_hours=Decimal("2.00"),
            work_type=WorkLog.WorkType.PROJECT,
        )
        WorkLog.objects.create(
            date="2026-03-30",
            description="Trabajo externo",
            actual_hours=Decimal("1.50"),
            work_type=WorkLog.WorkType.OTHER,
        )

        context = build_timeline_context(scale="month")
        same_day_events = [
            event for event in context["calendar_events"]
            if event["start"] == "2026-03-30"
        ]

        self.assertEqual(len(same_day_events), 3)
        self.assertEqual(
            sorted(event["extendedProps"]["eventType"] for event in same_day_events),
            ["project-range", "worklog", "worklog"],
        )
        self.assertEqual(len(context["calendar_markers"]["2026-03-30"]["actual"]), 1)
        self.assertTrue(context["calendar_markers"]["2026-03-30"]["other"])

    def test_project_worklog_is_sorted_right_after_its_project_in_day_view(self):
        project_a = Project.objects.create(
            name="Configuracion inicial",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("14.00"),
            color="#ff3300",
        )
        project_b = Project.objects.create(
            name="Sistema GIS",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("14.00"),
            color="#2563eb",
        )
        WorkLog.objects.create(
            date="2026-03-30",
            project=project_a,
            description="Trabajo sobre A",
            actual_hours=Decimal("7.00"),
            work_type=WorkLog.WorkType.PROJECT,
        )

        context = build_timeline_context(scale="day")
        same_day_events = [
            event for event in context["calendar_events"]
            if event["start"] == "2026-03-30"
        ]
        ordered = sorted(same_day_events, key=lambda event: event["displayOrder"])

        self.assertEqual(ordered[0]["extendedProps"]["eventType"], "project-range")
        self.assertEqual(ordered[0]["extendedProps"]["projectId"], project_a.id)
        self.assertEqual(ordered[1]["extendedProps"]["eventType"], "worklog")
        self.assertEqual(ordered[1]["extendedProps"]["projectId"], project_a.id)
        self.assertEqual(ordered[2]["extendedProps"]["eventType"], "project-range")
        self.assertEqual(ordered[2]["extendedProps"]["projectId"], project_b.id)


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class IndexViewTests(TestCase):
    @patch("planner.cloudinary_utils.cloudinary.uploader.upload")
    def test_can_create_work_log_with_attachments_from_index(self, mock_upload):
        mock_upload.return_value = {
            "public_id": "planner/worklogs/1/parte",
            "resource_type": "raw",
            "format": "pdf",
            "bytes": 12,
            "secure_url": "https://res.cloudinary.com/demo/raw/upload/v1/parte.pdf",
        }
        project = Project.objects.create(
            name="Proyecto Web",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("12.00"),
        )

        response = self.client.post(
            reverse("planner:index"),
            data={
                "scale": "month",
                "date": "2026-03-30",
                "project": project.pk,
                "description": "Primer bloque",
                "actual_hours": "2.50",
                "work_type": WorkLog.WorkType.PROJECT,
                "attachments": [
                    SimpleUploadedFile("parte.pdf", b"contenido pdf", content_type="application/pdf"),
                ],
            },
        )

        self.assertRedirects(response, reverse("planner:index"))
        attachment = WorkLogAttachment.objects.get()
        self.assertEqual(attachment.original_filename, "parte.pdf")
        self.assertEqual(attachment.file_format, "pdf")
        self.assertEqual(attachment.work_log.description, "Primer bloque")
        mock_upload.assert_called_once()

    @patch("planner.cloudinary_utils.cloudinary.uploader.upload")
    def test_can_create_project_with_attachments_from_index(self, mock_upload):
        mock_upload.return_value = {
            "public_id": "planner/projects/1/plano",
            "resource_type": "raw",
            "format": "docx",
            "bytes": 18,
            "secure_url": "https://res.cloudinary.com/demo/raw/upload/v1/plano.docx",
        }

        response = self.client.post(
            reverse("planner:index"),
            data={
                "form_type": "project",
                "scale": "month",
                "name": "Proyecto Nuevo",
                "description": "Alta desde portada",
                "planned_start_date": "2026-03-30",
                "delivery_date": "2026-04-15",
                "is_visible": "on",
                "estimated_hours": "14.00",
                "color": "#445566",
                "status": Project.Status.PLANNED,
                "attachments": [
                    SimpleUploadedFile(
                        "plano.docx",
                        b"contenido docx",
                        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ],
            },
        )

        self.assertRedirects(response, reverse("planner:index"))
        attachment = ProjectAttachment.objects.get()
        self.assertEqual(attachment.original_filename, "plano.docx")
        self.assertEqual(attachment.project.name, "Proyecto Nuevo")
        mock_upload.assert_called_once()

    def test_can_create_and_update_work_logs_from_index(self):
        requester = User.objects.create_user(username="solicita", password="x")
        requester_two = User.objects.create_user(username="jefe", password="x")
        worker_one = User.objects.create_user(username="edgar", password="x")
        worker_two = User.objects.create_user(username="ana", password="x")
        project = Project.objects.create(
            name="Proyecto Web",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("12.00"),
        )

        response = self.client.post(
            reverse("planner:index"),
            data={
                "scale": "month",
                "date": "2026-03-30",
                "requested_by": [requester.pk, requester_two.pk],
                "assigned_users": [worker_one.pk, worker_two.pk],
                "project": project.pk,
                "description": "Primer bloque",
                "actual_hours": "2.50",
                "work_type": WorkLog.WorkType.PROJECT,
                "notes": "",
            },
        )

        self.assertRedirects(response, reverse("planner:index"))
        work_log = WorkLog.objects.get()
        self.assertEqual(work_log.actual_hours, Decimal("2.50"))
        self.assertEqual(
            list(work_log.requested_by.order_by("username").values_list("username", flat=True)),
            ["jefe", "solicita"],
        )
        self.assertEqual(
            list(work_log.assigned_users.order_by("username").values_list("username", flat=True)),
            ["ana", "edgar"],
        )

        response = self.client.post(
            reverse("planner:index"),
            data={
                "entry_id": work_log.pk,
                "scale": "year",
                "date": "2026-03-30",
                "requested_by": [requester_two.pk],
                "assigned_users": [worker_two.pk],
                "project": project.pk,
                "description": "Primer bloque actualizado",
                "actual_hours": "3.00",
                "work_type": WorkLog.WorkType.PROJECT,
                "notes": "ajuste",
            },
        )

        self.assertRedirects(response, f"{reverse('planner:index')}?scale=year")
        work_log.refresh_from_db()
        self.assertEqual(work_log.description, "Primer bloque actualizado")
        self.assertEqual(work_log.actual_hours, Decimal("3.00"))
        self.assertEqual(
            list(work_log.requested_by.values_list("username", flat=True)),
            ["jefe"],
        )
        self.assertEqual(
            list(work_log.assigned_users.values_list("username", flat=True)),
            ["ana"],
        )

    def test_can_create_and_update_projects_from_index(self):
        requester = User.objects.create_user(username="cliente", password="x")
        requester_two = User.objects.create_user(username="gerencia", password="x")
        worker_one = User.objects.create_user(username="marta", password="x")
        worker_two = User.objects.create_user(username="luis", password="x")
        existing = Project.objects.create(
            name="Existente",
            planned_start_date="2026-03-20",
            estimated_hours=Decimal("10.00"),
            color="#999999",
        )

        response = self.client.post(
            reverse("planner:index"),
            data={
                "form_type": "project",
                "scale": "month",
                "name": "Proyecto Nuevo",
                "description": "Alta desde portada",
                "planned_start_date": "2026-03-30",
                "delivery_date": "2026-04-15",
                "requested_by": [requester.pk, requester_two.pk],
                "assigned_users": [worker_one.pk, worker_two.pk],
                "is_visible": "on",
                "estimated_hours": "14.00",
                "color": "#445566",
                "status": Project.Status.PLANNED,
                "notes": "",
            },
        )

        self.assertRedirects(response, reverse("planner:index"))
        project = Project.objects.get(name="Proyecto Nuevo")
        self.assertEqual(project.color, "#445566")
        self.assertEqual(project.delivery_date.isoformat(), "2026-04-15")
        self.assertEqual(
            list(project.requested_by.order_by("username").values_list("username", flat=True)),
            ["cliente", "gerencia"],
        )
        self.assertEqual(
            list(project.assigned_users.order_by("username").values_list("username", flat=True)),
            ["luis", "marta"],
        )
        existing.refresh_from_db()
        self.assertEqual(existing.name, "Existente")

        response = self.client.post(
            reverse("planner:index"),
            data={
                "form_type": "project",
                "project_id": project.pk,
                "scale": "year",
                "name": "Proyecto Nuevo Editado",
                "description": "Editado",
                "planned_start_date": "2026-04-01",
                "delivery_date": "2026-04-30",
                "requested_by": [requester_two.pk],
                "assigned_users": [worker_two.pk],
                "is_visible": "on",
                "estimated_hours": "21.00",
                "color": "#112233",
                "status": Project.Status.IN_PROGRESS,
                "notes": "ok",
            },
        )

        self.assertRedirects(response, f"{reverse('planner:index')}?scale=year")
        project.refresh_from_db()
        self.assertEqual(project.name, "Proyecto Nuevo Editado")
        self.assertEqual(project.color, "#112233")
        self.assertEqual(project.delivery_date.isoformat(), "2026-04-30")
        self.assertEqual(
            list(project.requested_by.values_list("username", flat=True)),
            ["gerencia"],
        )
        self.assertEqual(
            list(project.assigned_users.values_list("username", flat=True)),
            ["luis"],
        )

    def test_duplicate_project_creation_is_rejected(self):
        Project.objects.create(
            name="Duplicado",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("10.00"),
        )

        response = self.client.post(
            reverse("planner:index"),
            data={
                "form_type": "project",
                "scale": "month",
                "name": "Duplicado",
                "description": "Intento repetido",
                "planned_start_date": "2026-03-30",
                "delivery_date": "",
                "estimated_hours": "10.00",
                "color": "#445566",
                "status": Project.Status.PLANNED,
                "notes": "",
                "is_visible": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Project.objects.filter(name="Duplicado").count(), 1)
        self.assertContains(response, "Ya existe un proyecto con ese nombre y fecha de inicio.")

    def test_can_toggle_project_visibility_from_index(self):
        project = Project.objects.create(
            name="Proyecto visible",
            planned_start_date="2026-03-30",
            estimated_hours=Decimal("8.00"),
            is_visible=True,
        )

        response = self.client.post(
            reverse("planner:index"),
            data={
                "form_type": "toggle_project_visibility",
                "project_id": project.pk,
                "is_visible": "false",
                "scale": "month",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertFalse(project.is_visible)

    def test_can_toggle_other_work_visibility_from_index(self):
        settings = PlannerSettings.get_solo()
        self.assertTrue(settings.show_other_work)

        response = self.client.post(
            reverse("planner:index"),
            data={
                "form_type": "toggle_project_visibility",
                "visibility_scope": "other_work",
                "is_visible": "false",
                "scale": "month",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        settings.refresh_from_db()
        self.assertFalse(settings.show_other_work)
