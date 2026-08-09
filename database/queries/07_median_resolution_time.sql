SELECT
    category_name,
    subcategory,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_hours)::numeric, 2) AS median_resolution_hours
FROM ticket_metrics
WHERE resolution_hours IS NOT NULL
GROUP BY category_name, subcategory
ORDER BY median_resolution_hours DESC;

