// neo4j/import/seed.cypher

// Constraint — run once at startup
CREATE CONSTRAINT substation_id IF NOT EXISTS
FOR (s:Substation) REQUIRE s.substation_id IS UNIQUE;

CREATE CONSTRAINT transformer_id IF NOT EXISTS
FOR (t:Transformer) REQUIRE t.asset_id IS UNIQUE;

CREATE CONSTRAINT gsp_id IF NOT EXISTS
FOR (g:GridSupplyPoint) REQUIRE g.gsp_id IS UNIQUE;

CREATE CONSTRAINT meter_id IF NOT EXISTS
FOR (m:SmartMeter) REQUIRE m.meter_id IS UNIQUE;

// ── Nodes ────────────────────────────────────────────────────────
// Grid Supply Point (top of hierarchy)
MERGE (g:GridSupplyPoint {gsp_id: "GSP_NORTH"})
SET g.name = "Northern Grid Supply Point",
    g.voltage_kV = 132,
    g.region = "North Metro";

// Substations
MERGE (s:Substation {substation_id: "SS_001"})
SET s.name = "Volos Primary",
    s.voltage_kV = 11,
    s.lat = 39.358,
    s.lon = 22.938,
    s.commissioned_year = 1998;

MERGE (s:Substation {substation_id: "SS_002"})
SET s.name = "Larissa Primary",
    s.voltage_kV = 11,
    s.lat = 39.637,
    s.lon = 22.420,
    s.commissioned_year = 2004;

MERGE (s:Substation {substation_id: "SS_003"})
SET s.name = "Trikala Primary",
    s.voltage_kV = 11,
    s.lat = 39.555,
    s.lon = 21.768,
    s.commissioned_year = 2001;

MERGE (s:Substation {substation_id: "SS_004"})
SET s.name = "Karditsa Primary",
    s.voltage_kV = 11,
    s.lat = 39.364,
    s.lon = 21.922,
    s.commissioned_year = 1995;

MERGE (s:Substation {substation_id: "SS_005"})
SET s.name = "Farsala Primary",
    s.voltage_kV = 11,
    s.lat = 39.295,
    s.lon = 22.385,
    s.commissioned_year = 2008;

MERGE (s:Substation {substation_id: "SS_006"})
SET s.name = "Tyrnavos Primary",
    s.voltage_kV = 11,
    s.lat = 39.738,
    s.lon = 22.289,
    s.commissioned_year = 2003;

MERGE (s:Substation {substation_id: "SS_007"})
SET s.name = "Elassona Primary",
    s.voltage_kV = 11,
    s.lat = 39.895,
    s.lon = 22.189,
    s.commissioned_year = 1990;

MERGE (s:Substation {substation_id: "SS_008"})
SET s.name = "Kalambaka Primary",
    s.voltage_kV = 11,
    s.lat = 39.704,
    s.lon = 21.627,
    s.commissioned_year = 2011;

MERGE (s:Substation {substation_id: "SS_009"})
SET s.name = "Almyros Primary",
    s.voltage_kV = 11,
    s.lat = 39.182,
    s.lon = 22.759,
    s.commissioned_year = 2006;

MERGE (s:Substation {substation_id: "SS_010"})
SET s.name = "Velestino Primary",
    s.voltage_kV = 11,
    s.lat = 39.382,
    s.lon = 22.744,
    s.commissioned_year = 1999;

// Generate 4 transformers for each of the 10 substations
UNWIND range(1, 10) AS i
UNWIND range(1, 4) AS j

WITH i, j,
     "TX_" + right("00" + toString(i), 3) + "_" +
     CASE j
         WHEN 1 THEN "A"
         WHEN 2 THEN "B"
         WHEN 3 THEN "C"
         ELSE "D"
     END AS asset_id,
     CASE j
         WHEN 1 THEN 400
         WHEN 2 THEN 630
         WHEN 3 THEN 800
         ELSE 1000
     END AS rating_kVA

MERGE (t:Transformer {asset_id: asset_id})

