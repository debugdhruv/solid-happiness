SELECT category_name, subcategory, COUNT(*) AS tickets
FROM ticket_metrics
GROUP BY category_name, subcategory
ORDER BY tickets DESC;

