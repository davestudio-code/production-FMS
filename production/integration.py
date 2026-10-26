from decimal import Decimal
from production.db import openTransaction
from production.cache import getCached, setCached, invalidateKeys

def get_material_stock(materialID, conn=None):
    with openTransaction(conn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_stock FROM raw_material WHERE raw_material_id = %s",
                (materialID,)
            )
            row = cursor.fetchone()
            if row and row.get("current_stock") is not None:
                return Decimal(str(row["current_stock"]))
            return Decimal("0.000")

def deduct_material_stock(materialID, quantity, conn=None):
    deductQty = Decimal(str(quantity))
    if deductQty <= 0:
        raise ValueError("Deduct quantity must be greater than zero.")

    with openTransaction(conn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE raw_material SET current_stock = current_stock - %s WHERE raw_material_id = %s AND current_stock >= %s RETURNING current_stock",
                (deductQty, materialID, deductQty)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Insufficient stock to deduct {deductQty} for material ID {materialID}.")
            invalidateKeys("materials_all")
            return Decimal(str(row["current_stock"]))

def add_finished_goods_stock(furnitureID, quantity, conn=None):
    addQty = int(quantity)
    if addQty <= 0:
        raise ValueError("Finished goods quantity must be greater than zero.")

    with openTransaction(conn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT furniture_name, selling_price FROM prod_furniture WHERE furniture_id = %s",
                (furnitureID,)
            )
            furn = cursor.fetchone()
            if not furn:
                raise ValueError(f"Furniture ID {furnitureID} does not exist.")

            furnName = furn["furniture_name"]
            furnPrice = furn["selling_price"]
            itemCode = f"FG-{furnitureID:03d}"

            cursor.execute("""
                SELECT item_id
                FROM item_master
                WHERE (item_type = 'Finished Goods' AND LOWER(TRIM(item_name)) = LOWER(TRIM(%s)))
                   OR item_code = %s
                ORDER BY (CASE WHEN LOWER(TRIM(item_name)) = LOWER(TRIM(%s)) THEN 1 ELSE 2 END) ASC
                LIMIT 1
            """, (furnName, itemCode, furnName))
            itemRow = cursor.fetchone()
            if itemRow:
                itemID = itemRow["item_id"]
            else:
                cursor.execute("""
                    INSERT INTO item_master (item_code, item_name, unit, description, item_type)
                    VALUES (%s, %s, 'pcs', %s, 'Finished Goods')
                    RETURNING item_id
                """, (itemCode, furnName, f"Produced {furnName}"))
                itemID = cursor.fetchone()["item_id"]

            cursor.execute("""
                INSERT INTO finished_goods (item_id, product_name, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (item_id)
                DO UPDATE SET quantity = finished_goods.quantity + EXCLUDED.quantity,
                              unit_price = EXCLUDED.unit_price,
                              product_name = EXCLUDED.product_name
                RETURNING finished_goods_id, item_id, product_name, quantity, unit_price
            """, (itemID, furnName, addQty, furnPrice))
            row = cursor.fetchone()
            return row

def get_finished_goods_stock(furnitureID, conn=None):
    with openTransaction(conn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(fg.quantity, 0) AS quantity
                FROM prod_furniture f
                LEFT JOIN LATERAL (
                    SELECT im.item_id
                    FROM item_master im
                    WHERE (im.item_type = 'Finished Goods' AND LOWER(TRIM(item_name)) = LOWER(TRIM(f.furniture_name)))
                       OR im.item_code = 'FG-' || LPAD(f.furniture_id::text, 3, '0')
                    ORDER BY (CASE WHEN LOWER(TRIM(item_name)) = LOWER(TRIM(f.furniture_name)) THEN 1 ELSE 2 END) ASC
                    LIMIT 1
                ) im ON true
                LEFT JOIN finished_goods fg ON fg.item_id = im.item_id
                WHERE f.furniture_id = %s
            """, (furnitureID,))
            row = cursor.fetchone()
            return int(row["quantity"]) if row and row.get("quantity") is not None else 0

def get_warehouse_stockouts(conn=None):
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT f.furniture_id, f.furniture_name, f.furniture_type, f.selling_price,
                           COALESCE(fg.quantity, 0) AS current_stock,
                           act.order_id AS active_order_id,
                           act.status AS active_order_status,
                           act.planned_quantity AS active_order_qty,
                           COALESCE(bom_stat.item_count, 0) AS bom_item_count
                    FROM prod_furniture f
                    LEFT JOIN LATERAL (
                        SELECT im.item_id, im.item_code, im.item_name
                        FROM item_master im
                        WHERE (im.item_type = 'Finished Goods' AND LOWER(TRIM(item_name)) = LOWER(TRIM(f.furniture_name)))
                           OR im.item_code = 'FG-' || LPAD(f.furniture_id::text, 3, '0')
                        ORDER BY (CASE WHEN LOWER(TRIM(item_name)) = LOWER(TRIM(f.furniture_name)) THEN 1 ELSE 2 END) ASC
                        LIMIT 1
                    ) im ON true
                    LEFT JOIN finished_goods fg ON im.item_id = fg.item_id
                    LEFT JOIN LATERAL (
                        SELECT po.order_id, po.status, po.planned_quantity
                        FROM prod_productionorder po
                        WHERE po.furniture_id = f.furniture_id
                          AND po.status IN ('Draft', 'Released', 'In Progress')
                        ORDER BY po.order_id DESC
                        LIMIT 1
                    ) act ON true
                    LEFT JOIN LATERAL (
                        SELECT COUNT(bi.bom_item_id) AS item_count
                        FROM prod_billofmaterials bom
                        JOIN prod_bomitem bi ON bom.bom_id = bi.bom_id
                        WHERE bom.furniture_id = f.furniture_id
                    ) bom_stat ON true
                    WHERE COALESCE(fg.quantity, 0) <= 0
                    ORDER BY f.furniture_name ASC;
                """)
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
    except Exception:
        return []

def publish_production_cost(orderID, conn=None):
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT cost_id, order_id, material_cost, labor_cost, overhead_cost, total_cost, cost_date
                    FROM prod_productioncost
                    WHERE order_id = %s
                """, (orderID,))
                row = cursor.fetchone()
                if row:
                    return {
                        "costID": row["cost_id"],
                        "orderID": row["order_id"],
                        "materialCost": Decimal(str(row["material_cost"])),
                        "laborCost": Decimal(str(row["labor_cost"])),
                        "overheadCost": Decimal(str(row["overhead_cost"])),
                        "totalCost": Decimal(str(row["total_cost"])),
                        "costDate": str(row["cost_date"]) if row["cost_date"] else None
                    }
                return None
    except Exception:
        return None
