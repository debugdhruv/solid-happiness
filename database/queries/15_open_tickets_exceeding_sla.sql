SELECT ticket_id, category_name, subcategory, priority, status, hours_open, sla_hours, agent_name, shift
FROM ticket_metrics
WHERE resolved_at IS NULL
  AND hours_open > sla_hours
ORDER BY hours_open - sla_hours DESC;

