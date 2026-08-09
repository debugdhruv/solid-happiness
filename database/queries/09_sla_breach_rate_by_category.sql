SELECT
    category_name,
    subcategory,
    COUNT(*) AS tickets,
    ROUND(100.0 * COUNT(*) FILTER (WHERE sla_breached) / NULLIF(COUNT(*), 0), 2) AS breach_rate_pct
FROM ticket_metrics
GROUP BY category_name, subcategory
ORDER BY breach_rate_pct DESC, tickets DESC;

