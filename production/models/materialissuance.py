from decimal import Decimal
from production.db import openTransaction

class MaterialIssuance:
    def __init__(self, data=None):
        if data:
            self.issuanceID = data.get("issuance_id")
            self.orderID = data.get("order_id")
            self.materialID = data.get("material_id")
            rawQty = data.get("quantity_issued")
            self.quantityIssued = Decimal(str(rawQty)) if rawQty is not None else Decimal("0.000")
            self.issueDate = data.get("issue_date")
            self.materialName = data.get("material_name", f"Material #{self.materialID}")
            self.unit = data.get("unit", "")
            self.furnitureName = data.get("furniture_name", "")
        else:
            self.issuanceID = None
            self.orderID = None
            self.materialID = None
            self.quantityIssued = Decimal("0.000")
            self.issueDate = None
            self.materialName = ""
            self.unit = ""
            self.furnitureName = ""

    @classmethod
    def recordIssuance(cls, orderID, materialID, quantityIssued, conn=None):
        qtyVal = Decimal(str(quantityIssued))
        if qtyVal <= 0:
            raise ValueError("Issued quantity must be greater than zero.")

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO prod_materialissuance (order_id, material_id, quantity_issued, issue_date) VALUES (%s, %s, %s, CURRENT_DATE) RETURNING issuance_id, order_id, material_id, quantity_issued, issue_date",
                    (orderID, materialID, qtyVal)
                )
                row = cursor.fetchone()
                return cls(row)

    @classmethod
    def getAll(cls, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT mi.issuance_id,
                           mi.order_id,
                           mi.material_id,
                           mi.quantity_issued,
                           mi.issue_date,
                           im.item_name AS material_name,
                           im.unit AS unit,
                           f.furniture_name AS furniture_name
                    FROM prod_materialissuance mi
                    JOIN raw_material rm ON mi.material_id = rm.raw_material_id
                    JOIN item_master im ON rm.item_id = im.item_id
                    JOIN prod_productionorder po ON mi.order_id = po.order_id
                    JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                    ORDER BY mi.issuance_id DESC
                """)
                rows = cursor.fetchall()
                return [cls(r) for r in rows]

    @classmethod
    def getByOrderID(cls, orderID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT mi.issuance_id,
                           mi.order_id,
                           mi.material_id,
                           mi.quantity_issued,
                           mi.issue_date,
                           im.item_name AS material_name,
                           im.unit AS unit,
                           f.furniture_name AS furniture_name
                    FROM prod_materialissuance mi
                    JOIN raw_material rm ON mi.material_id = rm.raw_material_id
                    JOIN item_master im ON rm.item_id = im.item_id
                    JOIN prod_productionorder po ON mi.order_id = po.order_id
                    JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                    WHERE mi.order_id = %s
                    ORDER BY mi.issuance_id ASC
                """, (orderID,))
                rows = cursor.fetchall()
                return [cls(r) for r in rows]
