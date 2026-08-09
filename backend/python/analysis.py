from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from .db import get_engine


def _params(start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
    return {"start_date": start_date, "end_date": end_date}


def _date_filter(column: str = "created_at") -> str:
    return f"(:start_date IS NULL OR {column} >= :start_date) AND (:end_date IS NULL OR {column} < (CAST(:end_date AS date) + INTERVAL '1 day'))"


def read_frame(sql: str, params: dict[str, Any] | None = None, engine: Engine | None = None) -> pd.DataFrame:
    return pd.read_sql_query(text(sql), engine or get_engine(), params=params or {})


def overview_metrics(start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
    sql = f"""
    WITH current_period AS (
        SELECT *
        FROM ticket_metrics
        WHERE {_date_filter()}
    ),
    bounds AS (
        SELECT
            COALESCE(CAST(:start_date AS date), MIN(created_at)::date) AS start_date,
            COALESCE(CAST(:end_date AS date), MAX(created_at)::date) AS end_date
        FROM tickets
    ),
    previous_period AS (
        SELECT tm.*
        FROM ticket_metrics tm, bounds b
        WHERE tm.created_at >= b.start_date - ((b.end_date - b.start_date + 1) * INTERVAL '1 day')
          AND tm.created_at < b.start_date
    )
    SELECT
        (SELECT COUNT(*) FROM current_period) AS total_tickets,
        (SELECT COUNT(*) FILTER (WHERE sla_breached) FROM current_period) AS sla_breaches,
        (SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE NOT sla_breached) / NULLIF(COUNT(*), 0), 2) FROM current_period) AS sla_compliance,
        (SELECT ROUND(AVG(resolution_hours)::numeric, 2) FROM current_period WHERE resolution_hours IS NOT NULL) AS avg_resolution_hours,
        (SELECT COUNT(*) FROM previous_period) AS previous_total_tickets,
        (SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE NOT sla_breached) / NULLIF(COUNT(*), 0), 2) FROM previous_period) AS previous_sla_compliance,
        (SELECT ROUND(AVG(resolution_hours)::numeric, 2) FROM previous_period WHERE resolution_hours IS NOT NULL) AS previous_avg_resolution_hours,
        (SELECT COUNT(*) FILTER (WHERE sla_breached) FROM previous_period) AS previous_sla_breaches,
        (SELECT MAX(inserted_at) FROM tickets) AS data_freshness
    """
    row = read_frame(sql, _params(start_date, end_date)).iloc[0].to_dict()
    return {k: (None if pd.isna(v) else v) for k, v in row.items()}


def ticket_trends(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    sql = f"""
    SELECT
        DATE_TRUNC('day', created_at)::date AS date,
        COUNT(*) AS tickets,
        COUNT(*) FILTER (WHERE sla_breached) AS breaches,
        ROUND(AVG(resolution_hours)::numeric, 2) AS avg_resolution_hours
    FROM ticket_metrics
    WHERE {_date_filter()}
    GROUP BY 1
    ORDER BY 1
    """
    return read_frame(sql, _params(start_date, end_date)).to_dict("records")


def category_metrics(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    sql = f"""
    SELECT
        category_name,
        subcategory,
        CONCAT(category_name, ' / ', subcategory) AS category,
        COUNT(*) AS tickets,
        ROUND(AVG(resolution_hours)::numeric, 2) AS avg_resolution_hours,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_hours)::numeric, 2) AS median_resolution_hours,
        ROUND(100.0 * COUNT(*) FILTER (WHERE sla_breached) / NULLIF(COUNT(*), 0), 2) AS breach_rate
    FROM ticket_metrics
    WHERE {_date_filter()}
    GROUP BY category_name, subcategory
    ORDER BY tickets DESC
    """
    return read_frame(sql, _params(start_date, end_date)).fillna(0).to_dict("records")


def priority_distribution(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    sql = f"""
    SELECT priority, COUNT(*) AS tickets
    FROM ticket_metrics
    WHERE {_date_filter()}
    GROUP BY priority
    ORDER BY priority
    """
    return read_frame(sql, _params(start_date, end_date)).to_dict("records")


def resolution_distribution(start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
    sql = f"""
    SELECT
        CASE
            WHEN resolution_hours < 1 THEN '<1h'
            WHEN resolution_hours < 4 THEN '1-4h'
            WHEN resolution_hours < 8 THEN '4-8h'
            WHEN resolution_hours < 24 THEN '8-24h'
            WHEN resolution_hours < 72 THEN '1-3d'
            ELSE '3d+'
        END AS bucket,
        COUNT(*) AS tickets
    FROM ticket_metrics
    WHERE {_date_filter()} AND resolution_hours IS NOT NULL
    GROUP BY bucket
    ORDER BY MIN(resolution_hours)
    """
    by_category = category_metrics(start_date, end_date)
    return {"distribution": read_frame(sql, _params(start_date, end_date)).to_dict("records"), "byCategory": by_category}


def sla_metrics(start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
    sql = f"""
    SELECT
        COUNT(*) AS tickets,
        COUNT(*) FILTER (WHERE sla_breached) AS breached,
        COUNT(*) FILTER (WHERE NOT sla_breached) AS compliant,
        ROUND(100.0 * COUNT(*) FILTER (WHERE NOT sla_breached) / NULLIF(COUNT(*), 0), 2) AS compliance,
        ROUND(100.0 * COUNT(*) FILTER (WHERE sla_breached) / NULLIF(COUNT(*), 0), 2) AS breach_rate
    FROM ticket_metrics
    WHERE {_date_filter()}
    """
    by_category_sql = f"""
    SELECT CONCAT(category_name, ' / ', subcategory) AS label,
           ROUND(100.0 * COUNT(*) FILTER (WHERE NOT sla_breached) / NULLIF(COUNT(*), 0), 2) AS compliance,
           ROUND(100.0 * COUNT(*) FILTER (WHERE sla_breached) / NULLIF(COUNT(*), 0), 2) AS breach_rate
    FROM ticket_metrics
    WHERE {_date_filter()}
    GROUP BY label
    ORDER BY breach_rate DESC
    LIMIT 10
    """
    return {
        "overall": read_frame(sql, _params(start_date, end_date)).iloc[0].fillna(0).to_dict(),
        "byCategory": read_frame(by_category_sql, _params(start_date, end_date)).fillna(0).to_dict("records"),
    }


def root_cause_metrics(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    sql = f"""
    SELECT
        COALESCE(root_cause, 'Missing') AS root_cause,
        COUNT(*) AS tickets,
        ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS share
    FROM ticket_metrics
    WHERE {_date_filter()}
    GROUP BY COALESCE(root_cause, 'Missing')
    ORDER BY tickets DESC
    LIMIT 12
    """
    return read_frame(sql, _params(start_date, end_date)).to_dict("records")


def agent_metrics(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    sql = f"""
    SELECT
        agent_id,
        agent_name,
        team,
        shift,
        experience_level,
        COUNT(*) AS tickets,
        ROUND(AVG(resolution_hours)::numeric, 2) AS avg_resolution_hours,
        ROUND(100.0 * COUNT(*) FILTER (WHERE NOT sla_breached) / NULLIF(COUNT(*), 0), 2) AS sla_compliance,
        ROUND(100.0 * COUNT(*) FILTER (WHERE escalation_flag) / NULLIF(COUNT(*), 0), 2) AS escalation_rate
    FROM ticket_metrics
    WHERE {_date_filter()}
    GROUP BY agent_id, agent_name, team, shift, experience_level
    ORDER BY tickets DESC
    """
    return read_frame(sql, _params(start_date, end_date)).fillna(0).to_dict("records")


def shift_metrics(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    sql = f"""
    SELECT
        shift,
        COUNT(*) AS tickets,
        ROUND(AVG(resolution_hours)::numeric, 2) AS avg_resolution_hours,
        ROUND(100.0 * COUNT(*) FILTER (WHERE NOT sla_breached) / NULLIF(COUNT(*), 0), 2) AS sla_compliance,
        ROUND(100.0 * COUNT(*) FILTER (WHERE sla_breached) / NULLIF(COUNT(*), 0), 2) AS breach_rate
    FROM ticket_metrics
    WHERE {_date_filter()}
    GROUP BY shift
    ORDER BY CASE shift WHEN 'Morning' THEN 1 WHEN 'Evening' THEN 2 ELSE 3 END
    """
    return read_frame(sql, _params(start_date, end_date)).fillna(0).to_dict("records")


def data_quality() -> dict[str, Any]:
    sql = """
    WITH likely_duplicates AS (
        SELECT COUNT(*) AS duplicate_records
        FROM (
            SELECT category_id, description, DATE_TRUNC('hour', created_at) AS hour_bucket, COUNT(*)
            FROM tickets
            GROUP BY category_id, description, hour_bucket
            HAVING COUNT(*) > 1
        ) d
    )
    SELECT
        (SELECT duplicate_records FROM likely_duplicates) AS duplicate_records,
        COUNT(*) FILTER (WHERE root_cause IS NULL OR TRIM(root_cause) = '') AS missing_root_causes,
        COUNT(*) FILTER (
            WHERE first_response_at < created_at
               OR resolved_at < created_at
               OR priority NOT IN ('P1', 'P2', 'P3', 'P4')
        ) AS invalid_records,
        MAX(inserted_at) AS data_freshness
    FROM tickets
    """
    return read_frame(sql).iloc[0].fillna(0).to_dict()


def ticket_page(filters: dict[str, Any]) -> dict[str, Any]:
    clauses = ["(:start_date IS NULL OR created_at >= :start_date)", "(:end_date IS NULL OR created_at < (CAST(:end_date AS date) + INTERVAL '1 day'))"]
    params = {
        "start_date": filters.get("start_date"),
        "end_date": filters.get("end_date"),
        "category": filters.get("category"),
        "priority": filters.get("priority"),
        "status": filters.get("status"),
        "shift": filters.get("shift"),
        "sla_status": filters.get("sla_status"),
        "search": f"%{filters.get('search', '')}%",
        "limit": int(filters.get("limit", 25)),
        "offset": int(filters.get("offset", 0)),
    }
    if filters.get("category"):
        clauses.append("CONCAT(category_name, ' / ', subcategory) = :category")
    if filters.get("priority"):
        clauses.append("priority = :priority")
    if filters.get("status"):
        clauses.append("status = :status")
    if filters.get("shift"):
        clauses.append("shift = :shift")
    if filters.get("sla_status") == "Breached":
        clauses.append("sla_breached = TRUE")
    if filters.get("sla_status") == "Compliant":
        clauses.append("sla_breached = FALSE")
    if filters.get("search"):
        clauses.append("(ticket_id ILIKE :search OR description ILIKE :search OR COALESCE(root_cause, '') ILIKE :search OR agent_name ILIKE :search)")

    sort_map = {
        "created_at": "created_at",
        "resolution_hours": "resolution_hours",
        "priority": "priority",
        "status": "status",
        "category": "category_name",
        "sla": "sla_breached",
    }
    sort_by = sort_map.get(filters.get("sort_by", "created_at"), "created_at")
    direction = "ASC" if filters.get("direction") == "asc" else "DESC"
    where = " AND ".join(clauses)
    sql = f"""
    SELECT
        ticket_id,
        CONCAT(category_name, ' / ', subcategory) AS category,
        priority,
        status,
        agent_name,
        shift,
        created_at,
        first_response_at,
        resolved_at,
        ROUND(resolution_hours::numeric, 2) AS resolution_hours,
        ROUND(hours_open::numeric, 2) AS hours_open,
        sla_hours,
        sla_breached,
        root_cause,
        resolution_type,
        escalation_flag,
        customer_impact,
        description
    FROM ticket_metrics
    WHERE {where}
    ORDER BY {sort_by} {direction}
    LIMIT :limit OFFSET :offset
    """
    count_sql = f"SELECT COUNT(*) AS total FROM ticket_metrics WHERE {where}"
    rows = read_frame(sql, params).fillna("").to_dict("records")
    total = int(read_frame(count_sql, params).iloc[0]["total"])
    return {"rows": rows, "total": total}


def filter_options() -> dict[str, list[str]]:
    sql = """
    SELECT
        ARRAY_AGG(DISTINCT CONCAT(category_name, ' / ', subcategory) ORDER BY CONCAT(category_name, ' / ', subcategory)) AS categories,
        ARRAY_AGG(DISTINCT priority ORDER BY priority) AS priorities,
        ARRAY_AGG(DISTINCT status ORDER BY status) AS statuses,
        ARRAY_AGG(DISTINCT shift ORDER BY shift) AS shifts
    FROM ticket_metrics
    """
    return read_frame(sql).iloc[0].to_dict()
