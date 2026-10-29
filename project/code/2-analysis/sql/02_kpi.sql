-- Query KPI. {t} = v_raw_prod atau v_anon_prod; {d} = v_raw_defect atau v_anon_defect; {first}/{last} = stasiun pertama/terakhir lini.
-- name: line_yield
SELECT SUM(CASE WHEN station = '{last}' THEN input - ng END) / SUM(CASE WHEN station = '{first}' THEN input END) AS line_yield FROM {t};
-- name: station_ng_rate
SELECT station, SUM(ng) / SUM(input) AS ng_rate, RANK() OVER (ORDER BY SUM(ng) / SUM(input) DESC) AS rnk
FROM {t} GROUP BY station ORDER BY rnk, station;
-- name: pareto
SELECT defect_code, SUM(qty) AS qty, SUM(qty) / SUM(SUM(qty)) OVER () AS share FROM {d} GROUP BY defect_code ORDER BY qty DESC, defect_code;
-- name: weekly_yield
SELECT week, SUM(CASE WHEN station = '{last}' THEN input - ng END) / SUM(CASE WHEN station = '{first}' THEN input END) AS line_yield
FROM {t} GROUP BY week ORDER BY week;
-- name: yield_by_model
SELECT model, SUM(CASE WHEN station = '{last}' THEN input - ng END) / SUM(CASE WHEN station = '{first}' THEN input END) AS line_yield
FROM {t} GROUP BY model ORDER BY model;
-- name: yield_by_shift
SELECT shift, SUM(CASE WHEN station = '{last}' THEN input - ng END) / SUM(CASE WHEN station = '{first}' THEN input END) AS line_yield
FROM {t} GROUP BY shift ORDER BY shift;
