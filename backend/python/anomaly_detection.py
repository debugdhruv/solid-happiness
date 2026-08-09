from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from .analysis import _date_filter, _params, read_frame


def detect_anomalies(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []

    outlier_sql = f"""
    WITH stats AS (
        SELECT
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY resolution_hours) AS q3,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY resolution_hours) AS q1
        FROM ticket_metrics
        WHERE {_date_filter()} AND resolution_hours IS NOT NULL
    )
    SELECT ticket_id, category_name, subcategory, priority, resolution_hours, sla_hours, agent_name, root_cause
    FROM ticket_metrics, stats
    WHERE {_date_filter()} AND resolution_hours IS NOT NULL
      AND resolution_hours > q3 + 1.5 * (q3 - q1)
    ORDER BY resolution_hours DESC
    LIMIT 20
    """
    outliers = read_frame(outlier_sql, _params(start_date, end_date))
    for row in outliers.to_dict("records"):
        anomalies.append({
            "type": "resolution_outlier",
            "severity": "critical" if row["resolution_hours"] > row["sla_hours"] * 3 else "warning",
            "title": f"{row['ticket_id']} has unusually long resolution time",
            "description": f"{row['category_name']} / {row['subcategory']} took {row['resolution_hours']:.1f} hours.",
            "ticketId": row["ticket_id"],
            "metadata": row,
        })

    open_sql = """
    SELECT ticket_id, category_name, subcategory, priority, status, hours_open, sla_hours, agent_name, shift
    FROM ticket_metrics
    WHERE resolved_at IS NULL AND hours_open > sla_hours
    ORDER BY hours_open - sla_hours DESC
    LIMIT 25
    """
    open_risks = read_frame(open_sql)
    for row in open_risks.to_dict("records"):
        anomalies.append({
            "type": "open_beyond_sla",
            "severity": "critical",
            "title": f"{row['ticket_id']} is open beyond SLA",
            "description": f"{row['priority']} {row['category_name']} ticket is {row['hours_open'] - row['sla_hours']:.1f} hours over target.",
            "ticketId": row["ticket_id"],
            "metadata": row,
        })

    spike_sql = f"""
    WITH daily AS (
        SELECT DATE_TRUNC('day', created_at)::date AS day, category_name, subcategory, COUNT(*) AS tickets
        FROM ticket_metrics
        WHERE {_date_filter()}
        GROUP BY day, category_name, subcategory
    ),
    scored AS (
        SELECT *,
               AVG(tickets) OVER (PARTITION BY category_name, subcategory) AS avg_tickets,
               STDDEV_POP(tickets) OVER (PARTITION BY category_name, subcategory) AS std_tickets
        FROM daily
    )
    SELECT day, category_name, subcategory, tickets, avg_tickets, std_tickets
    FROM scored
    WHERE std_tickets > 0 AND tickets > avg_tickets + 2 * std_tickets
    ORDER BY day DESC, tickets DESC
    LIMIT 10
    """
    spikes = read_frame(spike_sql, _params(start_date, end_date))
    for row in spikes.to_dict("records"):
        anomalies.append({
            "type": "category_spike",
            "severity": "warning",
            "title": f"{row['category_name']} / {row['subcategory']} spike on {row['day']}",
            "description": f"{int(row['tickets'])} tickets versus a normal daily average of {row['avg_tickets']:.1f}.",
            "ticketId": None,
            "metadata": row,
        })

    return _json_safe(anomalies)


def _json_safe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def convert(value: Any) -> Any:
        if pd.isna(value):
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    return [{key: convert(value) if key != "metadata" else {k: convert(v) for k, v in value.items()} for key, value in item.items()} for item in records]

