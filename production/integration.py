from decimal import Decimal
from production.db import fetchAll, fetchOne, execute, executeReturning
from production.cache import getCached, setCached, invalidateKeys
from production.timefmt import toManilaDatetime

def get_material_stock(materialID, conn=None):
    row = fetchOne(
        "SELECT quantity FROM raw_material WHERE raw_material_id = %s",
        (materialID,),
        conn=conn
    )
    if row and row.get("quantity") is not None:
        return Decimal(str(row["quantity"]))
    return Decimal("0.000")

def _resolve_warehouse_id_for_item(itemID, conn=None):
    if itemID is not None:
        imRow = fetchOne(
            "SELECT warehouse_id FROM item_master WHERE item_id = %s",
            (itemID,),
            conn=conn
        )
        if imRow and imRow.get("warehouse_id") is not None:
            return int(imRow["warehouse_id"])
        try:
            sioRow = fetchOne(
                "SELECT warehouse_id FROM stock_in_out WHERE item_id = %s AND warehouse_id IS NOT NULL ORDER BY transaction_id DESC LIMIT 1",
                (itemID,),
                conn=conn
            )
            if sioRow and sioRow.get("warehouse_id") is not None:
                return int(sioRow["warehouse_id"])
        except Exception:
            pass
    try:
        whRow = fetchOne(
            "SELECT warehouse_id FROM warehouse WHERE status IS NULL OR LOWER(TRIM(status)) = 'active' ORDER BY warehouse_id ASC LIMIT 1",
            conn=conn
        )
        if not whRow:
            whRow = fetchOne("SELECT warehouse_id FROM warehouse ORDER BY warehouse_id ASC LIMIT 1", conn=conn)
        if whRow and whRow.get("warehouse_id") is not None:
            return int(whRow["warehouse_id"])
    except Exception:
        pass
    return None

def _log_stock_in_out(itemID, warehouseID, transactionType, quantity, remarks=None, rawMaterialID=None, conn=None):
    targetWarehouseID = int(warehouseID) if warehouseID is not None else _resolve_warehouse_id_for_item(itemID, conn=conn)
    if itemID is None or targetWarehouseID is None:
        return None
    cleanRemarks = (str(remarks or "").strip()[:255]) or None
    return executeReturning(
        """
        INSERT INTO stock_in_out (item_id, warehouse_id, transaction_type, quantity, remarks, raw_material_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING transaction_id
        """,
        (itemID, targetWarehouseID, transactionType, float(quantity), cleanRemarks, rawMaterialID),
        conn=conn
    )

def deduct_material_stock(materialID, quantity, remarks=None, conn=None):
    deductQty = Decimal(str(quantity))
    if deductQty <= 0:
        raise ValueError("Deduct quantity must be greater than zero.")

    row = executeReturning(
        "UPDATE raw_material SET quantity = quantity - %s WHERE raw_material_id = %s AND quantity >= %s RETURNING quantity, item_id",
        (deductQty, materialID, deductQty),
        conn=conn
    )
    if not row:
        raise ValueError(f"Insufficient stock to deduct {deductQty} for material ID {materialID}.")
    itemID = row.get("item_id")
    execute(
        "UPDATE item_master SET quantity = CASE WHEN quantity >= %s THEN quantity - %s ELSE 0.0 END WHERE item_id = %s",
        (float(deductQty), float(deductQty), itemID),
        conn=conn
    )
    _log_stock_in_out(
        itemID=itemID,
        warehouseID=None,
        transactionType="OUT",
        quantity=deductQty,
        remarks=remarks or f"Material issuance (RM #{materialID})",
        rawMaterialID=materialID,
        conn=conn
    )
    invalidateKeys("materials_all", "warehouse_stockouts")
    return Decimal(str(row["quantity"]))

