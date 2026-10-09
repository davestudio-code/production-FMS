from decimal import Decimal
from production.db import openTransaction

class Material:
    def __init__(self, data=None):
        if data:
            self.materialID = data.get("material_id")
            self.materialName = data.get("material_name")
            self.unit = data.get("unit")
            rawCost = data.get("unit_cost")
            self.unitCost = Decimal(str(rawCost)) if rawCost is not None else Decimal("0.00")
            rawStock = data.get("current_stock")
            self.currentStock = Decimal(str(rawStock)) if rawStock is not None else Decimal("0.000")
        else:
            self.materialID = None
            self.materialName = ""
            self.unit = ""
            self.unitCost = Decimal("0.00")
            self.currentStock = Decimal("0.000")

    @classmethod
    def getAll(cls, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT rm.raw_material_id AS material_id,
                           im.item_name AS material_name,
                           im.unit,
                           rm.unit_cost,
                           rm.current_stock
                    FROM raw_material rm
                    JOIN item_master im ON rm.item_id = im.item_id
                    ORDER BY im.item_name ASC
                    """
                )
                rows = cursor.fetchall()
                return [cls(row) for row in rows]

    @classmethod
    def getByID(cls, materialID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT rm.raw_material_id AS material_id,
                           im.item_name AS material_name,
                           im.unit,
                           rm.unit_cost,
                           rm.current_stock
                    FROM raw_material rm
                    JOIN item_master im ON rm.item_id = im.item_id
                    WHERE rm.raw_material_id = %s
                    """,
                    (materialID,)
                )
                row = cursor.fetchone()
                return cls(row) if row else None
