SELECT COALESCE(root_cause, 'Missing') AS root_cause, COUNT(*) AS tickets
FROM tickets
GROUP BY COALESCE(root_cause, 'Missing')
ORDER BY tickets DESC
LIMIT 15;

