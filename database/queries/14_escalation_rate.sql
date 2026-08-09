SELECT
    COUNT(*) AS tickets,
    COUNT(*) FILTER (WHERE escalation_flag) AS escalations,
    ROUND(100.0 * COUNT(*) FILTER (WHERE escalation_flag) / NULLIF(COUNT(*), 0), 2) AS escalation_rate_pct
FROM tickets;