def get_warehouses(conn=None):
    if conn is None:
        cached = getCached("warehouses_active")
        if cached is not None:
            return cached
    try:
        rows = fetchAll("""
            SELECT warehouse_id, warehouse_name, location, status
            FROM warehouse
            WHERE status IS NULL OR LOWER(TRIM(status)) = 'active'
            ORDER BY warehouse_id ASC
        """, conn=conn)
        result = [dict(r) for r in (rows or [])]
    except Exception:
        return []
    if conn is None:
        setCached("warehouses_active", result)
    return result

def add_finished_goods_stock(furnitureID, quantity, warehouseID=None, orderID=None, conn=None):
    addQty = int(quantity)
    if addQty <= 0:
        raise ValueError("Finished goods quantity must be greater than zero.")

    resolvedWarehouseID = None
    if warehouseID is not None and str(warehouseID).strip() != "":
        resolvedWarehouseID = int(warehouseID)
        whRow = fetchOne(
            "SELECT warehouse_id FROM warehouse WHERE warehouse_id = %s",
            (resolvedWarehouseID,),
            conn=conn
        )
        if not whRow:
            raise ValueError(f"Warehouse ID {resolvedWarehouseID} does not exist.")

    furn = fetchOne(
        "SELECT furniture_name FROM prod_furniture WHERE furniture_id = %s",
        (furnitureID,),
        conn=conn
    )
    if not furn:
        raise ValueError(f"Furniture ID {furnitureID} does not exist.")

    furnName = furn["furniture_name"]
    furnPrice = Decimal("0.00")
    itemCode = f"FG-{furnitureID:03d}"

    itemRow = fetchOne("""
        SELECT item_id
        FROM item_master
        WHERE (item_type IN ('Finished Goods', 'FINISHED') AND LOWER(TRIM(item_name)) = LOWER(TRIM(%s)))
           OR item_code = %s
        ORDER BY (CASE WHEN LOWER(TRIM(item_name)) = LOWER(TRIM(%s)) THEN 1 ELSE 2 END) ASC
        LIMIT 1
    """, (furnName, itemCode, furnName), conn=conn)

    if itemRow:
        itemID = itemRow["item_id"]
        if resolvedWarehouseID is not None:
            execute("""
                UPDATE item_master
                SET quantity = COALESCE(quantity, 0) + %s,
                    item_type = CASE WHEN item_type = 'Finished Goods' THEN 'FINISHED' ELSE item_type END,
                    warehouse_id = %s,
                    is_archived = false
                WHERE item_id = %s
            """, (float(addQty), resolvedWarehouseID, itemID), conn=conn)
        else:
            execute("""
                UPDATE item_master
                SET quantity = COALESCE(quantity, 0) + %s,
                    item_type = CASE WHEN item_type = 'Finished Goods' THEN 'FINISHED' ELSE item_type END,
                    is_archived = false
                WHERE item_id = %s
            """, (float(addQty), itemID), conn=conn)
    else:
        itemRow = executeReturning("""
            INSERT INTO item_master (item_code, item_name, unit, description, item_type, quantity, warehouse_id, is_archived)
            VALUES (%s, %s, 'pcs', %s, 'FINISHED', %s, %s, false)
            RETURNING item_id
        """, (itemCode, furnName, f"Produced {furnName}", float(addQty), resolvedWarehouseID), conn=conn)
        itemID = itemRow["item_id"]

    row = executeReturning("""
        INSERT INTO finished_goods (item_id, product_name, quantity, unit_price)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (item_id)
        DO UPDATE SET quantity = finished_goods.quantity + EXCLUDED.quantity,
                      unit_price = EXCLUDED.unit_price,
                      product_name = EXCLUDED.product_name
        RETURNING finished_goods_id, item_id, product_name, quantity, unit_price
    """, (itemID, furnName, addQty, furnPrice), conn=conn)
    if resolvedWarehouseID is not None:
        fgRemark = f"Production QC passed #PO-{orderID}" if orderID else f"Production QC passed ({furnName})"
        _log_stock_in_out(
            itemID=itemID,
            warehouseID=resolvedWarehouseID,
            transactionType="IN",
            quantity=addQty,
            remarks=fgRemark,
            rawMaterialID=None,
            conn=conn
        )
    invalidateKeys("materials_all", "warehouse_stockouts")
    return row

