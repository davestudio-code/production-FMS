CREATE TABLE IF NOT EXISTS prod_furniture (
    furniture_id SERIAL PRIMARY KEY,
    furniture_name VARCHAR(100) NOT NULL,
    furniture_type VARCHAR(50) NOT NULL,
    selling_price NUMERIC(12, 2) NOT NULL CHECK (selling_price >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_prod_furniture_name ON prod_furniture (LOWER(furniture_name));

CREATE TABLE IF NOT EXISTS prod_billofmaterials (
    bom_id SERIAL PRIMARY KEY,
    furniture_id INT NOT NULL REFERENCES prod_furniture(furniture_id) ON DELETE CASCADE,
    CONSTRAINT uq_prod_bom_furniture UNIQUE (furniture_id)
);

CREATE TABLE IF NOT EXISTS prod_bomitem (
    bom_item_id SERIAL PRIMARY KEY,
    bom_id INT NOT NULL REFERENCES prod_billofmaterials(bom_id) ON DELETE CASCADE,
    material_id INT NOT NULL REFERENCES raw_material(raw_material_id) ON DELETE CASCADE,
    quantity_required NUMERIC(12, 3) NOT NULL CHECK (quantity_required > 0),
    CONSTRAINT uq_prod_bomitem_bom_material UNIQUE (bom_id, material_id)
);

CREATE TABLE IF NOT EXISTS prod_productionorder (
    order_id SERIAL PRIMARY KEY,
    furniture_id INT NOT NULL REFERENCES prod_furniture(furniture_id),
    planned_quantity INT NOT NULL CHECK (planned_quantity > 0),
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    planned_start_date DATE,
    due_date DATE,
    purpose VARCHAR(50) NOT NULL DEFAULT 'Warehouse Restock',
    status VARCHAR(30) NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft', 'Released', 'In Progress', 'Completed'))
);

CREATE TABLE IF NOT EXISTS prod_materialissuance (
    issuance_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES prod_productionorder(order_id) ON DELETE CASCADE,
    material_id INT NOT NULL REFERENCES raw_material(raw_material_id) ON DELETE CASCADE,
    quantity_issued NUMERIC(12, 3) NOT NULL CHECK (quantity_issued > 0),
    issue_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS prod_productionmonitoring (
    monitoring_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL UNIQUE REFERENCES prod_productionorder(order_id) ON DELETE CASCADE,
    progress NUMERIC(5, 2) NOT NULL DEFAULT 0.0 CHECK (progress >= 0 AND progress <= 100),
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    completion_date DATE NULL
);

CREATE TABLE IF NOT EXISTS prod_productionoutput (
    output_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES prod_productionorder(order_id) ON DELETE CASCADE,
    furniture_id INT NOT NULL REFERENCES prod_furniture(furniture_id),
    quantity INT NOT NULL CHECK (quantity >= 0),
    quality_status VARCHAR(30) NOT NULL DEFAULT 'Pending' CHECK (quality_status IN ('Pending', 'Passed', 'Failed', 'Rework')),
    inspection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (order_id, quality_status)
);

CREATE TABLE IF NOT EXISTS prod_productioncost (
    cost_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL UNIQUE REFERENCES prod_productionorder(order_id) ON DELETE CASCADE,
    material_cost NUMERIC(12, 2) NOT NULL DEFAULT 0.0 CHECK (material_cost >= 0),
    labor_cost NUMERIC(12, 2) NOT NULL DEFAULT 0.0 CHECK (labor_cost >= 0),
    overhead_cost NUMERIC(12, 2) NOT NULL DEFAULT 0.0 CHECK (overhead_cost >= 0),
    total_cost NUMERIC(12, 2) NOT NULL DEFAULT 0.0 CHECK (total_cost >= 0),
    cost_date DATE NOT NULL DEFAULT CURRENT_DATE
);
