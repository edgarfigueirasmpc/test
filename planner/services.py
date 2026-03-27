from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from math import ceil

from .models import Project, WorkLog

DAILY_CAPACITY_HOURS = Decimal("8.00")
ZERO = Decimal("0.00")


def _quantize(value):
    return value.quantize(Decimal("0.01"))


def _date_range_days(start_date, end_date):
    if not start_date or not end_date:
        return 1
    return max((end_date - start_date).days + 1, 1)


def _build_gantt_span(row, range_start, range_days):
    def grid_start(point):
        if not point:
            return None
        return max((point - range_start).days + 1, 1)

    def grid_span(start_point, end_point):
        if not start_point or not end_point:
            return None
        return _date_range_days(start_point, end_point)

    return {
        "total_days": range_days,
        "baseline_start": grid_start(row["baseline_start"]),
        "baseline_span": grid_span(row["baseline_start"], row["baseline_end"]),
        "projected_start": grid_start(row["projected_start"]),
        "projected_span": grid_span(row["projected_start"], row["projected_end"]),
        "actual_start": grid_start(row["actual_start"]),
        "actual_span": grid_span(row["actual_start"], row["actual_end"]),
    }


def _schedule_tasks(tasks, start_date, initial_load):
    scheduled_load = defaultdict(lambda: ZERO)
    current_day = start_date
    results = {}

    for task in tasks:
        remaining_hours = max(task["remaining_hours"], ZERO)
        scheduled_start = None
        scheduled_end = None
        constraint_start = task.get("constraint_start")

        if constraint_start and current_day < constraint_start:
            current_day = constraint_start

        while remaining_hours > ZERO:
            used_hours = initial_load[current_day] + scheduled_load[current_day]
            free_hours = max(DAILY_CAPACITY_HOURS - used_hours, ZERO)

            if free_hours <= ZERO:
                current_day += timedelta(days=1)
                continue

            if scheduled_start is None:
                scheduled_start = current_day

            allocated_hours = min(free_hours, remaining_hours)
            scheduled_load[current_day] += allocated_hours
            remaining_hours -= allocated_hours
            scheduled_end = current_day

            if remaining_hours > ZERO and allocated_hours == free_hours:
                current_day += timedelta(days=1)

        results[task["id"]] = {
            "scheduled_start": scheduled_start,
            "scheduled_end": scheduled_end,
        }

    return results


