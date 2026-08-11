
from fastapi import APIRouter, Request, Query, Depends
from sqlalchemy.orm import Session
from nongzi.database import get_db
from nongzi.utils.helpers import format_currency

router = APIRouter(prefix="/trace", tags=["追溯"])

import os as _os
from fastapi.templating import Jinja2Templates
from nongzi.config import BASE_DIR
_td = _os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=_td)
templates.env.filters["currency"] = format_currency


@router.get("/")
def trace_index(request: Request):
    return templates.TemplateResponse("trace/index.html", {"request": request})


@router.get("/batch")
def trace_by_batch(request: Request, batch_no: str = Query(...), db: Session = Depends(get_db)):
    from nongzi.models.inventory import InventoryBatch
    from nongzi.models.sale import SaleItem, SaleOrder
    batch = db.query(InventoryBatch).filter(InventoryBatch.batch_no == batch_no).first()
    if not batch:
        return templates.TemplateResponse("trace/result.html", {"request": request, "error": f"未找到批号: {batch_no}"})
    
    # Forward trace: source
    source = {}
    if batch.purchase_item:
        pi = batch.purchase_item
        source = {"supplier": pi.order.supplier.name, "order_no": pi.order.order_no,
                   "order_date": pi.order.order_date.strftime("%Y-%m-%d") if pi.order.order_date else "",
                   "quantity": pi.quantity, "unit_price": pi.unit_price}
    
    # Current stock
    current = {"total": batch.quantity, "available": batch.available_quantity}
    
    # Where did it go (sales)
    sales = []
    sale_items = db.query(SaleItem).filter(SaleItem.batch_id == batch.id).join(SaleOrder).order_by(SaleOrder.order_date.desc()).all()
    for si in sale_items:
        sales.append({
            "order_no": si.order.order_no,
            "buyer": si.order.customer.name if si.order.customer else "零售",
            "quantity": si.quantity,
            "date": si.order.order_date.strftime("%Y-%m-%d") if si.order.order_date else "",
        })
    
    return templates.TemplateResponse("trace/result.html", {
        "request": request,
        "batch_no": batch_no,
        "product": batch.product,
        "source": source,
        "current": current,
        "sales": sales,
        "total_sold": sum(s["quantity"] for s in sales),
    })


@router.get("/sale")
def trace_by_sale(request: Request, order_no: str = Query(...), db: Session = Depends(get_db)):
    from nongzi.models.sale import SaleOrder, SaleItem
    from nongzi.models.inventory import InventoryBatch
    order = db.query(SaleOrder).filter(SaleOrder.order_no == order_no).first()
    if not order:
        return templates.TemplateResponse("trace/result.html", {"request": request, "error": f"未找到销售单: {order_no}"})
    
    items_data = []
    for item in order.items:
        batch_info = None
        if item.batch_id:
            batch = db.query(InventoryBatch).filter(InventoryBatch.id == item.batch_id).first()
            if batch and batch.purchase_item:
                batch_info = {
                    "batch_no": batch.batch_no,
                    "supplier": batch.purchase_item.order.supplier.name,
                    "purchase_order_no": batch.purchase_item.order.order_no,
                    "purchase_date": batch.purchase_item.order.order_date.strftime("%Y-%m-%d") if batch.purchase_item.order.order_date else "",
                }
        items_data.append({
            "product": item.product,
            "quantity": item.quantity,
            "batch": batch_info,
        })
    
    return templates.TemplateResponse("trace/result.html", {
        "request": request, "order": order, "items": items_data, "mode": "sale",
    })
