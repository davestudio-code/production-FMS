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
