from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from nongzi.database import get_db
from nongzi.models.sale import SaleOrder, SaleItem, RestrictedSale
from nongzi.models.product import Product
from nongzi.models.contact import Customer
from nongzi.models.inventory import Inventory
from nongzi.models.finance import ARTransaction
from nongzi.utils.helpers import format_currency, paginate, generate_order_no, get_or_create_default_warehouse

router = APIRouter(prefix='/sales', tags=['销售管理'])

import os, json
from fastapi.templating import Jinja2Templates
from nongzi.config import BASE_DIR
_td = os.path.join(BASE_DIR, 'templates')
templates = Jinja2Templates(directory=_td)
templates.env.filters['currency'] = format_currency


@router.get('/')
def sale_list(request: Request, search: str = Query(None), page: int = Query(1), db: Session = Depends(get_db)):
    query = db.query(SaleOrder).order_by(SaleOrder.order_date.desc(), SaleOrder.id.desc())
    if search: query = query.filter(SaleOrder.order_no.ilike(f'%{search}%'))
    result = paginate(query, page, 20)
    return templates.TemplateResponse('sales/list.html', {'request': request, **result, 'search': search or ''})


@router.get('/pos')
def pos_page(request: Request, db: Session = Depends(get_db)):
    customers = db.query(Customer).filter(Customer.is_active == True).order_by(Customer.name).all()
    return templates.TemplateResponse('sales/pos.html', {'request': request, 'customers': customers})


@router.post('/pos')
def create_sale(request: Request, items_json: str = Form(...), payment_method: str = Form('cash'), customer_id: int = Form(None), db: Session = Depends(get_db)):
    items = json.loads(items_json)
    if not items: return RedirectResponse('/sales/pos', 302)
    order_no = generate_order_no('SO', db)
    is_credit = payment_method == 'credit'
    total_amount = sum(float(it.get('quantity', 0)) * float(it.get('unitPrice', 0)) for it in items)
    order = SaleOrder(order_no=order_no, customer_id=customer_id if is_credit else None, total_amount=round(total_amount, 2), payment_method=payment_method, is_paid=not is_credit)
    db.add(order); db.flush()
    warehouse = get_or_create_default_warehouse(db)
    for item in items:
        pid = item['productId']; qty = float(item.get('quantity', 0)); uprice = float(item.get('unitPrice', 0))
        amt = round(qty * uprice, 2)
        # Get inventory cost for profit tracking
        inv = db.query(Inventory).filter(Inventory.product_id == pid, Inventory.warehouse_id == warehouse.id).first()
        cost = inv.cost_price if inv else None
        # Deduct from inventory_batch (FIFO: oldest first)
        from nongzi.models.inventory import InventoryBatch
        batches = db.query(InventoryBatch).filter(
            InventoryBatch.product_id == pid, InventoryBatch.warehouse_id == warehouse.id,
            InventoryBatch.available_quantity > 0
        ).order_by(
            InventoryBatch.expiry_date.asc().nulls_last(), InventoryBatch.id.asc()
        ).all()
        remaining = qty
        batch_id = None
        for b in batches:
            if remaining <= 0: break
            deduct = min(remaining, b.available_quantity)
            b.available_quantity -= deduct
            b.quantity -= deduct
            remaining -= deduct
            if batch_id is None: batch_id = b.id
        if inv:
            inv.quantity -= qty
            inv.available_quantity -= qty
        db.add(SaleItem(order_id=order.id, product_id=pid, batch_id=batch_id, quantity=qty, unit_price=uprice, amount=amt, cost_price_at_sale=cost))
        product = db.query(Product).filter(Product.id == pid).first()
        if product and product.is_restricted:
            rs_data = item.get('restricted', {})
            if rs_data:
                db.add(RestrictedSale(sale_order_id=order.id, product_id=pid, buyer_name=rs_data.get('name',''), buyer_id_card=rs_data.get('idCard',''), buyer_phone=rs_data.get('phone',''), usage_purpose=rs_data.get('purpose',''), usage_crop=rs_data.get('crop',''), quantity=qty))
    if is_credit and customer_id:
        db.add(ARTransaction(customer_id=customer_id, sale_order_id=order.id, type='debit', amount=round(total_amount, 2), balance_after=round(total_amount, 2), note=f'销售挂账 {order_no}'))
    from nongzi.models.system import OperationLog
    db.add(OperationLog(user_id=1, action='CREATE_SALE', target_type='sale_order', target_id=order.id, detail=f'{{"order_no":"{order_no}","total":{round(total_amount,2)},"payment":"{payment_method}"}}', ip_address=request.client.host if request.client else ''))
    db.commit()
    return JSONResponse({'success': True, 'order_no': order_no})


@router.get('/{id}')
def sale_detail(request: Request, id: int, db: Session = Depends(get_db)):
    order = db.query(SaleOrder).filter(SaleOrder.id == id).first()
    if not order: return RedirectResponse('/sales', 302)
    return templates.TemplateResponse('sales/detail.html', {'request': request, 'order': order})


@router.get('/customers/search')
def search_customers(q: str = Query(''), db: Session = Depends(get_db)):
    from sqlalchemy import or_
    if not q: return JSONResponse([])
    customers = db.query(Customer).filter(Customer.is_active == True, or_(Customer.name.ilike(f'%{q}%'), Customer.phone.ilike(f'%{q}%'))).limit(10).all()
    return JSONResponse([{'id': c.id, 'name': c.name, 'phone': c.phone, 'balance': round(c.credit_balance, 2)} for c in customers])

@router.get("/{id}/receipt")
def print_receipt(request: Request, id: int, db: Session = Depends(get_db)):
    """打印销售小票"""
    from nongzi.config import STORE_NAME, STORE_ADDRESS, STORE_PHONE, VERSION
    order = db.query(SaleOrder).filter(SaleOrder.id == id).first()
    if not order:
        return RedirectResponse("/sales", 302)
    receipt_width = request.query_params.get("width", "80mm")
    templates_receipt = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates", "sales"))
    return templates_receipt.TemplateResponse("receipt.html", {
        "request": request,
        "order": order,
        "store_name": STORE_NAME,
        "store_address": STORE_ADDRESS,
        "store_phone": STORE_PHONE,
        "receipt_width": receipt_width,
        "version": f"v{VERSION}"
    })
