SELECT DATE_TRUNC('day', created_at)::date AS ticket_day, COUNT(*) AS tickets
FROM tickets
GROUP BY ticket_day
ORDER BY ticket_day;

