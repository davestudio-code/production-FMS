from decimal import Decimal
from production.db import openTransaction
from production.cache import getCached, setCached, invalidateKeys

class Furniture:
    def __init__(self, data=None):
        if data:
            self.furnitureID = data.get("furniture_id")
            self.furnitureName = data.get("furniture_name")
            self.furnitureType = data.get("furniture_type")
            rawPrice = data.get("selling_price")
            self.sellingPrice = Decimal(str(rawPrice)) if rawPrice is not None else Decimal("0.00")
            rawBomCost = data.get("bom_material_cost")
            self.bomCost = Decimal(str(rawBomCost)) if rawBomCost is not None else Decimal("0.00")
            self.componentCount = int(data.get("component_count") or 0)
            self.hasBOM = self.componentCount > 0
            self.bomID = data.get("bom_id")
        else:
            self.furnitureID = None
            self.furnitureName = ""
            self.furnitureType = ""
            self.sellingPrice = Decimal("0.00")
            self.bomCost = Decimal("0.00")
            self.componentCount = 0
            self.hasBOM = False
            self.bomID = None

    @classmethod
    def getAll(cls, searchQuery=None, category=None, conn=None):
        if not searchQuery and not category and conn is None:
            cached = getCached("furniture_all")
            if cached is not None:
                return cached

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                sql = """
                    SELECT f.furniture_id, f.furniture_name, f.furniture_type, f.selling_price,
                           bom.bom_id,
                           COALESCE(SUM(bi.quantity_required * rm.unit_cost), 0.00) AS bom_material_cost,
                           COUNT(bi.bom_item_id) AS component_count
                    FROM prod_furniture f
                    LEFT JOIN prod_billofmaterials bom ON f.furniture_id = bom.furniture_id
                    LEFT JOIN prod_bomitem bi ON bom.bom_id = bi.bom_id
                    LEFT JOIN raw_material rm ON bi.material_id = rm.raw_material_id
                    WHERE 1=1
                """
                params = []
                if searchQuery:
                    sql += " AND f.furniture_name ILIKE %s"
                    params.append(f"%{searchQuery.strip()}%")
                if category:
                    sql += " AND f.furniture_type = %s"
                    params.append(category.strip())
                sql += " GROUP BY f.furniture_id, f.furniture_name, f.furniture_type, f.selling_price, bom.bom_id ORDER BY f.furniture_id ASC"
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                result = [cls(row) for row in rows]
                if not searchQuery and not category and conn is None:
                    setCached("furniture_all", result)
                return result

    @classmethod
    def getCategories(cls, conn=None):
        if conn is None:
            cached = getCached("furniture_categories")
            if cached is not None:
                return cached

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT furniture_type FROM prod_furniture WHERE furniture_type IS NOT NULL AND furniture_type != '' ORDER BY furniture_type ASC")
                rows = cursor.fetchall()
                result = [row["furniture_type"] for row in rows]
                if conn is None:
                    setCached("furniture_categories", result)
                return result

    @classmethod
    def getByID(cls, furnitureID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                sql = """
                    SELECT f.furniture_id, f.furniture_name, f.furniture_type, f.selling_price,
                           bom.bom_id,
                           COALESCE(SUM(bi.quantity_required * rm.unit_cost), 0.00) AS bom_material_cost,
                           COUNT(bi.bom_item_id) AS component_count
                    FROM prod_furniture f
                    LEFT JOIN prod_billofmaterials bom ON f.furniture_id = bom.furniture_id
                    LEFT JOIN prod_bomitem bi ON bom.bom_id = bi.bom_id
                    LEFT JOIN raw_material rm ON bi.material_id = rm.raw_material_id
                    WHERE f.furniture_id = %s
                    GROUP BY f.furniture_id, f.furniture_name, f.furniture_type, f.selling_price, bom.bom_id
                """
                cursor.execute(sql, (furnitureID,))
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
    def addFurniture(cls, furnitureName, furnitureType, sellingPrice=Decimal("0.00"), conn=None):
        cleanName = furnitureName.strip()
        cleanType = furnitureType.strip()
        priceVal = Decimal(str(sellingPrice)) if sellingPrice is not None else Decimal("0.00")
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO prod_furniture (furniture_name, furniture_type, selling_price) VALUES (%s, %s, %s) RETURNING furniture_id, furniture_name, furniture_type, selling_price",
                    (cleanName, cleanType, priceVal)
                )
                row = cursor.fetchone()
                invalidateKeys("furniture_all", "furniture_categories")
                return cls(row)

    @classmethod
    def updateFurniture(cls, furnitureID, furnitureName, furnitureType, sellingPrice=Decimal("0.00"), conn=None):
        cleanName = furnitureName.strip()
        cleanType = furnitureType.strip()
        priceVal = Decimal(str(sellingPrice)) if sellingPrice is not None else Decimal("0.00")
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE prod_furniture SET furniture_name = %s, furniture_type = %s, selling_price = %s WHERE furniture_id = %s RETURNING furniture_id, furniture_name, furniture_type, selling_price",
                    (cleanName, cleanType, priceVal, furnitureID)
                )
                row = cursor.fetchone()
                invalidateKeys("furniture_all", "furniture_categories")
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
                invalidateKeys("furniture_all", "furniture_categories")
                return True