ON CREATE SET
    t.rating_kVA = rating_kVA,
    t.manufacturer =
        CASE (i + j) % 4
            WHEN 0 THEN "ABB"
            WHEN 1 THEN "Siemens Energy"
            WHEN 2 THEN "Schneider Electric"
            ELSE "Hitachi Energy"
        END,
    t.model =
        CASE (i + j) % 4
            WHEN 0 THEN "ABB-DT-" + toString(rating_kVA)
            WHEN 1 THEN "SIE-DT-" + toString(rating_kVA)
            WHEN 2 THEN "SCH-DT-" + toString(rating_kVA)
            ELSE "HIT-DT-" + toString(rating_kVA)
        END,
    t.installed = date("2010-01-01") + duration({days: i * 240 + j * 45}),
    t.last_inspection = date("2025-01-01") + duration({days: i * 20 + j * 7});

// Generate 5 smart meters for each of the 40 transformers
UNWIND range(1, 10) AS i
UNWIND range(1, 4) AS j
UNWIND range(1, 5) AS k

WITH i, j, k,
     ((i - 1) * 20) + ((j - 1) * 5) + k AS meter_number

WITH i, j, k, meter_number,
     "SM_" + right("00000" + toString(meter_number), 5) AS meter_id,
     "PREM_" + toString(10000 + meter_number) AS premise_id

MERGE (m:SmartMeter {meter_id: meter_id})

ON CREATE SET
    m.premise_id = premise_id,
    m.tariff_class =
        CASE meter_number % 5
            WHEN 0 THEN "commercial"
            WHEN 1 THEN "residential"
            WHEN 2 THEN "residential"
            WHEN 3 THEN "residential"
            ELSE "commercial"
        END,
    m.phase =
        CASE meter_number % 4
            WHEN 0 THEN "three"
            ELSE "single"
        END;

// ── Relationships ────────────────────────────────────────────────
// Grid Supply Point → Substations
MATCH (g:GridSupplyPoint {gsp_id: "GSP_NORTH"})
UNWIND range(1, 10) AS i

WITH g, i,
     "SS_" + right("00" + toString(i), 3) AS substation_id

MATCH (s:Substation {substation_id: substation_id})
MERGE (g)-[r:FEEDS]->(s)
SET r.feeder_id = "F_" + right("00" + toString(i), 3),
    r.voltage_kV = 11,
    r.length_km = 1.5 + i * 0.35;

// Substations → Transformers
UNWIND range(1, 10) AS i
UNWIND range(1, 4) AS j

WITH i, j,
     "SS_" + right("00" + toString(i), 3) AS substation_id,
     CASE j
         WHEN 1 THEN "A"
         WHEN 2 THEN "B"
         WHEN 3 THEN "C"
         ELSE "D"
     END AS transformer_letter

WITH i, j, substation_id, transformer_letter,
     "TX_" + right("00" + toString(i), 3) + "_" + transformer_letter AS asset_id

MATCH (s:Substation {substation_id: substation_id})
MATCH (t:Transformer {asset_id: asset_id})
MERGE (s)-[r:SUPPLIES]->(t)
SET r.cable_id = "CB_" + right("00" + toString(i), 3) + "_" + transformer_letter,
    r.distance_m = 180 + i * 25 + j * 40;

// Transformers → Smart Meters
UNWIND range(1, 10) AS i
UNWIND range(1, 4) AS j
UNWIND range(1, 5) AS k

WITH i, j, k,
     ((i - 1) * 20) + ((j - 1) * 5) + k AS meter_number,
     CASE j
         WHEN 1 THEN "A"
         WHEN 2 THEN "B"
         WHEN 3 THEN "C"
         ELSE "D"
     END AS transformer_letter

WITH meter_number,
     "TX_" + right("00" + toString(i), 3) + "_" + transformer_letter AS asset_id

WITH asset_id,
     "SM_" + right("00000" + toString(meter_number), 5) AS meter_id

MATCH (t:Transformer {asset_id: asset_id})
MATCH (m:SmartMeter {meter_id: meter_id})
MERGE (t)-[:CONNECTS_TO]->(m);