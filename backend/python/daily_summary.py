from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd

from .analysis import category_metrics, overview_metrics, read_frame, root_cause_metrics, shift_metrics
from .anomaly_detection import detect_anomalies


def generate_summary(summary_date: date | None = None) -> dict[str, Any]:
    day_filter = "created_at::date = COALESCE(CAST(:summary_date AS date), (SELECT MAX(created_at)::date FROM tickets))"
    params = {"summary_date": summary_date}
    volume_sql = f"""
    SELECT COUNT(*) AS tickets_created,
           ROUND(100.0 * COUNT(*) FILTER (WHERE NOT sla_breached) / NULLIF(COUNT(*), 0), 2) AS sla_compliance,
           ROUND(AVG(resolution_hours)::numeric, 2) AS avg_resolution_hours
    FROM ticket_metrics
    WHERE {day_filter}
    """
    base = read_frame(volume_sql, params).iloc[0].fillna(0).to_dict()

    top_category = read_frame(f"""
        SELECT CONCAT(category_name, ' / ', subcategory) AS category, COUNT(*) AS tickets
        FROM ticket_metrics
        WHERE {day_filter}
        GROUP BY category
        ORDER BY tickets DESC
        LIMIT 1
    """, params).to_dict("records")

    top_root = read_frame(f"""
        SELECT COALESCE(root_cause, 'Missing') AS root_cause, COUNT(*) AS tickets
        FROM ticket_metrics
        WHERE {day_filter}
        GROUP BY COALESCE(root_cause, 'Missing')
        ORDER BY tickets DESC
        LIMIT 1
    """, params).to_dict("records")

    trend_sql = """
    WITH daily AS (
        SELECT created_at::date AS day, category_name, subcategory, COUNT(*) AS tickets
        FROM ticket_metrics
        GROUP BY day, category_name, subcategory
    ),
    latest AS (
        SELECT COALESCE(CAST(:summary_date AS date), MAX(day)) AS day FROM daily
    )
    SELECT
        CONCAT(d.category_name, ' / ', d.subcategory) AS category,
        d.tickets,
        p.tickets AS previous_tickets,
        ROUND(100.0 * (d.tickets - p.tickets) / NULLIF(p.tickets, 0), 1) AS change_pct
    FROM daily d
    JOIN latest l ON d.day = l.day
    LEFT JOIN daily p
      ON p.day = d.day - INTERVAL '1 day'
     AND p.category_name = d.category_name
     AND p.subcategory = d.subcategory
    WHERE p.tickets IS NOT NULL
    ORDER BY ABS(d.tickets - p.tickets) DESC
    LIMIT 1
    """
    trend = read_frame(trend_sql, params).fillna(0).to_dict("records")

    risks = detect_anomalies()[:10]
    categories = category_metrics()
    shifts = shift_metrics()
    roots = root_cause_metrics()

    recommendation = _recommendation(categories, shifts, roots, risks, trend)

    return {
        "ticketsCreated": int(base["tickets_created"]),
        "slaCompliance": float(base["sla_compliance"]),
        "averageResolutionHours": float(base["avg_resolution_hours"]),
        "topCategory": top_category[0] if top_category else None,
        "topRootCause": top_root[0] if top_root else None,
        "largestTrendChange": trend[0] if trend else None,
        "currentSlaRisks": len([r for r in risks if r["type"] == "open_beyond_sla"]),
        "recommendedInvestigation": recommendation,
        "risks": risks,
    }


def _recommendation(categories: list[dict[str, Any]], shifts: list[dict[str, Any]], roots: list[dict[str, Any]], risks: list[dict[str, Any]], trend: list[dict[str, Any]]) -> str:
    worst_category = max(categories, key=lambda item: item.get("avg_resolution_hours") or 0, default=None)
    worst_shift = max(shifts, key=lambda item: item.get("breach_rate") or 0, default=None)
    top_root = roots[0] if roots else None
    if risks:
        return f"Prioritize {len(risks)} active SLA risks, then review {worst_shift['shift']} shift handoffs and {top_root['root_cause']} incidents." if worst_shift and top_root else "Prioritize active SLA risks and review ownership handoffs."
    if trend and trend[0].get("change_pct", 0) > 25:
        return f"Investigate the {trend[0]['category']} volume increase before the next shift handoff."
    if worst_category:
        return f"Review runbooks and escalation paths for {worst_category['category']}, the slowest-resolving category."
    return "Monitor SLA exposure and compare category mix against the previous period."


def render_text(summary: dict[str, Any]) -> str:
    top_category = summary.get("topCategory") or {}
    top_root = summary.get("topRootCause") or {}
    trend = summary.get("largestTrendChange") or {}
    return f"""DAILY OPERATIONS SUMMARY

Tickets created: {summary['ticketsCreated']}
SLA compliance: {summary['slaCompliance']}%
Average resolution: {summary['averageResolutionHours']} hours

Top category:
{top_category.get('category', 'No tickets')} ({top_category.get('tickets', 0)} tickets)

Top root cause:
{top_root.get('root_cause', 'No root cause')} ({top_root.get('tickets', 0)} tickets)

SLA Risk:
{summary['currentSlaRisks']} tickets currently exceed SLA.

Trend:
{trend.get('category', 'No trend available')} changed by {trend.get('change_pct', 0)}%.

Recommended investigation:
{summary['recommendedInvestigation']}
"""


def main() -> None:
    summary = generate_summary()
    print(render_text(summary))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
