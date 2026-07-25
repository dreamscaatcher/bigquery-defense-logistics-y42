CREATE CONSTRAINT depot_id_unique IF NOT EXISTS
FOR (d:Depot) REQUIRE d.depot_id IS UNIQUE;

CREATE CONSTRAINT route_id_unique IF NOT EXISTS
FOR (r:Route) REQUIRE r.route_id IS UNIQUE;

CREATE CONSTRAINT requisition_id_unique IF NOT EXISTS
FOR (q:Requisition) REQUIRE q.requisition_id IS UNIQUE;

CREATE INDEX requisition_date_index IF NOT EXISTS
FOR (q:Requisition) ON (q.request_date);

CREATE INDEX depot_country_index IF NOT EXISTS
FOR (d:Depot) ON (d.country_code);