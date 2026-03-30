from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from .models import PlannerSettings, Project, WorkLog

DAILY_PROJECT_CAPACITY = Decimal("7.00")
ZERO = Decimal("0.00")
def _quantize(value):
    return value.quantize(Decimal("0.01"))


def _hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


def _soft_color(color):
    red, green, blue = _hex_to_rgb(color)
    return f"rgba({red}, {green}, {blue}, 0.14)"


def _contrast_text_color(color):
    red, green, blue = _hex_to_rgb(color)
    luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
    return "#111827" if luminance > 170 else "#ffffff"


def _format_hours_label(hours):
    normalized = _quantize(hours)
    if normalized == normalized.to_integral():
        return f"{int(normalized)} h"
    return f"{normalized} h"


def _days_from_hours(hours):
    if hours <= ZERO:
        return 1
    full_days, remainder = divmod(hours, DAILY_PROJECT_CAPACITY)
    return int(full_days) + (1 if remainder else 0)


def _width_percent_from_hours(hours):
    if hours <= ZERO:
        return 0
    return min(int((hours / DAILY_PROJECT_CAPACITY) * 100), 100)


def _end_date_from_hours(start_date, hours):
    return start_date + timedelta(days=_days_from_hours(hours) - 1)


def _floor_to_scale(value, scale):
    if scale == "year":
        return date(value.year, 1, 1)
    if scale == "month":
        return date(value.year, value.month, 1)
    return value


def _add_scale(value, scale):
    if scale == "year":
        return date(value.year + 1, 1, 1)
    if scale == "month":
        if value.month == 12:
            return date(value.year + 1, 1, 1)
        return date(value.year, value.month + 1, 1)
    return value + timedelta(days=1)


def _slot_label(value, scale):
    if scale == "year":
        return value.strftime("%Y")
    if scale == "month":
        return value.strftime("%m/%Y")
    return value.strftime("%d/%m")


def _build_slots(start_date, end_date, scale):
    current = _floor_to_scale(start_date, scale)
    slots = []
    slot_index = {}
    index = 1

    while current <= end_date:
        slots.append({"index": index, "label": _slot_label(current, scale)})
        slot_index[current] = index
        current = _add_scale(current, scale)
        index += 1

    return slots, slot_index


def _slot_start(value, scale, slot_index):
    return slot_index[_floor_to_scale(value, scale)]


def _slot_span(start_value, end_value, scale, slot_index):
    return _slot_start(end_value, scale, slot_index) - _slot_start(start_value, scale, slot_index) + 1


