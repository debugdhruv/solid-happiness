SELECT
    ROUND(100.0 * COUNT(*) FILTER (WHERE sla_breached) / NULLIF(COUNT(*), 0), 2) AS sla_breach_rate_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE NOT sla_breached) / NULLIF(COUNT(*), 0), 2) AS sla_compliance_pct
FROM ticket_metrics;

