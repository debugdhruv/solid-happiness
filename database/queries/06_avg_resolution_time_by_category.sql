SELECT category_name, subcategory, ROUND(AVG(resolution_hours)::numeric, 2) AS avg_resolution_hours
FROM ticket_metrics
WHERE resolution_hours IS NOT NULL
GROUP BY category_name, subcategory
ORDER BY avg_resolution_hours DESC;

