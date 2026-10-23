from decimal import Decimal
from production.db import openTransaction

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

            cursor.execute(
                "SELECT item_id FROM item_master WHERE item_code = %s OR (item_name = %s AND item_type = 'Finished Goods')",
                (itemCode, furnName)
            )
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
                SELECT fg.quantity
                FROM finished_goods fg
                JOIN item_master im ON fg.item_id = im.item_id
                WHERE im.item_code = %s OR (im.item_name = (SELECT furniture_name FROM prod_furniture WHERE furniture_id = %s))
            """, (f"FG-{furnitureID:03d}", furnitureID))
            row = cursor.fetchone()
            return int(row["quantity"]) if row and row.get("quantity") is not None else 0

def get_pending_sales_orders(conn=None):
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT so.order_id AS sales_order_id,
                           oi.order_item_id,
                           oi.quantity,
                           so.order_date,
                           so.status AS sales_status,
                           c.name AS customer_name,
                           COALESCE(im.item_name, 'Furniture Product') AS item_name,
                           f.furniture_id,
                           f.furniture_name
                    FROM salesorder so
                    JOIN customer c ON so.customer_id = c.customer_id
                    JOIN orderitem oi ON so.order_id = oi.order_id
                    LEFT JOIN item_master im ON oi.item_id = im.item_id
                    LEFT JOIN prod_furniture f ON LOWER(TRIM(f.furniture_name)) = LOWER(TRIM(im.item_name))
                    WHERE LOWER(so.status) IN ('pending', 'backorder', 'approved')
                       OR so.status IS NULL
                    ORDER BY so.order_id DESC, oi.order_item_id ASC;
                """)
                return cursor.fetchall()
    except Exception:
        return []
