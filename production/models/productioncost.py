from decimal import Decimal
from datetime import date
from production.db import openTransaction

class ProductionCost:
    DEFAULT_OVERHEAD_PERCENT = Decimal("0.10")

    def __init__(self, data=None):
        if data:
            self.costID = data.get("cost_id")
            self.orderID = data.get("order_id")
            rawMat = data.get("material_cost")
            self.materialCost = Decimal(str(rawMat)) if rawMat is not None else Decimal("0.00")
            rawLab = data.get("labor_cost")
            self.laborCost = Decimal(str(rawLab)) if rawLab is not None else Decimal("0.00")
            rawOver = data.get("overhead_cost")
            self.overheadCost = Decimal(str(rawOver)) if rawOver is not None else Decimal("0.00")
            rawTot = data.get("total_cost")
            self.totalCost = Decimal(str(rawTot)) if rawTot is not None else Decimal("0.00")
            self.costDate = data.get("cost_date")
            self.furnitureName = data.get("furniture_name", "")
            self.furnitureType = data.get("furniture_type", "")
            self.plannedQuantity = int(data.get("planned_quantity", 0))
            self.orderStatus = data.get("order_status", "")
        else:
            self.costID = None
            self.orderID = None
            self.materialCost = Decimal("0.00")
            self.laborCost = Decimal("0.00")
            self.overheadCost = Decimal("0.00")
            self.totalCost = Decimal("0.00")
            self.costDate = None
            self.furnitureName = ""
            self.furnitureType = ""
            self.plannedQuantity = 0
            self.orderStatus = ""

    @property
    def unitCost(self):
        if self.plannedQuantity and self.plannedQuantity > 0:
            return (self.totalCost / Decimal(str(self.plannedQuantity))).quantize(Decimal("0.01"))
        return Decimal("0.00")

    @classmethod
    def calculateCostPerGoodUnit(cls, orderID, totalCost, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(SUM(quantity), 0) AS passed_units
                    FROM prod_productionoutput
                    WHERE order_id = %s AND quality_status = 'Passed'
                """, (orderID,))
                row = cursor.fetchone()
                passedUnits = int(row["passed_units"]) if row else 0
                if passedUnits <= 0:
                    return None, 0
                goodCost = (Decimal(str(totalCost)) / Decimal(str(passedUnits))).quantize(Decimal("0.01"))
                return goodCost, passedUnits

    @property
    def formattedCostDate(self):
        if not self.costDate:
            return "-"
        try:
            return self.costDate.strftime("%b %d, %Y")
        except AttributeError:
            return str(self.costDate)

    @classmethod
    def calculateOverhead(cls, materialCost):
        return (Decimal(str(materialCost)) * cls.DEFAULT_OVERHEAD_PERCENT).quantize(Decimal("0.01"))

    @classmethod
    def getAll(cls, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.cost_id,
                           c.order_id,
                           c.material_cost,
                           c.labor_cost,
                           c.overhead_cost,
                           c.total_cost,
                           c.cost_date,
                           po.planned_quantity,
                           po.status AS order_status,
                           f.furniture_name,
                           f.furniture_type
                    FROM prod_productioncost c
                    JOIN prod_productionorder po ON c.order_id = po.order_id
                    JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                    ORDER BY c.cost_id DESC
                """)
                rows = cursor.fetchall()
                return [cls(r) for r in rows]

    @classmethod
    def getByOrderID(cls, orderID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.cost_id,
                           c.order_id,
                           c.material_cost,
                           c.labor_cost,
                           c.overhead_cost,
                           c.total_cost,
                           c.cost_date,
                           po.planned_quantity,
                           po.status AS order_status,
                           f.furniture_name,
                           f.furniture_type
                    FROM prod_productioncost c
                    JOIN prod_productionorder po ON c.order_id = po.order_id
                    JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                    WHERE c.order_id = %s
                """, (orderID,))
                row = cursor.fetchone()
                return cls(row) if row else None

    @classmethod
    def calculateActualMaterialCost(cls, orderID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(SUM(mi.quantity_issued * rm.unit_cost), 0.00) AS actual_cost
                    FROM prod_materialissuance mi
                    JOIN raw_material rm ON mi.material_id = rm.raw_material_id
                    WHERE mi.order_id = %s
                """, (orderID,))
                row = cursor.fetchone()
                actualCost = Decimal(str(row["actual_cost"])) if row and row.get("actual_cost") is not None else Decimal("0.00")
                if actualCost > Decimal("0.00"):
                    return actualCost.quantize(Decimal("0.01"))

                cursor.execute("""
                    SELECT COALESCE(SUM(bi.quantity_required * po.planned_quantity * rm.unit_cost), 0.00) AS bom_cost
                    FROM prod_productionorder po
                    JOIN prod_billofmaterials bom ON po.furniture_id = bom.furniture_id
                    JOIN prod_bomitem bi ON bom.bom_id = bi.bom_id
                    JOIN raw_material rm ON bi.material_id = rm.raw_material_id
                    WHERE po.order_id = %s
                """, (orderID,))
                rowBom = cursor.fetchone()
                bomCost = Decimal(str(rowBom["bom_cost"])) if rowBom and rowBom.get("bom_cost") is not None else Decimal("0.00")
                return bomCost.quantize(Decimal("0.01"))

    @classmethod
    def saveCost(cls, orderID, materialCost, laborCost, overheadCost=None, conn=None):
        mat = Decimal(str(materialCost)).quantize(Decimal("0.01"))
        lab = Decimal(str(laborCost)).quantize(Decimal("0.01"))
        if mat < Decimal("0.00") or lab < Decimal("0.00"):
            raise ValueError("Costs cannot be negative.")

        if overheadCost is not None:
            over = Decimal(str(overheadCost)).quantize(Decimal("0.01"))
        else:
            over = cls.calculateOverhead(mat)

        if over < Decimal("0.00"):
            raise ValueError("Overhead cost cannot be negative.")

        total = mat + lab + over

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO prod_productioncost (order_id, material_cost, labor_cost, overhead_cost, total_cost, cost_date)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
                    ON CONFLICT (order_id)
                    DO UPDATE SET material_cost = EXCLUDED.material_cost,
                                  labor_cost = EXCLUDED.labor_cost,
                                  overhead_cost = EXCLUDED.overhead_cost,
                                  total_cost = EXCLUDED.total_cost,
                                  cost_date = CURRENT_DATE
                    RETURNING cost_id, order_id, material_cost, labor_cost, overhead_cost, total_cost, cost_date
                """, (orderID, mat, lab, over, total))
                row = cursor.fetchone()
                return cls(row)
