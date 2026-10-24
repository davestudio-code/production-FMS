INSERT INTO prod_furniture (furniture_id, furniture_name, furniture_type, selling_price) VALUES
(1, 'Dining Chair', 'Seating', 4500.00),
(2, 'Dining Table', 'Table', 18000.00),
(3, '3-Door Cabinet', 'Storage', 22000.00)
ON CONFLICT (furniture_id) DO NOTHING;

SELECT setval(pg_get_serial_sequence('prod_furniture', 'furniture_id'), COALESCE(MAX(furniture_id), 1)) FROM prod_furniture;

INSERT INTO prod_material (material_id, material_name, unit, unit_cost) VALUES
(1, 'Mahogany lumber', 'board ft', 180.00),
(2, 'Plywood 3/4"', 'sheet', 1450.00),
(3, 'Screws', 'pcs', 2.50),
(4, 'Wood glue', 'liter', 320.00),
(5, 'Drawer handles', 'pcs', 85.00),
(6, 'Wood stain', 'liter', 450.00),
(7, 'Varnish', 'liter', 520.00),
(8, 'Sandpaper', 'sheet', 25.00),
(9, 'Foam', 'pcs', 150.00),
(10, 'Fabric', 'meter', 280.00)
ON CONFLICT (material_id) DO NOTHING;

SELECT setval(pg_get_serial_sequence('prod_material', 'material_id'), COALESCE(MAX(material_id), 1)) FROM prod_material;

INSERT INTO prod_billofmaterials (bom_id, furniture_id) VALUES
(1, 1),
(2, 2),
(3, 3)
ON CONFLICT (bom_id) DO NOTHING;

SELECT setval(pg_get_serial_sequence('prod_billofmaterials', 'bom_id'), COALESCE(MAX(bom_id), 1)) FROM prod_billofmaterials;

INSERT INTO prod_bomitem (bom_item_id, bom_id, material_id, quantity_required) VALUES
(1, 1, 1, 6.000),
(2, 1, 3, 12.000),
(3, 1, 4, 0.100),
(4, 1, 7, 0.200),
(5, 1, 8, 2.000),
(6, 1, 9, 1.000),
(7, 1, 10, 0.500),
(8, 2, 1, 20.000),
(9, 2, 2, 1.000),
(10, 2, 3, 24.000),
(11, 2, 4, 0.300),
(12, 2, 6, 0.500),
(13, 2, 7, 0.600),
(14, 2, 8, 4.000),
(15, 3, 1, 10.000),
(16, 3, 2, 3.000),
(17, 3, 3, 40.000),
(18, 3, 4, 0.400),
(19, 3, 5, 3.000),
(20, 3, 6, 0.500),
(21, 3, 7, 0.600),
(22, 3, 8, 5.000)
ON CONFLICT (bom_item_id) DO NOTHING;

SELECT setval(pg_get_serial_sequence('prod_bomitem', 'bom_item_id'), COALESCE(MAX(bom_item_id), 1)) FROM prod_bomitem;
