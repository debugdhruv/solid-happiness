SELECT
    agent_name,
    team,
    shift,
    COUNT(*) AS tickets,
    ROUND(AVG(resolution_hours)::numeric, 2) AS avg_resolution_hours,
    ROUND(100.0 * COUNT(*) FILTER (WHERE NOT sla_breached) / NULLIF(COUNT(*), 0), 2) AS sla_compliance_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE escalation_flag) / NULLIF(COUNT(*), 0), 2) AS escalation_rate_pct
FROM ticket_metrics
GROUP BY agent_name, team, shift
ORDER BY tickets DESC;

