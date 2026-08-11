"""演示数据初始化"""
from datetime import datetime, timezone
import random

def load_demo_data(db):
    """清空现有数据并加载演示数据"""
    from nongzi.models.product import Category, Product
    from nongzi.models.contact import Supplier, Customer
    from nongzi.models.inventory import Warehouse, Inventory, InventoryBatch
    from nongzi.models.purchase import PurchaseOrder, PurchaseItem
    from nongzi.models.sale import SaleOrder, SaleItem
    from nongzi.models.system import User, OperationLog
    from nongzi.models.finance import ARTransaction, APTransaction

    # Clear existing data (order matters for FK constraints)
    for model in [OperationLog, ARTransaction, APTransaction,
                  SaleItem, SaleOrder, PurchaseItem, PurchaseOrder,
                  InventoryBatch, Inventory, Product, Category,
                  Customer, Supplier, Warehouse]:
        db.query(model).delete()
    db.commit()

    # 1. Create warehouse
    wh = Warehouse(name="默认仓库", is_default=True)
    db.add(wh)
    db.flush()

    # 2. Create categories
    cats_data = [
        ("种子", None),
        ("农药", None),
        ("化肥", None),
        ("农膜", None),
        ("饲料", None),
        ("农具", None),
        ("其他", None),
    ]
    cats = {}
    for i, (name, _) in enumerate(cats_data):
        c = Category(name=name, sort_order=i, parent_id=None)
        db.add(c); db.flush(); cats[name] = c

    sub_cats = [
        ("水稻种子", cats["种子"].id), ("小麦种子", cats["种子"].id),
        ("玉米种子", cats["种子"].id), ("蔬菜种子", cats["种子"].id),
        ("杀虫剂", cats["农药"].id), ("杀菌剂", cats["农药"].id),
        ("除草剂", cats["农药"].id), ("植物生长调节剂", cats["农药"].id),
        ("氮肥", cats["化肥"].id), ("复合肥", cats["化肥"].id),
    ]
    for i, (name, pid) in enumerate(sub_cats):
        c = Category(name=name, sort_order=i, parent_id=pid)
        db.add(c); db.flush(); cats[name] = c

    # 3. Create suppliers
    suppliers_data = [
        {"name": "兴农种业有限公司", "contact": "张经理", "phone": "139-0001-0001", "address": "XX市XX区XX路100号"},
        {"name": "绿源农药批发", "contact": "李经理", "phone": "139-0002-0002", "address": "XX市XX区XX路200号"},
        {"name": "丰盛化肥经销部", "contact": "王经理", "phone": "139-0003-0003", "address": "XX市XX区XX路300号"},
    ]
    suppliers = []
    for s in suppliers_data:
        sup = Supplier(**s)
        db.add(sup); db.flush(); suppliers.append(sup)

    # 4. Create customers
    customers_data = [
        {"name": "张三", "phone": "138-1001-0001", "address": "XX村1组", "tag": "farmer"},
        {"name": "李四", "phone": "138-1002-0002", "address": "XX村2组", "tag": "farmer"},
        {"name": "王五合作社", "phone": "138-1003-0003", "address": "XX镇XX号", "tag": "cooperative"},
        {"name": "赵六种植基地", "phone": "138-1004-0004", "address": "XX乡XX村", "tag": "major_farmer"},
        {"name": "孙七", "phone": "138-1005-0005", "address": "XX村3组", "tag": "farmer"},
    ]
    customers = []
    for c in customers_data:
        cust = Customer(**c)
        db.add(cust); db.flush(); customers.append(cust)

    # 5. Create products
    pesticide_cat = cats.get("杀虫剂")
    fungicide_cat = cats.get("杀菌剂")
    herbicide_cat = cats.get("除草剂")
    rice_cat = cats.get("水稻种子")
    corn_cat = cats.get("玉米种子")
    fertilizer_cat = cats.get("复合肥")
    nitrogen_cat = cats.get("氮肥")
    film_cat = cats.get("农膜")

    products_data = [
        {"code": "SP-20260601-001", "generic_name": "吡虫啉", "trade_name": "一遍净", "barcode": "6901234001",
         "spec": "10g*500袋", "formulation": "可湿性粉剂", "content": "10%", "toxicity": "低毒",
         "manufacturer": "江苏扬农", "base_unit": "袋", "retail_price": 3.5, "ref_cost": 2.8, "category_id": pesticide_cat.id},
        {"code": "SP-20260601-002", "generic_name": "阿维菌素", "trade_name": "爱福丁", "barcode": "6901234002",
         "spec": "100ml*50瓶", "formulation": "乳油", "content": "1.8%", "toxicity": "低毒",
         "manufacturer": "深圳诺普信", "base_unit": "瓶", "retail_price": 12.0, "ref_cost": 9.0, "category_id": pesticide_cat.id},
        {"code": "SP-20260601-003", "generic_name": "草甘膦", "trade_name": "农达", "barcode": "6901234003",
         "spec": "200ml*40瓶", "formulation": "水剂", "content": "41%", "toxicity": "低毒",
         "manufacturer": "拜耳", "base_unit": "瓶", "retail_price": 18.0, "ref_cost": 14.0, "category_id": herbicide_cat.id},
        {"code": "SP-20260601-004", "generic_name": "多菌灵", "trade_name": "", "barcode": "6901234004",
         "spec": "400g*20袋", "formulation": "可湿性粉剂", "content": "50%", "toxicity": "低毒",
         "manufacturer": "江苏龙灯", "base_unit": "袋", "retail_price": 15.0, "ref_cost": 11.0, "category_id": fungicide_cat.id},
        {"code": "SP-20260601-005", "generic_name": "水稻种子", "trade_name": "丰两优香1号", "barcode": "6901234005",
         "spec": "1kg*30袋", "base_unit": "kg", "retail_price": 48.0, "ref_cost": 36.0, "category_id": rice_cat.id},
        {"code": "SP-20260601-006", "generic_name": "复合肥", "trade_name": "史丹利", "barcode": "6901234006",
         "spec": "50kg/袋", "content": "15-15-15", "base_unit": "袋", "retail_price": 180.0, "ref_cost": 150.0, "category_id": fertilizer_cat.id},
        {"code": "SP-20260601-007", "generic_name": "高效氯氟氰菊酯", "trade_name": "功夫", "barcode": "6901234007",
         "spec": "200ml*40瓶", "formulation": "乳油", "content": "2.5%", "toxicity": "中等毒",
         "manufacturer": "先正达", "base_unit": "瓶", "retail_price": 8.0, "ref_cost": 6.0,
         "category_id": pesticide_cat.id, "is_restricted": True, "restricted_max_quantity": 100},
        {"code": "SP-20260601-008", "generic_name": "农膜", "trade_name": "大棚膜", "barcode": "6901234008",
         "spec": "8m*50m/卷", "base_unit": "卷", "retail_price": 320.0, "ref_cost": 260.0, "category_id": film_cat.id if film_cat else None},
        {"code": "SP-20260601-009", "generic_name": "尿素", "trade_name": "", "barcode": "6901234009",
         "spec": "50kg/袋", "content": "含氮46%", "base_unit": "袋", "retail_price": 150.0, "ref_cost": 130.0, "category_id": nitrogen_cat.id if nitrogen_cat else None},
        {"code": "SP-20260601-010", "generic_name": "噻虫嗪", "trade_name": "阿克泰", "barcode": "6901234010",
         "spec": "10g*500袋", "formulation": "水分散粒剂", "content": "25%", "toxicity": "低毒",
         "manufacturer": "先正达", "base_unit": "袋", "retail_price": 5.0, "ref_cost": 3.8, "category_id": pesticide_cat.id},
        {"code": "SP-20260601-011", "generic_name": "玉米种子", "trade_name": "郑单958", "barcode": "6901234011",
         "spec": "4500粒/袋", "base_unit": "袋", "retail_price": 65.0, "ref_cost": 50.0, "category_id": corn_cat.id if corn_cat else None},
        {"code": "SP-20260601-012", "generic_name": "百草枯替代除草剂", "trade_name": "克无踪", "barcode": "6901234012",
         "spec": "200ml*20瓶", "formulation": "水剂", "content": "20%", "toxicity": "中等毒",
         "manufacturer": "浙江新安", "base_unit": "瓶", "retail_price": 15.0, "ref_cost": 11.5, "category_id": herbicide_cat.id},
    ]
    products = []
    for p in products_data:
        prod = Product(**p)
        db.add(prod); db.flush(); products.append(prod)
        init_qty = random.randint(20, 100)
        db.add(Inventory(product_id=prod.id, warehouse_id=wh.id, quantity=init_qty,
                         available_quantity=init_qty, cost_price=prod.ref_cost))

    db.commit()

    # 6. Create purchase orders
    po1 = PurchaseOrder(order_no="PO-20260628-001", supplier_id=suppliers[0].id, total_amount=1430.0, status="confirmed", order_date=datetime.now(timezone.utc))
    db.add(po1); db.flush()
    db.add(PurchaseItem(order_id=po1.id, product_id=products[0].id, quantity=100, unit_price=2.8, amount=280.0))
    db.add(PurchaseItem(order_id=po1.id, product_id=products[4].id, quantity=25, unit_price=36.0, amount=900.0))
    db.add(PurchaseItem(order_id=po1.id, product_id=products[9].id, quantity=50, unit_price=3.8, amount=190.0))

    po2 = PurchaseOrder(order_no="PO-20260628-002", supplier_id=suppliers[1].id, total_amount=2700.0, status="confirmed", order_date=datetime.now(timezone.utc))
    db.add(po2); db.flush()
    db.add(PurchaseItem(order_id=po2.id, product_id=products[1].id, quantity=60, unit_price=9.0, amount=540.0))
    db.add(PurchaseItem(order_id=po2.id, product_id=products[2].id, quantity=80, unit_price=14.0, amount=1120.0))
    db.add(PurchaseItem(order_id=po2.id, product_id=products[3].id, quantity=40, unit_price=11.0, amount=440.0))
    db.add(PurchaseItem(order_id=po2.id, product_id=products[6].id, quantity=60, unit_price=6.0, amount=360.0))

    po3 = PurchaseOrder(order_no="PO-20260628-003", supplier_id=suppliers[2].id, total_amount=4600.0, status="confirmed", order_date=datetime.now(timezone.utc))
    db.add(po3); db.flush()
    db.add(PurchaseItem(order_id=po3.id, product_id=products[5].id, quantity=20, unit_price=150.0, amount=3000.0))
    db.add(PurchaseItem(order_id=po3.id, product_id=products[8].id, quantity=10, unit_price=130.0, amount=1300.0))

    # 7. Create sale orders
    for i in range(10):
        cust = customers[i % len(customers)]
        prod = products[i % len(products)]
        qty = random.randint(1, 5)
        price = prod.retail_price or 10
        amount = round(qty * price, 2)
        so = SaleOrder(
            order_no=f"SO-20260628-{str(i+1).zfill(3)}",
            customer_id=cust.id if i % 3 == 0 else None,
            total_amount=amount,
            payment_method="cash" if i % 3 != 0 else "credit",
            is_paid=(i % 3 != 0),
            order_date=datetime.now(timezone.utc)
        )
        db.add(so); db.flush()
        db.add(SaleItem(order_id=so.id, product_id=prod.id, quantity=qty, unit_price=price, amount=amount))

    db.commit()
    print("[DemoData] 演示数据初始化完成")