def get_finished_goods_stock(furnitureID, conn=None):
    row = fetchOne("""
        SELECT COALESCE(fg.quantity, 0) AS quantity
        FROM prod_furniture f
        LEFT JOIN LATERAL (
            SELECT im.item_id
            FROM item_master im
            WHERE (im.item_type IN ('Finished Goods', 'FINISHED') AND LOWER(TRIM(item_name)) = LOWER(TRIM(f.furniture_name)))
               OR im.item_code = 'FG-' || LPAD(f.furniture_id::text, 3, '0')
            ORDER BY (CASE WHEN LOWER(TRIM(item_name)) = LOWER(TRIM(f.furniture_name)) THEN 1 ELSE 2 END) ASC
            LIMIT 1
        ) im ON true
        LEFT JOIN finished_goods fg ON fg.item_id = im.item_id
        WHERE f.furniture_id = %s
    """, (furnitureID,), conn=conn)
    return int(row["quantity"]) if row and row.get("quantity") is not None else 0

def get_warehouse_stockouts(conn=None):
    if conn is None:
        cached = getCached("warehouse_stockouts")
        if cached is not None:
            return cached
    try:
        rows = fetchAll("""
            SELECT f.furniture_id, f.furniture_name, f.furniture_type,
                   COALESCE(fg.quantity, 0) AS current_stock,
                   act.order_id AS active_order_id,
                   act.status AS active_order_status,
                   act.planned_quantity AS active_order_qty,
                   COALESCE(act_agg.active_order_count, 0) AS active_order_count,
                   COALESCE(act_agg.total_incoming_qty, 0) AS total_incoming_qty,
                   COALESCE(bom_stat.item_count, 0) AS bom_item_count
            FROM prod_furniture f
            LEFT JOIN LATERAL (
                SELECT im.item_id, im.item_code, im.item_name
                FROM item_master im
                WHERE (im.item_type IN ('Finished Goods', 'FINISHED') AND LOWER(TRIM(item_name)) = LOWER(TRIM(f.furniture_name)))
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
            SELECT COUNT(*) AS active_order_count,
                   COALESCE(SUM(po.planned_quantity), 0) AS total_incoming_qty
            FROM prod_productionorder po
            WHERE po.furniture_id = f.furniture_id
              AND po.status IN ('Draft', 'Released', 'In Progress')
        ) act_agg ON true
        LEFT JOIN LATERAL (
            SELECT COUNT(bi.bom_item_id) AS item_count
            FROM prod_billofmaterials bom
            JOIN prod_bomitem bi ON bom.bom_id = bi.bom_id
            WHERE bom.furniture_id = f.furniture_id
        ) bom_stat ON true
        WHERE COALESCE(fg.quantity, 0) <= 0
        ORDER BY f.furniture_name ASC;
    """, conn=conn)
        result = [dict(r) for r in rows]
        if conn is None:
            setCached("warehouse_stockouts", result)
        return result
    except Exception:
        return []

def publish_production_cost(orderID, conn=None):
    try:
        row = fetchOne("""
            SELECT cost_id, order_id, material_cost, labor_cost, overhead_cost, total_cost, cost_date
            FROM prod_productioncost
            WHERE order_id = %s
        """, (orderID,), conn=conn)
        if row:
            return {
                "costID": row["cost_id"],
                "orderID": row["order_id"],
                "materialCost": Decimal(str(row["material_cost"])),
                "laborCost": Decimal(str(row["labor_cost"])),
                "overheadCost": Decimal(str(row["overhead_cost"])),
                "totalCost": Decimal(str(row["total_cost"])),
                "costDate": toManilaDatetime(row["cost_date"]).isoformat() if row["cost_date"] else None
            }
        return None
    except Exception:
        return None
