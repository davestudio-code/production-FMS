from decimal import Decimal
from production.db import fetchAll, fetchOne, execute, executeReturning
from production.cache import getCached, setCached, invalidateKeys
from .bomitem import BOMItem

class BillOfMaterials:
    def __init__(self, data=None):
        if data:
            self.bomID = data.get("bom_id")
            self.furnitureID = data.get("furniture_id")
        else:
            self.bomID = None
            self.furnitureID = None

    @classmethod
    def getByFurnitureID(cls, furnitureID, autoCreate=False, conn=None):
        cacheKey = f"bom_by_furn:{int(furnitureID)}"
        if conn is None:
            cached = getCached(cacheKey)
            if cached is not None:
                return cached

        row = fetchOne(
            "SELECT bom_id, furniture_id FROM prod_billofmaterials WHERE furniture_id = %s",
            (furnitureID,),
            conn=conn
        )
        if row:
            obj = cls(row)
            if conn is None:
                setCached(cacheKey, obj)
            return obj

        if autoCreate:
            execute(
                "INSERT INTO prod_billofmaterials (furniture_id) VALUES (%s) ON CONFLICT (furniture_id) DO NOTHING",
                (furnitureID,),
                conn=conn
            )
            newRow = fetchOne(
                "SELECT bom_id, furniture_id FROM prod_billofmaterials WHERE furniture_id = %s",
                (furnitureID,),
                conn=conn
            )
            if newRow:
                obj = cls(newRow)
                if conn is None:
                    setCached(cacheKey, obj)
                return obj

        return None

    def getItems(self, conn=None):
        cacheKey = f"bom_items:{int(self.bomID)}" if self.bomID is not None else None
        if conn is None and cacheKey:
            cached = getCached(cacheKey)
            if cached is not None:
                return cached

        sql = """
            SELECT bi.bom_item_id, bi.bom_id, bi.material_id, bi.quantity_required,
                   im.item_code, im.item_name AS material_name, im.unit, rm.unit_cost,
                   rm.quantity AS current_stock
            FROM prod_bomitem bi
            JOIN raw_material rm ON bi.material_id = rm.raw_material_id
            JOIN item_master im ON rm.item_id = im.item_id
            WHERE bi.bom_id = %s
            ORDER BY bi.bom_item_id ASC
        """
        rows = fetchAll(sql, (self.bomID,), conn=conn)
        result = [BOMItem(row) for row in rows]
        if conn is None and cacheKey:
            setCached(cacheKey, result)
        return result

    @classmethod
    def getAllItemsByFurnitureMap(cls, conn=None):
        if conn is None:
            cached = getCached("bom_items_by_furniture")
            if cached is not None:
                return cached

        sql = """
            SELECT bom.furniture_id,
                   bi.bom_item_id, bi.bom_id, bi.material_id, bi.quantity_required,
                   im.item_code, im.item_name AS material_name, im.unit, rm.unit_cost,
                   rm.quantity AS current_stock
            FROM prod_billofmaterials bom
            JOIN prod_bomitem bi ON bom.bom_id = bi.bom_id
            JOIN raw_material rm ON bi.material_id = rm.raw_material_id
            JOIN item_master im ON rm.item_id = im.item_id
            ORDER BY bom.furniture_id ASC, bi.bom_item_id ASC
        """
        rows = fetchAll(sql, conn=conn)
        grouped = {}
        for row in rows:
            fid = row["furniture_id"]
            grouped.setdefault(fid, []).append(BOMItem(row))
        if conn is None:
            setCached("bom_items_by_furniture", grouped)
        return grouped

    def addMaterial(self, materialID, quantityRequired, conn=None):
        cleanQty = Decimal(str(quantityRequired))
        if cleanQty <= Decimal("0"):
            raise ValueError("Quantity required must be greater than 0.")
        if not cleanQty.is_finite() or cleanQty.is_nan():
            raise ValueError("Invalid quantity format.")

        sql = """
            INSERT INTO prod_bomitem (bom_id, material_id, quantity_required)
            VALUES (%s, %s, %s)
            ON CONFLICT (bom_id, material_id)
            DO UPDATE SET quantity_required = EXCLUDED.quantity_required
            RETURNING bom_item_id, (xmax <> 0) AS was_updated
        """
        res = executeReturning(sql, (self.bomID, materialID, cleanQty), conn=conn)
        invalidateKeys("furniture_all")
        return res["bom_item_id"], res["was_updated"]

    def removeMaterial(self, bomItemID, conn=None):
        execute(
            "DELETE FROM prod_bomitem WHERE bom_item_id = %s AND bom_id = %s",
            (bomItemID, self.bomID),
            conn=conn
        )
        invalidateKeys("furniture_all")
        return True

    def calculateRequirements(self, plannedQuantity, conn=None, items=None):
        if items is None:
            items = self.getItems(conn)
        multiplier = Decimal(str(plannedQuantity))
        calculatedList = []
        for item in items:
            batchQty = item.calculateQuantity(multiplier)
            batchCost = batchQty * item.unitCost
            calculatedList.append({
                "bomItemID": item.bomItemID,
                "materialID": item.materialID,
                "itemCode": item.itemCode,
                "materialName": item.materialName,
                "unit": item.unit,
                "unitCost": item.unitCost,
                "quantityRequired": item.quantityRequired,
                "batchQuantity": batchQty,
                "batchCost": batchCost
            })
        return calculatedList