def build_timeline_context(scale="month"):
    today = timezone.localdate()
    settings = PlannerSettings.get_solo()
    projects = list(
        Project.objects.prefetch_related("requested_by", "assigned_users").all()
    )
    work_logs = list(
        WorkLog.objects.select_related("project")
        .prefetch_related("requested_by", "assigned_users")
        .order_by("-date", "-id")
    )

    project_hours = defaultdict(lambda: ZERO)
    project_last_log = {}
    other_hours = ZERO
    daily_markers = defaultdict(lambda: {"planned": [], "actual": [], "other": False})

    for work_log in work_logs:
        if work_log.work_type == WorkLog.WorkType.PROJECT and work_log.project_id:
            project_hours[work_log.project_id] += work_log.actual_hours
            last_log = project_last_log.get(work_log.project_id)
            if last_log is None or work_log.date > last_log:
                project_last_log[work_log.project_id] = work_log.date
            marker_list = daily_markers[work_log.date.isoformat()]["actual"]
            if not any(marker["projectId"] == work_log.project_id for marker in marker_list):
                marker_list.append(
                    {
                        "projectId": work_log.project_id,
                        "color": work_log.project.color,
                        "name": work_log.project.name,
                    }
                )
        else:
            other_hours += work_log.actual_hours
            daily_markers[work_log.date.isoformat()]["other"] = True

    project_summaries = []
    project_display_order = {}
    calendar_events = []
    timeline_start = None
    timeline_end = None

    for position, project in enumerate(projects, start=1):
        estimated_hours = project.estimated_hours
        logged_hours = _quantize(project_hours[project.id])
        remaining_hours = _quantize(max(estimated_hours - logged_hours, ZERO))

        baseline_end = _end_date_from_hours(project.planned_start_date, estimated_hours)

        if remaining_hours == ZERO:
            projected_end = project_last_log.get(project.id, baseline_end)
        elif logged_hours > ZERO:
            anchor = project_last_log.get(project.id, project.planned_start_date)
            projected_end = _end_date_from_hours(anchor, remaining_hours)
        else:
            projected_end = baseline_end

        blocking_hours = ZERO
        if remaining_hours > ZERO:
            for work_log in work_logs:
                if work_log.date < project.planned_start_date:
                    continue
                if work_log.work_type == WorkLog.WorkType.PROJECT and work_log.project_id == project.id:
                    continue
                blocking_hours += work_log.actual_hours

        interruption_delay_days = _days_from_hours(blocking_hours) if blocking_hours > ZERO else 0
        if interruption_delay_days:
            projected_end += timedelta(days=interruption_delay_days)

        delivery_date = project.delivery_date
        delivery_delay_days = None
        delivery_margin_days = None
        if delivery_date:
            if projected_end > delivery_date:
                delivery_delay_days = (projected_end - delivery_date).days
                delivery_margin_days = 0
            else:
                delivery_delay_days = 0
                delivery_margin_days = (delivery_date - projected_end).days

        actual_bar_end = (
            _end_date_from_hours(project.planned_start_date, min(logged_hours, estimated_hours))
            if logged_hours > ZERO
            else None
        )
        progress_percent = (
            min(round((logged_hours / estimated_hours) * 100, 2), 100)
            if estimated_hours > ZERO
            else 0
        )
        accent_color = project.color
        soft_color = _soft_color(project.color)
        contrast_text_color = _contrast_text_color(project.color)

        timeline_start = min(timeline_start, project.planned_start_date) if timeline_start else project.planned_start_date
        max_project_end = max(baseline_end, projected_end)
        timeline_end = max(timeline_end, max_project_end) if timeline_end else max_project_end

        summary = {
            "project": project,
            "estimated_hours": _quantize(estimated_hours),
            "logged_hours": logged_hours,
            "remaining_hours": remaining_hours,
            "baseline_end": baseline_end,
            "projected_end": projected_end,
            "actual_bar_end": actual_bar_end,
            "progress_percent": progress_percent,
            "accent_color": accent_color,
            "soft_color": soft_color,
            "delivery_date": delivery_date,
            "delivery_delay_days": delivery_delay_days,
            "delivery_margin_days": delivery_margin_days,
            "blocking_hours": _quantize(blocking_hours),
            "requested_by_names": [user.get_username() for user in project.requested_by.all()],
            "assigned_user_names": [user.get_username() for user in project.assigned_users.all()],
        }
        project_summaries.append(summary)
        project_display_order[project.id] = position * 10

        if not project.is_visible:
            continue

        calendar_events.append(
            {
                "id": f"project-{project.id}",
                "title": project.name,
                "start": project.planned_start_date.isoformat(),
                "end": (projected_end + timedelta(days=1)).isoformat(),
                "allDay": True,
                "backgroundColor": accent_color,
                "borderColor": accent_color,
                "textColor": contrast_text_color,
                "displayOrder": project_display_order[project.id],
                "classNames": ["project-range-event"],
                "extendedProps": {
                    "eventType": "project-range",
                    "projectId": project.id,
                    "hours": str(estimated_hours),
                    "remainingHours": str(remaining_hours),
                    "projectColor": accent_color,
                    "textColor": contrast_text_color,
                    "displayOrder": project_display_order[project.id],
                },
            }
        )

        current_day = project.planned_start_date
        while current_day <= projected_end:
            marker_list = daily_markers[current_day.isoformat()]["planned"]
            if not any(marker["projectId"] == project.id for marker in marker_list):
                marker_list.append(
                    {
                        "projectId": project.id,
                        "color": project.color,
                        "name": project.name,
                    }
                )
            current_day += timedelta(days=1)

    if not timeline_start:
        timeline_start = today
        timeline_end = today
    else:
        timeline_end = max(timeline_end, today)

    for work_log in reversed(work_logs):
        if work_log.project_id and not work_log.project.is_visible:
            continue
        if work_log.work_type == WorkLog.WorkType.OTHER and not settings.show_other_work:
            continue
        if work_log.work_type == WorkLog.WorkType.PROJECT and work_log.project_id:
            background_color = work_log.project.color
            text_color = _contrast_text_color(background_color)
            title = f"{work_log.project.name}: {work_log.actual_hours} h"
            class_names = ["worklog-event", "project-worklog-event"]
            display_order = project_display_order.get(work_log.project_id, 10_000) + 1
        else:
            background_color = "#cbd5e1"
            text_color = "#111827"
            title = f"No proyecto: {work_log.actual_hours} h"
            class_names = ["worklog-event", "external-worklog-event"]
            display_order = 100_000

        calendar_events.append(
            {
                "id": f"log-{work_log.id}",
                "title": title,
                "start": work_log.date.isoformat(),
                "allDay": True,
                "backgroundColor": background_color,
                "borderColor": background_color,
                "textColor": text_color,
                "displayOrder": display_order,
                "classNames": class_names,
                "extendedProps": {
                    "eventType": "worklog",
                    "editId": work_log.id,
                    "projectId": work_log.project_id,
                    "projectName": work_log.project.name if work_log.project_id else "",
                    "workType": work_log.work_type,
                    "description": work_log.description,
                    "hours": str(work_log.actual_hours),
                    "hoursLabel": _format_hours_label(work_log.actual_hours),
                    "widthPercent": _width_percent_from_hours(work_log.actual_hours),
                    "projectColor": background_color,
                    "textColor": text_color,
                    "displayOrder": display_order,
                },
            }
        )

    slots, slot_index = _build_slots(timeline_start, timeline_end, scale)

    visible_project_summaries = [summary for summary in project_summaries if summary["project"].is_visible]

    for summary in visible_project_summaries:
        project = summary["project"]
        summary["bars"] = {
            "baseline_start": _slot_start(project.planned_start_date, scale, slot_index),
            "baseline_span": _slot_span(project.planned_start_date, summary["baseline_end"], scale, slot_index),
            "projected_start": _slot_start(project.planned_start_date, scale, slot_index),
            "projected_span": _slot_span(project.planned_start_date, summary["projected_end"], scale, slot_index),
            "actual_start": _slot_start(project.planned_start_date, scale, slot_index),
            "actual_span": (
                _slot_span(project.planned_start_date, summary["actual_bar_end"], scale, slot_index)
                if summary["actual_bar_end"]
                else None
            ),
        }

    return {
        "projects": visible_project_summaries,
        "project_legend": project_summaries,
        "slots": slots,
        "slot_count": len(slots),
        "scale": scale,
        "daily_capacity_hours": DAILY_PROJECT_CAPACITY,
        "other_hours": _quantize(other_hours),
        "calendar_events": calendar_events,
        "calendar_markers": dict(daily_markers),
        "other_work_visible": settings.show_other_work,
    }
