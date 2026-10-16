from datetime import date
from production.db import openTransaction

class ProductionOutput:
    VALID_STATUSES = ("Pending", "Passed", "Failed", "Rework")

    def __init__(self, data=None):
        if data:
            self.outputID = data.get("output_id")
            self.orderID = data.get("order_id")
            self.furnitureID = data.get("furniture_id")
            self.quantity = int(data.get("quantity", 0))
            self.qualityStatus = data.get("quality_status", "Pending")
            self.inspectionDate = data.get("inspection_date")
            self.furnitureName = data.get("furniture_name", "")
            self.furnitureType = data.get("furniture_type", "")
        else:
            self.outputID = None
            self.orderID = None
            self.furnitureID = None
            self.quantity = 0
            self.qualityStatus = "Pending"
            self.inspectionDate = None
            self.furnitureName = ""
            self.furnitureType = ""

    @property
    def formattedInspectionDate(self):
        if not self.inspectionDate:
            return "-"
        try:
            return self.inspectionDate.strftime("%b %d, %Y")
        except AttributeError:
            return str(self.inspectionDate)

    @classmethod
    def recordOutput(cls, orderID, furnitureID, quantity, qualityStatus="Passed", conn=None):
        if qualityStatus not in cls.VALID_STATUSES:
            raise ValueError(f"Invalid quality status '{qualityStatus}'. Allowed: {cls.VALID_STATUSES}")
        if int(quantity) < 0:
            raise ValueError("Quantity cannot be negative.")

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO prod_productionoutput (order_id, furniture_id, quantity, quality_status, inspection_date)
                    VALUES (%s, %s, %s, %s, CURRENT_DATE)
                    RETURNING output_id, order_id, furniture_id, quantity, quality_status, inspection_date
                """, (orderID, furnitureID, quantity, qualityStatus))
                row = cursor.fetchone()
                return cls(row)

    @classmethod
    def getAll(cls, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT o.output_id,
                           o.order_id,
                           o.furniture_id,
                           o.quantity,
                           o.quality_status,
                           o.inspection_date,
                           f.furniture_name,
                           f.furniture_type
                    FROM prod_productionoutput o
                    JOIN prod_furniture f ON o.furniture_id = f.furniture_id
                    ORDER BY o.output_id DESC
                """)
                rows = cursor.fetchall()
                return [cls(r) for r in rows]

    @classmethod
    def getByOrderID(cls, orderID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT o.output_id,
                           o.order_id,
                           o.furniture_id,
                           o.quantity,
                           o.quality_status,
                           o.inspection_date,
                           f.furniture_name,
                           f.furniture_type
                    FROM prod_productionoutput o
                    JOIN prod_furniture f ON o.furniture_id = f.furniture_id
                    WHERE o.order_id = %s
                    ORDER BY o.output_id DESC
                """, (orderID,))
                rows = cursor.fetchall()
                return [cls(r) for r in rows]
