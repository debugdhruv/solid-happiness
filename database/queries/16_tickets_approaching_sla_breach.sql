SELECT ticket_id, category_name, subcategory, priority, status, hours_open, sla_hours, agent_name, shift
FROM ticket_metrics
WHERE resolved_at IS NULL
  AND hours_open BETWEEN sla_hours * 0.8 AND sla_hours
ORDER BY sla_hours - hours_open ASC;

