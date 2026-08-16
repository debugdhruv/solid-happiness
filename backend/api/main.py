from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.python.analysis import (
    agent_metrics,
    category_metrics,
    data_quality,
    filter_options,
    overview_metrics,
    priority_distribution,
    resolution_distribution,
    root_cause_metrics,
    shift_metrics,
    sla_metrics,
    ticket_page,
    ticket_trends,
)
from backend.python.anomaly_detection import detect_anomalies
from backend.python.daily_summary import generate_summary
from backend.python.db import healthcheck

app = FastAPI(
    title="Support Ticket Analytics API",
    description="Operational analytics and root-cause monitoring API backed by PostgreSQL, SQLAlchemy, and Pandas.",
    version="1.0.0",
)


def _cors_origins() -> list[str]:
    defaults = ["http://localhost:3000", "http://127.0.0.1:3000"]
    configured = os.getenv("BACKEND_CORS_ORIGINS", "")
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [*defaults, *origins]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=os.getenv("BACKEND_CORS_ORIGIN_REGEX"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return healthcheck()


@app.get("/api/overview")
def overview(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: overview_metrics(start_date, end_date))


@app.get("/api/tickets/trend")
def trends(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: ticket_trends(start_date, end_date))


@app.get("/api/tickets/categories")
def categories(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: category_metrics(start_date, end_date))


@app.get("/api/tickets/priorities")
def priorities(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: priority_distribution(start_date, end_date))


@app.get("/api/resolution")
def resolution(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: resolution_distribution(start_date, end_date))


@app.get("/api/sla")
def sla(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: sla_metrics(start_date, end_date))


@app.get("/api/root-causes")
def root_causes(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: root_cause_metrics(start_date, end_date))


@app.get("/api/agents")
def agents(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: agent_metrics(start_date, end_date))


@app.get("/api/shifts")
def shifts(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: shift_metrics(start_date, end_date))


@app.get("/api/anomalies")
def anomalies(start_date: date | None = None, end_date: date | None = None) -> Any:
    return _safe(lambda: detect_anomalies(start_date, end_date))


@app.get("/api/summary")
def summary(summary_date: date | None = None) -> Any:
    return _safe(lambda: generate_summary(summary_date))


@app.get("/api/data-quality")
def quality() -> Any:
    return _safe(data_quality)


@app.get("/api/filter-options")
def filters() -> Any:
    return _safe(filter_options)


@app.get("/api/tickets")
def tickets(
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    shift: str | None = None,
    sla_status: str | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    direction: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
) -> Any:
    return _safe(lambda: ticket_page({
        "start_date": start_date,
        "end_date": end_date,
        "category": category,
        "priority": priority,
        "status": status,
        "shift": shift,
        "sla_status": sla_status,
        "search": search,
        "sort_by": sort_by,
        "direction": direction,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }))


@app.get("/api/insights")
def insights(start_date: date | None = None, end_date: date | None = None) -> Any:
    def compute() -> list[dict[str, str]]:
        categories_data = category_metrics(start_date, end_date)
        shifts_data = shift_metrics(start_date, end_date)
        roots_data = root_cause_metrics(start_date, end_date)
        overview_data = overview_metrics(start_date, end_date)
        anomalies_data = detect_anomalies(start_date, end_date)
        results: list[dict[str, str]] = []

        if categories_data:
            slowest = max(categories_data, key=lambda row: row.get("avg_resolution_hours") or 0)
            results.append({
                "type": "warning",
                "title": "Slowest Category",
                "description": f"{slowest['category']} has the highest average resolution time at {slowest['avg_resolution_hours']} hours.",
            })
            riskiest = max(categories_data, key=lambda row: row.get("breach_rate") or 0)
            if riskiest.get("breach_rate", 0) > 20:
                results.append({
                    "type": "critical",
                    "title": "Category SLA Exposure",
                    "description": f"{riskiest['category']} has a {riskiest['breach_rate']}% breach rate and needs RCA review.",
                })

        if shifts_data:
            worst_shift = max(shifts_data, key=lambda row: row.get("breach_rate") or 0)
            results.append({
                "type": "warning" if worst_shift.get("breach_rate", 0) > 15 else "info",
                "title": "Shift Performance",
                "description": f"{worst_shift['shift']} shift has the highest SLA breach rate at {worst_shift['breach_rate']}%.",
            })

        if roots_data:
            top_root = roots_data[0]
            results.append({
                "type": "info",
                "title": "Recurring Root Cause",
                "description": f"{top_root['root_cause']} is the most common root cause with {top_root['tickets']} tickets.",
            })

        if overview_data.get("previous_total_tickets"):
            current = overview_data["total_tickets"] or 0
            previous = overview_data["previous_total_tickets"] or 0
            change = round(100 * (current - previous) / previous, 1) if previous else 0
            results.append({
                "type": "critical" if change > 25 else "positive" if change < -10 else "info",
                "title": "Volume Trend",
                "description": f"Ticket volume changed {change}% compared with the previous comparable period.",
            })

        active_risks = len([row for row in anomalies_data if row["type"] == "open_beyond_sla"])
        if active_risks:
            results.append({
                "type": "critical",
                "title": "Active SLA Risk",
                "description": f"{active_risks} open tickets are currently beyond SLA and require ownership review.",
            })
        return results

    return _safe(compute)


def _safe(callback):
    try:
        return _normalize(callback())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if np.isnan(value) else float(value)
    if pd.isna(value):
        return None
    return value
