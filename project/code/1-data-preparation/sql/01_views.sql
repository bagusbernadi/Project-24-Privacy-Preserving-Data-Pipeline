-- View seragam untuk data asli (raw) dan data anonim (anon): kolom sama, jadi query sama persis dipakai di keduanya.
-- raw_production memuat kolom tambahan week (ISO) dan operator_norm (nama dinormalkan) yang dihitung di Python saat memuat.
-- name: v_raw_prod
CREATE OR REPLACE VIEW v_raw_prod AS
SELECT date, week, shift, station, model, operator_norm AS operator, input_qty AS input, ng_qty AS ng FROM raw_production;
-- name: v_anon_prod
CREATE OR REPLACE VIEW v_anon_prod AS
SELECT week, shift, station, model, operator_code AS operator, input_index AS input, ng_index AS ng FROM anon_production;
-- name: v_raw_defect
CREATE OR REPLACE VIEW v_raw_defect AS
SELECT week, shift, station, model, defect_code, qty FROM raw_defect;
-- name: v_anon_defect
CREATE OR REPLACE VIEW v_anon_defect AS
SELECT week, shift, station, model, defect_code, qty_index AS qty FROM anon_defect;
