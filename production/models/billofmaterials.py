from decimal import Decimal
from production.db import openTransaction
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
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT bom_id, furniture_id FROM prod_billofmaterials WHERE furniture_id = %s",
                    (furnitureID,)
                )
                row = cursor.fetchone()
                if row:
                    return cls(row)

                if autoCreate:
                    cursor.execute(
                        "INSERT INTO prod_billofmaterials (furniture_id) VALUES (%s) ON CONFLICT (furniture_id) DO NOTHING",
                        (furnitureID,)
                    )
                    cursor.execute(
                        "SELECT bom_id, furniture_id FROM prod_billofmaterials WHERE furniture_id = %s",
                        (furnitureID,)
                    )
                    newRow = cursor.fetchone()
                    if newRow:
                        return cls(newRow)

                return None

    def getItems(self, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT bi.bom_item_id, bi.bom_id, bi.material_id, bi.quantity_required,
                           im.item_name AS material_name, im.unit, rm.unit_cost
                    FROM prod_bomitem bi
                    JOIN raw_material rm ON bi.material_id = rm.raw_material_id
                    JOIN item_master im ON rm.item_id = im.item_id
                    WHERE bi.bom_id = %s
                    ORDER BY bi.bom_item_id ASC
                    """,
                    (self.bomID,)
                )
                rows = cursor.fetchall()
                return [BOMItem(row) for row in rows]

    def addMaterial(self, materialID, quantityRequired, conn=None):
        cleanQty = Decimal(str(quantityRequired))
        if cleanQty <= Decimal("0"):
            raise ValueError("Quantity required must be greater than 0.")
        if not cleanQty.is_finite() or cleanQty.is_nan():
            raise ValueError("Invalid quantity format.")

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO prod_bomitem (bom_id, material_id, quantity_required)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (bom_id, material_id)
                    DO UPDATE SET quantity_required = EXCLUDED.quantity_required
                    RETURNING bom_item_id, (xmax <> 0) AS was_updated
                    """,
                    (self.bomID, materialID, cleanQty)
                )
                res = cursor.fetchone()
                return res["bom_item_id"], res["was_updated"]

    def removeMaterial(self, bomItemID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM prod_bomitem WHERE bom_item_id = %s AND bom_id = %s",
                    (bomItemID, self.bomID)
                )
                return True

    def calculateRequirements(self, plannedQuantity, conn=None):
        items = self.getItems(conn)
        multiplier = Decimal(str(plannedQuantity))
        calculatedList = []
        for item in items:
            batchQty = item.calculateQuantity(multiplier)
            batchCost = batchQty * item.unitCost
            calculatedList.append({
                "bomItemID": item.bomItemID,
                "materialID": item.materialID,
                "materialName": item.materialName,
                "unit": item.unit,
                "unitCost": item.unitCost,
                "quantityRequired": item.quantityRequired,
                "batchQuantity": batchQty,
                "batchCost": batchCost
            })
        return calculatedList
