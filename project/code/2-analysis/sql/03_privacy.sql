-- Ukuran risiko pada kombinasi quasi-identifier. {t} = view; {cols} = daftar kolom kombinasi.
-- name: k_anonymity
WITH g AS (SELECT COUNT(*) AS n FROM {t} GROUP BY {cols})
SELECT COUNT(*) AS n_groups, SUM(n) AS n_rows, MIN(n) AS k_min, MEDIAN(n) AS k_median,
       SUM(CASE WHEN n = 1 THEN 1 ELSE 0 END) * 1.0 / SUM(n) AS pct_unique FROM g;
-- name: operators_per_cell
SELECT station, shift, COUNT(DISTINCT operator) AS n_operators FROM {t} GROUP BY station, shift ORDER BY station, shift;