def build_timeline_context():
    projects = Project.objects.prefetch_related("tasks", "work_logs").all()
    work_logs = list(
        WorkLog.objects.select_related("project", "task").order_by("date", "id")
    )

    load_by_day = defaultdict(lambda: ZERO)
    task_actual_hours = defaultdict(lambda: ZERO)
    project_actual_hours = defaultdict(lambda: ZERO)
    external_hours = ZERO

    for work_log in work_logs:
        load_by_day[work_log.date] += work_log.actual_hours
        if work_log.project_id:
            project_actual_hours[work_log.project_id] += work_log.actual_hours
        if work_log.task_id:
            task_actual_hours[work_log.task_id] += work_log.actual_hours
        if work_log.work_type != WorkLog.WorkType.PROJECT:
            external_hours += work_log.actual_hours

    project_summaries = []

    for project in projects:
        task_rows = []
        ordered_tasks = list(project.tasks.all())

        for task in ordered_tasks:
            actual_hours = task_actual_hours[task.id]
            inferred_from_status = False
            remaining_hours = max(task.estimated_hours - actual_hours, ZERO)
            task_logs = [log for log in work_logs if log.task_id == task.id]
            actual_start = task_logs[0].date if task_logs else None
            actual_end = task_logs[-1].date if task_logs else None

            if actual_hours == ZERO and task.status == task.Status.COMPLETED:
                actual_hours = task.estimated_hours
                remaining_hours = ZERO
                inferred_from_status = True

            task_rows.append(
                {
                    "id": task.id,
                    "task": task,
                    "estimated_hours": task.estimated_hours,
                    "actual_hours": _quantize(actual_hours),
                    "remaining_hours": _quantize(remaining_hours),
                    "actual_start": actual_start,
                    "actual_end": actual_end,
                    "inferred_from_status": inferred_from_status,
                    "constraint_start": task.planned_start_date,
                    "constraint_end": task.planned_end_date,
                }
            )

        baseline_tasks = [
            {**row, "remaining_hours": row["estimated_hours"]} for row in task_rows
        ]
        baseline_schedule = _schedule_tasks(
            baseline_tasks,
            project.planned_start_date,
            defaultdict(lambda: ZERO),
        )
        projected_schedule = _schedule_tasks(task_rows, project.planned_start_date, load_by_day)

        baseline_end = None
        projected_end = None

        for row in task_rows:
            baseline_row = baseline_schedule[row["id"]]
            projected_row = projected_schedule[row["id"]]
            baseline_end = baseline_row["scheduled_end"] or baseline_end

            if row["inferred_from_status"] and not row["actual_start"]:
                row["actual_start"] = row["task"].planned_start_date or baseline_row["scheduled_start"]
            if row["inferred_from_status"] and not row["actual_end"]:
                row["actual_end"] = row["task"].planned_end_date or baseline_row["scheduled_end"]

            projected_start = row["actual_start"] or projected_row["scheduled_start"]
            projected_end_for_task = projected_row["scheduled_end"] or row["actual_end"]

            if not row["actual_start"] and row["task"].planned_start_date:
                row["baseline_start"] = max(
                    baseline_row["scheduled_start"],
                    row["task"].planned_start_date,
                )
            else:
                row["baseline_start"] = baseline_row["scheduled_start"]

            if row["task"].planned_end_date and row["baseline_start"]:
                row["baseline_end"] = max(
                    row["baseline_start"],
                    row["task"].planned_end_date,
                )
            else:
                row["baseline_end"] = baseline_row["scheduled_end"]

            if not row["actual_start"] and row["task"].planned_start_date and projected_start:
                projected_start = max(projected_start, row["task"].planned_start_date)
            if row["task"].planned_end_date and projected_end_for_task:
                projected_end_for_task = max(projected_end_for_task, row["task"].planned_end_date)

            if projected_end_for_task:
                projected_end = projected_end_for_task

            row["projected_start"] = projected_start
            row["projected_end"] = projected_end_for_task

        delay_days = 0
        if baseline_end and projected_end:
            delay_days = max((projected_end - baseline_end).days, 0)

        range_candidates_start = [
            value
            for value in [project.planned_start_date]
            + [task["baseline_start"] for task in task_rows]
            + [task["projected_start"] for task in task_rows]
            + [task["actual_start"] for task in task_rows]
            if value
        ]
        range_candidates_end = [
            value
            for value in [baseline_end, projected_end]
            + [task["actual_end"] for task in task_rows]
            if value
        ]
        gantt_start = min(range_candidates_start) if range_candidates_start else None
        gantt_end = max(range_candidates_end) if range_candidates_end else gantt_start
        gantt_days = _date_range_days(gantt_start, gantt_end) if gantt_start else 1

        gantt_ticks = []
        if gantt_start and gantt_end:
            tick_step = max(1, ceil(gantt_days / 8))
            current_day = gantt_start
            while current_day <= gantt_end:
                day_index = (current_day - gantt_start).days + 1
                is_first = day_index == 1
                is_last = day_index == gantt_days
                is_step_tick = (day_index - 1) % tick_step == 0

                if is_first or is_last or is_step_tick:
                    gantt_ticks.append(
                        {
                            "label": current_day.strftime("%d/%m"),
                            "day_index": day_index,
                        }
                    )
                current_day += timedelta(days=1)

        for row in task_rows:
            row["progress_percent"] = min(
                round((row["actual_hours"] / row["estimated_hours"]) * 100, 2)
                if row["estimated_hours"] > ZERO
                else 0,
                100,
            )
            row["gantt"] = _build_gantt_span(row, gantt_start, gantt_days)

        project_summaries.append(
            {
                "project": project,
                "tasks": task_rows,
                "estimated_hours": _quantize(
                    sum((task["estimated_hours"] for task in task_rows), ZERO)
                ),
                "actual_hours": _quantize(
                    sum((task["actual_hours"] for task in task_rows), ZERO)
                ),
                "remaining_hours": _quantize(
                    sum((task["remaining_hours"] for task in task_rows), ZERO)
                ),
                "baseline_end": baseline_end,
                "projected_end": projected_end,
                "delay_days": delay_days,
                "gantt_start": gantt_start,
                "gantt_end": gantt_end,
                "gantt_days": gantt_days,
                "gantt_ticks": gantt_ticks,
            }
        )

    return {
        "projects": project_summaries,
        "external_hours": _quantize(external_hours),
        "daily_capacity_hours": DAILY_CAPACITY_HOURS,
    }
