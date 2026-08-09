WITH stats AS (
    SELECT
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY resolution_hours) AS q3,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY resolution_hours) AS q1
    FROM ticket_metrics
    WHERE resolution_hours IS NOT NULL
)
SELECT ticket_id, category_name, subcategory, priority, resolution_hours, sla_hours, agent_name, root_cause
FROM ticket_metrics, stats
WHERE resolution_hours IS NOT NULL
  AND resolution_hours > q3 + 1.5 * (q3 - q1)
ORDER BY resolution_hours DESC
LIMIT 100;

