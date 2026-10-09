from decimal import Decimal
from production.db import openTransaction

class Furniture:
    def __init__(self, data=None):
        if data:
            self.furnitureID = data.get("furniture_id")
            self.furnitureName = data.get("furniture_name")
            self.furnitureType = data.get("furniture_type")
            rawPrice = data.get("selling_price")
            self.sellingPrice = Decimal(str(rawPrice)) if rawPrice is not None else Decimal("0.00")
        else:
            self.furnitureID = None
            self.furnitureName = ""
            self.furnitureType = ""
            self.sellingPrice = Decimal("0.00")

    @classmethod
    def getAll(cls, searchQuery=None, category=None, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                sql = "SELECT furniture_id, furniture_name, furniture_type, selling_price FROM prod_furniture WHERE 1=1"
                params = []
                if searchQuery:
                    sql += " AND furniture_name ILIKE %s"
                    params.append(f"%{searchQuery.strip()}%")
                if category:
                    sql += " AND furniture_type = %s"
                    params.append(category.strip())
                sql += " ORDER BY furniture_id ASC"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                return [cls(row) for row in rows]

    @classmethod
    def getCategories(cls, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT furniture_type FROM prod_furniture WHERE furniture_type IS NOT NULL AND furniture_type != '' ORDER BY furniture_type ASC")
                rows = cursor.fetchall()
                return [row["furniture_type"] for row in rows]

    @classmethod
    def getByID(cls, furnitureID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT furniture_id, furniture_name, furniture_type, selling_price FROM prod_furniture WHERE furniture_id = %s", (furnitureID,))
                row = cursor.fetchone()
                return cls(row) if row else None

    @classmethod
    def existsByName(cls, furnitureName, excludeID=None, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                if excludeID:
                    cursor.execute("SELECT 1 FROM prod_furniture WHERE LOWER(TRIM(furniture_name)) = LOWER(TRIM(%s)) AND furniture_id != %s", (furnitureName, excludeID))
                else:
                    cursor.execute("SELECT 1 FROM prod_furniture WHERE LOWER(TRIM(furniture_name)) = LOWER(TRIM(%s))", (furnitureName,))
                return cursor.fetchone() is not None

    @classmethod
    def addFurniture(cls, furnitureName, furnitureType, sellingPrice, conn=None):
        cleanName = furnitureName.strip()
        cleanType = furnitureType.strip()
        priceVal = Decimal(str(sellingPrice))
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO prod_furniture (furniture_name, furniture_type, selling_price) VALUES (%s, %s, %s) RETURNING furniture_id, furniture_name, furniture_type, selling_price",
                    (cleanName, cleanType, priceVal)
                )
                row = cursor.fetchone()
                return cls(row)

    @classmethod
    def updateFurniture(cls, furnitureID, furnitureName, furnitureType, sellingPrice, conn=None):
        cleanName = furnitureName.strip()
        cleanType = furnitureType.strip()
        priceVal = Decimal(str(sellingPrice))
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE prod_furniture SET furniture_name = %s, furniture_type = %s, selling_price = %s WHERE furniture_id = %s RETURNING furniture_id, furniture_name, furniture_type, selling_price",
                    (cleanName, cleanType, priceVal, furnitureID)
                )
                row = cursor.fetchone()
                return cls(row) if row else None

    @classmethod
    def canDelete(cls, furnitureID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS count FROM prod_bomitem bi JOIN prod_billofmaterials b ON bi.bom_id = b.bom_id WHERE b.furniture_id = %s",
                    (furnitureID,)
                )
                bomItemCount = cursor.fetchone()["count"]
                if bomItemCount > 0:
                    return False, f"Cannot delete: Product has {bomItemCount} active Bill of Materials item(s) attached."

                cursor.execute("SELECT COUNT(*) AS count FROM prod_productionorder WHERE furniture_id = %s", (furnitureID,))
                orderCount = cursor.fetchone()["count"]
                if orderCount > 0:
                    return False, f"Cannot delete: Product is referenced in {orderCount} production order(s)."

                cursor.execute("SELECT COUNT(*) AS count FROM prod_productionoutput WHERE furniture_id = %s", (furnitureID,))
                fgCount = cursor.fetchone()["count"]
                if fgCount > 0:
                    return False, f"Cannot delete: Product is referenced in {fgCount} finished goods inspection record(s)."

                return True, ""

    @classmethod
    def deleteFurniture(cls, furnitureID, conn=None):
        can, reason = cls.canDelete(furnitureID, conn)
        if not can:
            raise ValueError(reason)

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM prod_furniture WHERE furniture_id = %s", (furnitureID,))
                return True
