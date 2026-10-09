from decimal import Decimal

class BOMItem:
    def __init__(self, data=None):
        if data:
            self.bomItemID = data.get("bom_item_id")
            self.bomID = data.get("bom_id")
            self.materialID = data.get("material_id")
            rawQty = data.get("quantity_required")
            self.quantityRequired = Decimal(str(rawQty)) if rawQty is not None else Decimal("0.000")
            self.materialName = data.get("material_name", "")
            self.unit = data.get("unit", "")
            rawCost = data.get("unit_cost")
            self.unitCost = Decimal(str(rawCost)) if rawCost is not None else Decimal("0.00")
        else:
            self.bomItemID = None
            self.bomID = None
            self.materialID = None
            self.quantityRequired = Decimal("0.000")
            self.materialName = ""
            self.unit = ""
            self.unitCost = Decimal("0.00")

    def calculateQuantity(self, plannedQuantity):
        qtyMultiplier = Decimal(str(plannedQuantity))
        return self.quantityRequired * qtyMultiplier
