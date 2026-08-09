WITH weekly AS (
    SELECT DATE_TRUNC('week', created_at)::date AS week_start, COUNT(*) AS tickets
    FROM tickets
    GROUP BY week_start
),
monthly AS (
    SELECT DATE_TRUNC('month', created_at)::date AS month_start, COUNT(*) AS tickets
    FROM tickets
    GROUP BY month_start
)
SELECT 'week' AS period_type, week_start AS period_start, tickets,
       tickets - LAG(tickets) OVER (ORDER BY week_start) AS change_from_previous
FROM weekly
UNION ALL
SELECT 'month' AS period_type, month_start AS period_start, tickets,
       tickets - LAG(tickets) OVER (ORDER BY month_start) AS change_from_previous
FROM monthly
ORDER BY period_type, period_start;

