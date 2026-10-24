CREATE UNIQUE INDEX IF NOT EXISTS uq_prod_material_name
  ON prod_material (LOWER(material_name));

INSERT INTO prod_material (material_name, unit, unit_cost) VALUES
  ('Mahogany lumber', 'board ft', 180.00),
  ('Plywood 3/4"',    'sheet',    1450.00),
  ('Screws',          'pcs',      2.50),
  ('Wood glue',       'liter',    320.00),
  ('Drawer handles',  'pcs',      85.00),
  ('Wood stain',      'liter',    450.00),
  ('Varnish',         'liter',    520.00),
  ('Sandpaper',       'sheet',    25.00),
  ('Foam',            'pcs',      150.00),
  ('Fabric',          'meter',    280.00)
ON CONFLICT DO NOTHING;
