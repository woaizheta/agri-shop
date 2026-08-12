from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from nongzi.database import get_db
from nongzi.models.purchase import PurchaseOrder, PurchaseItem
from nongzi.models.product import Product
from nongzi.models.contact import Supplier
from nongzi.models.inventory import Inventory
from nongzi.utils.helpers import format_currency, paginate, generate_order_no, get_or_create_default_warehouse

router = APIRouter(prefix='/purchases', tags=['进货管理'])

import os
from fastapi.templating import Jinja2Templates
from nongzi.config import BASE_DIR
_td = os.path.join(BASE_DIR, 'templates')
templates = Jinja2Templates(directory=_td)
templates.env.filters['currency'] = format_currency


@router.get('/')
def purchase_list(request: Request, search: str = Query(None), supplier_id: int = Query(None), page: int = Query(1), db: Session = Depends(get_db)):
    query = db.query(PurchaseOrder).filter(PurchaseOrder.is_active == True)
    if search: query = query.filter(PurchaseOrder.order_no.ilike(f'%{search}%'))
    if supplier_id: query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    query = query.order_by(PurchaseOrder.order_date.desc())
    result = paginate(query, page, 20)
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.name).all()
    from nongzi.models.finance import APTransaction
    from sqlalchemy import func
    paid_map = {}
    for item in result.get('items', []):
        paid = db.query(func.coalesce(func.sum(APTransaction.amount), 0)).filter(APTransaction.purchase_order_id == item.id, APTransaction.type == 'payment').scalar() or 0
        paid_map[item.id] = round(paid, 2)
    return templates.TemplateResponse('purchases/list.html', {'request': request, **result, 'search': search or '', 'current_supplier_id': supplier_id, 'suppliers': suppliers, 'paid_map': paid_map})


@router.get('/new')
def new_purchase_form(request: Request, db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.name).all()
    return templates.TemplateResponse('purchases/form.html', {'request': request, 'order': None, 'suppliers': suppliers, 'today': datetime.now(timezone.utc).strftime('%Y-%m-%d')})


@router.post('/')
def create_purchase(request: Request, supplier_id: int = Form(...), order_date: str = Form(...), note: str = Form(''), product_id: list = Form(...), quantity: list = Form(...), unit_price: list = Form(...), batch_no: list = Form(...), prod_date: list = Form(default=[]), expiry_date: list = Form(default=[]), db: Session = Depends(get_db)):
    from datetime import datetime as dt
    order_no = generate_order_no('PO', db)
    total_amount = 0.0
    items_data = []
    from datetime import datetime as dt
    # Validate batch uniqueness per product
    batch_seen = {}
    for i in range(len(product_id)):
        pid_str = str(product_id[i]).strip()
        if not pid_str: continue
        pid = int(pid_str)
        bn = str(batch_no[i]).strip() if i < len(batch_no) else ''
        if not bn:
            return RedirectResponse('/purchases/new?error=批号不能为空', 302)
        if pid in batch_seen and bn in batch_seen[pid]:
            return RedirectResponse('/purchases/new?error=同一商品下批号不可重复', 302)
        batch_seen.setdefault(pid, set()).add(bn)
        # Check existing batch in inventory_batch
        from nongzi.models.inventory import InventoryBatch
        existing = db.query(InventoryBatch).filter(
            InventoryBatch.product_id == pid, InventoryBatch.batch_no == bn
        ).first()
        if existing:
            return RedirectResponse(f'/purchases/new?error=批号{bn}已存在', 302)
        qty = float(quantity[i]) if (i < len(quantity) and quantity[i]) else 0
        uprice = float(unit_price[i]) if (i < len(unit_price) and unit_price[i]) else 0
        amt = round(qty * uprice, 2); total_amount += amt
        pd = str(prod_date[i]).strip() if i < len(prod_date) else ''
        ed = str(expiry_date[i]).strip() if i < len(expiry_date) else ''
        items_data.append({'product_id': pid, 'quantity': qty, 'unit_price': uprice, 'amount': amt, 'batch_no': bn, 'prod_date': pd, 'expiry_date': ed})
    if not items_data:
        return RedirectResponse('/purchases/new', 302)
    order = PurchaseOrder(order_no=order_no, supplier_id=supplier_id, total_amount=round(total_amount, 2), order_date=dt.strptime(order_date, '%Y-%m-%d') if order_date else datetime.now(timezone.utc), note=note, status='confirmed')
    db.add(order); db.flush()
    warehouse = get_or_create_default_warehouse(db)
    for item_data in items_data:
        pd_val = dt.strptime(item_data['prod_date'], '%Y-%m-%d') if item_data['prod_date'] else None
        ed_val = dt.strptime(item_data['expiry_date'], '%Y-%m-%d') if item_data['expiry_date'] else None
        item = PurchaseItem(order_id=order.id, product_id=item_data['product_id'], batch_no=item_data['batch_no'], quantity=item_data['quantity'], unit_price=item_data['unit_price'], amount=item_data['amount'], prod_date=pd_val, expiry_date=ed_val)
        db.add(item)
        db.flush()
        # Write inventory_batch
        from nongzi.models.inventory import InventoryBatch
        ib = InventoryBatch(product_id=item_data['product_id'], warehouse_id=warehouse.id, batch_no=item_data['batch_no'], quantity=item_data['quantity'], available_quantity=item_data['quantity'], prod_date=pd_val, expiry_date=ed_val, purchase_item_id=item.id)
        db.add(ib)
        inv = db.query(Inventory).filter(Inventory.product_id == item_data['product_id'], Inventory.warehouse_id == warehouse.id).first()
        if inv:
            total_cost_before = inv.quantity * (inv.cost_price or 0)
            new_cost = item_data['quantity'] * item_data['unit_price']
            inv.quantity += item_data['quantity']
            inv.available_quantity += item_data['quantity']
            if inv.quantity > 0: inv.cost_price = round((total_cost_before + new_cost) / inv.quantity, 2)
        else:
            inv = Inventory(product_id=item_data['product_id'], warehouse_id=warehouse.id, quantity=item_data['quantity'], available_quantity=item_data['quantity'], cost_price=round(item_data['unit_price'], 2))
            db.add(inv)
    # Operation log
    from nongzi.models.system import OperationLog
    db.add(OperationLog(user_id=1, action='CREATE_PURCHASE', target_type='purchase_order', target_id=order.id, detail=f'{{"order_no":"{order_no}","total":{round(total_amount,2)}}}', ip_address=request.client.host if request.client else ''))
    db.commit()
    return RedirectResponse('/purchases', 302)


@router.get('/{id}')
def purchase_detail(request: Request, id: int, db: Session = Depends(get_db)):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == id).first()
    if not order: return RedirectResponse('/purchases', 302)
    return templates.TemplateResponse('purchases/detail.html', {'request': request, 'order': order})
