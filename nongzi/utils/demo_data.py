"""演示数据初始化 - 丰富版"""
from datetime import datetime, timedelta, timezone
import random
random.seed(42)

def load_demo_data(db):
    """清空现有数据并加载丰富演示数据"""
    from nongzi.models.product import Category, Product
    from nongzi.models.contact import Supplier, Customer
    from nongzi.models.inventory import Warehouse, Inventory, InventoryBatch
    from nongzi.models.purchase import PurchaseOrder, PurchaseItem
    from nongzi.models.sale import SaleOrder, SaleItem
    from nongzi.models.system import User, OperationLog
    from nongzi.models.finance import ARTransaction, APTransaction

    # Clear
    for model in [OperationLog, ARTransaction, APTransaction,
                  SaleItem, SaleOrder, PurchaseItem, PurchaseOrder,
                  InventoryBatch, Inventory, Product, Category,
                  Customer, Supplier, Warehouse]:
        db.query(model).delete()
    db.commit()

    # ===== 1. Warehouse =====
    wh = Warehouse(name="默认仓库", is_default=True)
    db.add(wh); db.flush()

    # ===== 2. Categories =====
    cat_data = [
        ("种子", None), ("农药", None), ("化肥", None), ("农膜", None),
        ("饲料", None), ("农具", None), ("其他", None),
    ]
    cats = {}
    for i, (name, _) in enumerate(cat_data):
        c = Category(name=name, sort_order=i, parent_id=None)
        db.add(c); db.flush(); cats[name] = c

    sub_data = [
        ("水稻种子", "种子"), ("小麦种子", "种子"), ("玉米种子", "种子"),
        ("蔬菜种子", "种子"), ("豆类种子", "种子"),
        ("杀虫剂", "农药"), ("杀菌剂", "农药"), ("除草剂", "农药"),
        ("植物生长调节剂", "农药"), ("杀螨剂", "农药"),
        ("氮肥", "化肥"), ("磷肥", "化肥"), ("钾肥", "化肥"), ("复合肥", "化肥"),
        ("有机肥", "化肥"), ("水溶肥", "化肥"),
        ("地膜", "农膜"), ("大棚膜", "农膜"), ("遮阳网", "农膜"),
        ("猪饲料", "饲料"), ("鸡饲料", "饲料"), ("鱼饲料", "饲料"),
        ("喷雾器", "农具"), ("锄头", "农具"), ("镰刀", "农具"), ("水管", "农具"),
    ]
    for i, (name, parent) in enumerate(sub_data):
        c = Category(name=name, sort_order=i, parent_id=cats[parent].id)
        db.add(c); db.flush(); cats[name] = c

    # ===== 3. Suppliers (8) =====
    sup_data = [
        {"name": "兴农种业有限公司", "contact": "张经理", "phone": "139-0001-0001", "address": "XX市XX区XX路100号"},
        {"name": "绿源农药批发", "contact": "李经理", "phone": "139-0002-0002", "address": "XX市XX区XX路200号"},
        {"name": "丰盛化肥经销部", "contact": "王经理", "phone": "139-0003-0003", "address": "XX市XX区XX路300号"},
        {"name": "大棚物资供应站", "contact": "赵老板", "phone": "139-0004-0004", "address": "XX市XX区XX路400号"},
        {"name": "正大饲料代理", "contact": "钱经理", "phone": "139-0005-0005", "address": "XX市XX区XX路500号"},
        {"name": "农机具批发城", "contact": "周老板", "phone": "139-0006-0006", "address": "XX市XX区XX路600号"},
        {"name": "省农资总公司", "contact": "吴经理", "phone": "139-0007-0007", "address": "XX市XX区XX路700号"},
        {"name": "华农生物科技", "contact": "郑经理", "phone": "139-0008-0008", "address": "XX市XX区XX路800号"},
    ]
    suppliers = []
    for s in sup_data:
        sup = Supplier(**s)
        db.add(sup); db.flush(); suppliers.append(sup)

    # ===== 4. Customers (15) =====
    cust_data = [
        {"name": "张三", "phone": "138-1001-0001", "address": "XX村1组", "tag": "farmer"},
        {"name": "李四", "phone": "138-1002-0002", "address": "XX村2组", "tag": "farmer"},
        {"name": "王五合作社", "phone": "138-1003-0003", "address": "XX镇XX号", "tag": "cooperative"},
        {"name": "赵六种植基地", "phone": "138-1004-0004", "address": "XX乡XX村", "tag": "major_farmer"},
        {"name": "孙七", "phone": "138-1005-0005", "address": "XX村3组", "tag": "farmer"},
        {"name": "周八", "phone": "138-1006-0006", "address": "XX村4组", "tag": "farmer"},
        {"name": "吴九家庭农场", "phone": "138-1007-0007", "address": "XX乡YY村", "tag": "major_farmer"},
        {"name": "郑十", "phone": "138-1008-0008", "address": "XX村5组", "tag": "farmer"},
        {"name": "绿丰蔬菜合作社", "phone": "138-1009-0009", "address": "XX镇ZZ号", "tag": "cooperative"},
        {"name": "钱十一", "phone": "138-1010-0010", "address": "XX村6组", "tag": "farmer"},
        {"name": "刘十二果园", "phone": "138-1011-0011", "address": "XX乡AA村", "tag": "major_farmer"},
        {"name": "陈十三", "phone": "138-1012-0012", "address": "XX村7组", "tag": "farmer"},
        {"name": "杨十四养殖场", "phone": "138-1013-0013", "address": "XX乡BB村", "tag": "major_farmer"},
        {"name": "黄十五", "phone": "138-1014-0014", "address": "XX村8组", "tag": "farmer"},
        {"name": "农旺合作社", "phone": "138-1015-0015", "address": "XX镇CC号", "tag": "cooperative"},
    ]
    customers = []
    for c in cust_data:
        cust = Customer(**c)
        db.add(cust); db.flush(); customers.append(cust)

    # ===== 5. Products (30) =====
    pdata = [
        # 种子类 (5)
        {"code": "ZZ-001", "generic_name": "杂交水稻种", "trade_name": "Y两优1号", "barcode": "6901001",
         "spec": "1kg/袋", "base_unit": "袋", "retail_price": 45.0, "ref_cost": 35.0, "category_id": cats["水稻种子"].id},
        {"code": "ZZ-002", "generic_name": "小麦种", "trade_name": "济麦22", "barcode": "6901002",
         "spec": "25kg/袋", "base_unit": "袋", "retail_price": 120.0, "ref_cost": 95.0, "category_id": cats["小麦种子"].id},
        {"code": "ZZ-003", "generic_name": "玉米种子", "trade_name": "郑单958", "barcode": "6901003",
         "spec": "4500粒/袋", "base_unit": "袋", "retail_price": 65.0, "ref_cost": 50.0, "category_id": cats["玉米种子"].id},
        {"code": "ZZ-004", "generic_name": "白菜种子", "trade_name": "北京新三号", "barcode": "6901004",
         "spec": "25g/袋", "base_unit": "袋", "retail_price": 8.0, "ref_cost": 5.5, "category_id": cats["蔬菜种子"].id},
        {"code": "ZZ-005", "generic_name": "大豆种子", "trade_name": "中黄13", "barcode": "6901005",
         "spec": "5kg/袋", "base_unit": "袋", "retail_price": 55.0, "ref_cost": 42.0, "category_id": cats["豆类种子"].id},
        # 农药-杀虫剂 (4)
        {"code": "NY-001", "generic_name": "吡虫啉", "trade_name": "一遍净", "barcode": "6902001",
         "spec": "10g*500袋", "formulation": "可湿性粉剂", "content": "10%", "toxicity": "低毒",
         "manufacturer": "江苏扬农", "base_unit": "袋", "retail_price": 3.5, "ref_cost": 2.8, "category_id": cats["杀虫剂"].id},
        {"code": "NY-002", "generic_name": "阿维菌素", "trade_name": "爱福丁", "barcode": "6902002",
         "spec": "100ml*50瓶", "formulation": "乳油", "content": "1.8%", "toxicity": "低毒",
         "manufacturer": "深圳诺普信", "base_unit": "瓶", "retail_price": 12.0, "ref_cost": 9.0, "category_id": cats["杀虫剂"].id},
        {"code": "NY-003", "generic_name": "高效氯氟氰菊酯", "trade_name": "功夫", "barcode": "6902003",
         "spec": "200ml*40瓶", "formulation": "乳油", "content": "2.5%", "toxicity": "中等毒",
         "manufacturer": "先正达", "base_unit": "瓶", "retail_price": 8.0, "ref_cost": 6.0,
         "category_id": cats["杀虫剂"].id, "is_restricted": True, "restricted_max_quantity": 100},
        {"code": "NY-004", "generic_name": "噻虫嗪", "trade_name": "阿克泰", "barcode": "6902004",
         "spec": "10g*500袋", "formulation": "水分散粒剂", "content": "25%", "toxicity": "低毒",
         "manufacturer": "先正达", "base_unit": "袋", "retail_price": 5.0, "ref_cost": 3.8, "category_id": cats["杀虫剂"].id},
        # 农药-杀菌剂 (3)
        {"code": "NY-005", "generic_name": "多菌灵", "trade_name": "", "barcode": "6902005",
         "spec": "400g*20袋", "formulation": "可湿性粉剂", "content": "50%", "toxicity": "低毒",
         "manufacturer": "江苏蓝丰", "base_unit": "袋", "retail_price": 25.0, "ref_cost": 19.0, "category_id": cats["杀菌剂"].id},
        {"code": "NY-006", "generic_name": "百菌清", "trade_name": "达科宁", "barcode": "6902006",
         "spec": "100g*50袋", "formulation": "可湿性粉剂", "content": "75%", "toxicity": "低毒",
         "manufacturer": "先正达", "base_unit": "袋", "retail_price": 15.0, "ref_cost": 11.0, "category_id": cats["杀菌剂"].id},
        {"code": "NY-007", "generic_name": "戊唑醇", "trade_name": "好力克", "barcode": "6902007",
         "spec": "100ml*50瓶", "formulation": "悬浮剂", "content": "430g/L", "toxicity": "低毒",
         "manufacturer": "拜耳", "base_unit": "瓶", "retail_price": 22.0, "ref_cost": 17.0, "category_id": cats["杀菌剂"].id},
        # 农药-除草剂 (3)
        {"code": "NY-008", "generic_name": "草甘膦", "trade_name": "农达", "barcode": "6902008",
         "spec": "200ml*40瓶", "formulation": "水剂", "content": "41%", "toxicity": "低毒",
         "manufacturer": "拜耳", "base_unit": "瓶", "retail_price": 18.0, "ref_cost": 14.0, "category_id": cats["除草剂"].id},
        {"code": "NY-009", "generic_name": "草铵膦", "trade_name": "保试达", "barcode": "6902009",
         "spec": "200ml*40瓶", "formulation": "水剂", "content": "200g/L", "toxicity": "低毒",
         "manufacturer": "拜耳", "base_unit": "瓶", "retail_price": 20.0, "ref_cost": 15.5, "category_id": cats["除草剂"].id},
        {"code": "NY-010", "generic_name": "烟嘧磺隆", "trade_name": "玉农乐", "barcode": "6902010",
         "spec": "100ml*50瓶", "formulation": "悬浮剂", "content": "4%", "toxicity": "低毒",
         "manufacturer": "日本石原", "base_unit": "瓶", "retail_price": 28.0, "ref_cost": 22.0, "category_id": cats["除草剂"].id},
        # 化肥类 (6)
        {"code": "HF-001", "generic_name": "尿素", "trade_name": "", "barcode": "6903001",
         "spec": "50kg/袋", "content": "含氮46%", "base_unit": "袋", "retail_price": 150.0, "ref_cost": 130.0, "category_id": cats["氮肥"].id},
        {"code": "HF-002", "generic_name": "过磷酸钙", "trade_name": "", "barcode": "6903002",
         "spec": "50kg/袋", "content": "P2O5≥12%", "base_unit": "袋", "retail_price": 60.0, "ref_cost": 48.0, "category_id": cats["磷肥"].id},
        {"code": "HF-003", "generic_name": "氯化钾", "trade_name": "", "barcode": "6903003",
         "spec": "50kg/袋", "content": "K2O≥60%", "base_unit": "袋", "retail_price": 220.0, "ref_cost": 190.0, "category_id": cats["钾肥"].id},
        {"code": "HF-004", "generic_name": "复合肥", "trade_name": "史丹利", "barcode": "6903004",
         "spec": "50kg/袋", "content": "15-15-15", "base_unit": "袋", "retail_price": 180.0, "ref_cost": 150.0, "category_id": cats["复合肥"].id},
        {"code": "HF-005", "generic_name": "有机肥", "trade_name": "金正大", "barcode": "6903005",
         "spec": "40kg/袋", "content": "有机质≥45%", "base_unit": "袋", "retail_price": 85.0, "ref_cost": 65.0, "category_id": cats["有机肥"].id},
        {"code": "HF-006", "generic_name": "大量元素水溶肥", "trade_name": "芳润", "barcode": "6903006",
         "spec": "5kg/袋", "content": "20-20-20+TE", "base_unit": "袋", "retail_price": 55.0, "ref_cost": 40.0, "category_id": cats["水溶肥"].id},
        # 农膜类 (3)
        {"code": "NM-001", "generic_name": "地膜", "trade_name": "黑地膜", "barcode": "6904001",
         "spec": "0.8m*400m/卷", "base_unit": "卷", "retail_price": 65.0, "ref_cost": 50.0, "category_id": cats["地膜"].id},
        {"code": "NM-002", "generic_name": "大棚膜", "trade_name": "PO膜", "barcode": "6904002",
         "spec": "8m*50m/卷", "base_unit": "卷", "retail_price": 320.0, "ref_cost": 260.0, "category_id": cats["大棚膜"].id},
        {"code": "NM-003", "generic_name": "遮阳网", "trade_name": "", "barcode": "6904003",
         "spec": "4m*50m/卷", "base_unit": "卷", "retail_price": 90.0, "ref_cost": 70.0, "category_id": cats["遮阳网"].id},
        # 饲料类 (3)
        {"code": "SL-001", "generic_name": "猪浓缩料", "trade_name": "正大猪料", "barcode": "6905001",
         "spec": "40kg/袋", "base_unit": "袋", "retail_price": 280.0, "ref_cost": 240.0, "category_id": cats["猪饲料"].id},
        {"code": "SL-002", "generic_name": "蛋鸡配合料", "trade_name": "正大蛋鸡料", "barcode": "6905002",
         "spec": "40kg/袋", "base_unit": "袋", "retail_price": 165.0, "ref_cost": 140.0, "category_id": cats["鸡饲料"].id},
        {"code": "SL-003", "generic_name": "鱼膨化料", "trade_name": "通威鱼料", "barcode": "6905003",
         "spec": "25kg/袋", "base_unit": "袋", "retail_price": 195.0, "ref_cost": 170.0, "category_id": cats["鱼饲料"].id},
        # 农具类 (3)
        {"code": "NJ-001", "generic_name": "背负式喷雾器", "trade_name": "", "barcode": "6906001",
         "spec": "16L", "base_unit": "台", "retail_price": 85.0, "ref_cost": 65.0, "category_id": cats["喷雾器"].id},
        {"code": "NJ-002", "generic_name": "锄头", "trade_name": "", "barcode": "6906002",
         "spec": "标准", "base_unit": "把", "retail_price": 25.0, "ref_cost": 18.0, "category_id": cats["锄头"].id},
        {"code": "NJ-003", "generic_name": "PVC水管", "trade_name": "", "barcode": "6906003",
         "spec": "25mm*100m/卷", "base_unit": "卷", "retail_price": 120.0, "ref_cost": 95.0, "category_id": cats["水管"].id},
    ]
    products = []
    for p in pdata:
        prod = Product(**p)
        db.add(prod); db.flush(); products.append(prod)
        init_qty = random.randint(30, 200)
        inv = Inventory(product_id=prod.id, warehouse_id=wh.id, quantity=init_qty,
                        available_quantity=init_qty, cost_price=(prod.ref_cost or 10))
        db.add(inv)
    db.commit()

    # ===== 6. Purchase Orders (8) =====
    today = datetime.now(timezone.utc)
    po_config = [
        {"no": "JH-20260801-001", "supplier": 0, "days_ago": 10, "items": [(0,80,35.0), (3,100,5.5), (4,50,42.0)]},
        {"no": "JH-20260802-001", "supplier": 1, "days_ago": 9, "items": [(5,200,2.8), (6,120,9.0), (7,100,6.0), (8,80,3.8)]},
        {"no": "JH-20260803-001", "supplier": 1, "days_ago": 8, "items": [(9,80,19.0), (10,100,11.0), (11,60,17.0)]},
        {"no": "JH-20260804-001", "supplier": 1, "days_ago": 7, "items": [(12,150,14.0), (13,100,15.5), (14,60,22.0)]},
        {"no": "JH-20260805-001", "supplier": 2, "days_ago": 6, "items": [(15,30,130.0), (16,50,48.0), (17,20,190.0), (18,40,150.0)]},
        {"no": "JH-20260806-001", "supplier": 2, "days_ago": 5, "items": [(19,60,65.0), (20,40,40.0)]},
        {"no": "JH-20260807-001", "supplier": 3, "days_ago": 4, "items": [(21,30,50.0), (22,15,260.0), (23,40,70.0)]},
        {"no": "JH-20260808-001", "supplier": 4, "days_ago": 3, "items": [(24,25,240.0), (25,30,140.0), (26,20,170.0)]},
    ]
    for po_cfg in po_config:
        d = today - timedelta(days=po_cfg["days_ago"])
        total = sum(qty * price for _, qty, price in po_cfg["items"])
        po = PurchaseOrder(order_no=po_cfg["no"], supplier_id=suppliers[po_cfg["supplier"]].id,
                           total_amount=total, status="confirmed", order_date=d)
        db.add(po); db.flush()
        for pid, qty, price in po_cfg["items"]:
            db.add(PurchaseItem(order_id=po.id, product_id=products[pid].id,
                                quantity=qty, unit_price=price, amount=qty*price))

    # ===== 7. Sale Orders (50+) =====
    pay_methods = ["cash", "wechat", "alipay", "credit"]
    for i in range(55):
        days_ago = random.randint(0, 30)
        d = today - timedelta(days=days_ago)
        cust = random.choice(customers)
        is_credit = (random.random() < 0.2)  # 20% credit
        # 1-3 items per sale
        n_items = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        items = []
        total = 0.0
        used_prods = set()
        for _ in range(n_items):
            pid = random.randrange(len(products))
            while pid in used_prods:
                pid = random.randrange(len(products))
            used_prods.add(pid)
            qty = random.randint(1, 8)
            price = products[pid].retail_price or 10
            amt = round(qty * float(price), 2)
            items.append((pid, qty, float(price), amt))
            total += amt
        total = round(total, 2)

        so = SaleOrder(
            order_no=f"XS-202608{str(i+1).zfill(3)}",
            customer_id=cust.id,
            total_amount=total,
            payment_method="credit" if is_credit else random.choice(pay_methods[:3]),
            is_paid=not is_credit,
            order_date=d,
        )
        db.add(so); db.flush()
        for pid, qty, price, amt in items:
            db.add(SaleItem(order_id=so.id, product_id=products[pid].id,
                            quantity=qty, unit_price=price, amount=amt))
        # AR for credit sales
        if is_credit:
            db.add(ARTransaction(
                customer_id=cust.id, sale_order_id=so.id,
                type="debit", amount=total, balance_after=total,
                created_at=d, note=f"销售单 {so.order_no} 挂账"
            ))
    db.commit()

    # ===== 8. AP Transactions (8) =====
    for po_cfg in po_config:
        d = today - timedelta(days=po_cfg["days_ago"])
        total = sum(qty * price for _, qty, price in po_cfg["items"])
        db.add(APTransaction(
            supplier_id=suppliers[po_cfg["supplier"]].id,
            purchase_order_id=None, type="payable", amount=total,
            balance_after=total,
            created_at=d,
            note=f"进货 {po_cfg['no']} 应付"
        ))
    db.commit()

    # ===== 9. Recent AR repayments (only for customers with credit balance) =====
    # Calculate credit balances for each customer
    cust_balances = {}
    for txn in db.query(ARTransaction).filter(ARTransaction.type.in_(["debit", "credit"])).all():
        cust_id = txn.customer_id
        if cust_id not in cust_balances:
            cust_balances[cust_id] = 0.0
        cust_balances[cust_id] += txn.amount if txn.type == "debit" else -txn.amount

    for cust_id, bal in cust_balances.items():
        if bal <= 0:
            continue
        # Repay 30-80% of the outstanding balance
        repay_amt = round(bal * random.uniform(0.3, 0.8), 2)
        if repay_amt < 10:
            continue
        d = today - timedelta(days=random.randint(1, 5))
        db.add(ARTransaction(
            customer_id=cust_id, type="credit", amount=repay_amt,
            balance_after=0, created_at=d, note="还款"
        ))
    db.commit()

    print(f"[DemoData] 初始化完成: {len(products)}商品, {len(suppliers)}供应商, {len(customers)}客户, 8笔进货, 55笔销售")