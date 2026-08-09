SELECT EXTRACT(hour FROM created_at)::int AS hour_of_day, COUNT(*) AS tickets
FROM tickets
GROUP BY hour_of_day
ORDER BY hour_of_day;

