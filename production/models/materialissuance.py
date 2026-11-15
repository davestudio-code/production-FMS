from decimal import Decimal
from production.db import fetchAll, fetchOne, executeReturning
from production.timefmt import formatManilaDateTime, toManilaIsoDate

class MaterialIssuance:
    VALID_ISSUANCE_TYPES = ("Initial", "Rework Replacement")

    def __init__(self, data=None):
        if data:
            self.issuanceID = data.get("issuance_id")
            self.orderID = data.get("order_id")
            self.materialID = data.get("material_id")
            rawQty = data.get("quantity_issued")
            self.quantityIssued = Decimal(str(rawQty)) if rawQty is not None else Decimal("0.000")
            self.issueDate = data.get("issue_date")
            self.recordedBy = data.get("recorded_by") or "Manager"
            self.issuanceType = data.get("issuance_type") or "Initial"
            self.reason = data.get("reason") or ""
            self.reworkRound = int(data.get("rework_round") or 0)
            rawUnitCost = data.get("unit_cost")
            self.unitCost = Decimal(str(rawUnitCost)) if rawUnitCost is not None else Decimal("0.00")
            self.materialName = data.get("material_name", f"Material #{self.materialID}")
            self.unit = data.get("unit", "")
            self.furnitureName = data.get("furniture_name", "")
        else:
            self.issuanceID = None
            self.orderID = None
            self.materialID = None
            self.quantityIssued = Decimal("0.000")
            self.issueDate = None
            self.recordedBy = "Manager"
            self.issuanceType = "Initial"
            self.reason = ""
            self.reworkRound = 0
            self.unitCost = Decimal("0.00")
            self.materialName = ""
            self.unit = ""
            self.furnitureName = ""

    @property
    def formattedIssueDate(self):
        return formatManilaDateTime(self.issueDate)

    @property
    def issueDateIso(self):
        return toManilaIsoDate(self.issueDate)

    @property
    def lineCost(self):
        return (self.quantityIssued * self.unitCost).quantize(Decimal("0.01"))

    @property
    def isReworkReplacement(self):
        return self.issuanceType == "Rework Replacement"

    @classmethod
    def recordIssuance(cls, orderID, materialID, quantityIssued, recordedBy=None, issuanceType="Initial", reason=None, reworkRound=0, conn=None):
        qtyVal = Decimal(str(quantityIssued))
        if not qtyVal.is_finite() or qtyVal.is_nan() or qtyVal <= 0:
            raise ValueError("Issued quantity must be greater than zero.")

        cleanType = (issuanceType or "Initial").strip()
        if cleanType not in cls.VALID_ISSUANCE_TYPES:
            raise ValueError(f"Invalid issuance type '{cleanType}'.")

        cleanRound = int(reworkRound or 0)
        if cleanRound < 0:
            raise ValueError("Rework round cannot be negative.")

        cleanReason = reason.strip() if reason is not None else ""
        dbReason = cleanReason if cleanReason else None
        if cleanType == "Rework Replacement":
            if not dbReason:
                raise ValueError("Reason is required for rework replacement issuance.")
            if len(dbReason) > 255:
                raise ValueError("Replacement reason cannot exceed 255 characters.")
            if cleanRound <= 0:
                raise ValueError("Rework round must be at least 1 for replacement issuance.")
        elif dbReason and len(dbReason) > 255:
            raise ValueError("Issuance reason cannot exceed 255 characters.")

        issuerName = (recordedBy or "").strip() or "Manager"
        sql = """
            INSERT INTO prod_materialissuance (
                order_id, material_id, quantity_issued, issue_date, recorded_by, issuance_type, reason, rework_round
            )
            VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s)
            RETURNING issuance_id, order_id, material_id, quantity_issued, issue_date, recorded_by, issuance_type, reason, rework_round
        """
        row = executeReturning(sql, (orderID, materialID, qtyVal, issuerName, cleanType, dbReason, cleanRound), conn=conn)
        return cls(row)

    @classmethod
    def getIssuedForRound(cls, orderID, materialID, reworkRound, conn=None):
        row = fetchOne(
            """
            SELECT COALESCE(SUM(quantity_issued), 0.000) AS total_issued
            FROM prod_materialissuance
            WHERE order_id = %s
              AND material_id = %s
              AND issuance_type = 'Rework Replacement'
              AND rework_round = %s
            """,
            (orderID, materialID, int(reworkRound)),
            conn=conn
        )
        if row and row.get("total_issued") is not None:
            return Decimal(str(row["total_issued"]))
        return Decimal("0.000")

    @classmethod
    def getInitialCountForOrder(cls, orderID, conn=None):
        row = fetchOne(
            """
            SELECT COUNT(*) AS cnt
            FROM prod_materialissuance
            WHERE order_id = %s
              AND issuance_type = 'Initial'
            """,
            (orderID,),
            conn=conn
        )
        return int(row["cnt"]) if row else 0

    @classmethod
    def getAll(cls, conn=None):
        sql = """
            SELECT mi.issuance_id,
                   mi.order_id,
                   mi.material_id,
                   mi.quantity_issued,
                   mi.issue_date,
                   mi.recorded_by,
                   COALESCE(mi.issuance_type, 'Initial') AS issuance_type,
                   mi.reason,
                   COALESCE(mi.rework_round, 0) AS rework_round,
                   rm.unit_cost,
                   im.item_name AS material_name,
                   im.unit AS unit,
                   f.furniture_name AS furniture_name
            FROM prod_materialissuance mi
            JOIN raw_material rm ON mi.material_id = rm.raw_material_id
            JOIN item_master im ON rm.item_id = im.item_id
            JOIN prod_productionorder po ON mi.order_id = po.order_id
            JOIN prod_furniture f ON po.furniture_id = f.furniture_id
            ORDER BY mi.issuance_id DESC
        """
        rows = fetchAll(sql, conn=conn)
        return [cls(r) for r in rows]

    @classmethod
    def getByOrderID(cls, orderID, conn=None):
        sql = """
            SELECT mi.issuance_id,
                   mi.order_id,
                   mi.material_id,
                   mi.quantity_issued,
                   mi.issue_date,
                   mi.recorded_by,
                   COALESCE(mi.issuance_type, 'Initial') AS issuance_type,
                   mi.reason,
                   COALESCE(mi.rework_round, 0) AS rework_round,
                   rm.unit_cost,
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
        """
        rows = fetchAll(sql, (orderID,), conn=conn)
        return [cls(r) for r in rows]
