SELECT priority, COUNT(*) AS tickets
FROM tickets
GROUP BY priority
ORDER BY priority;

