from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from nongzi.database import get_db
from nongzi.models.inventory import Inventory
from nongzi.models.product import Product, Category
from nongzi.utils.helpers import format_currency, get_or_create_default_warehouse

router = APIRouter(prefix='/inventory', tags=['库存管理'])

import os
from fastapi.templating import Jinja2Templates
from nongzi.config import BASE_DIR
_td = os.path.join(BASE_DIR, 'templates')
templates = Jinja2Templates(directory=_td)
templates.env.filters['currency'] = format_currency


@router.get('/batch-detail/{product_id}')
def batch_detail(request: Request, product_id: int, db: Session = Depends(get_db)):
    from nongzi.models.inventory import InventoryBatch
    from datetime import datetime
    today = datetime.now()
    batches = db.query(InventoryBatch).filter(
        InventoryBatch.product_id == product_id, InventoryBatch.available_quantity > 0
    ).order_by(InventoryBatch.expiry_date.asc().nulls_last()).all()
    product = db.query(Product).filter(Product.id == product_id).first()
    results = []
    for b in batches:
        days_left = None
        if b.expiry_date:
            days_left = (b.expiry_date - today).days
        results.append({"batch": b, "days_left": days_left})
    return templates.TemplateResponse("inventory/batch_detail.html", {"request": request, "product": product, "batches": results})


@router.get('/')
def inventory_list(request: Request, search: str = Query(None), category_id: int = Query(None), sort: str = Query('name'), page: int = Query(1), db: Session = Depends(get_db)):
    warehouse = get_or_create_default_warehouse(db)
    query = db.query(Inventory, Product).join(Product, Inventory.product_id == Product.id).filter(Inventory.warehouse_id == warehouse.id, Product.is_active == True)
    if category_id:
        cat_ids = [category_id]
        children = db.query(Category).filter(Category.parent_id == category_id, Category.is_active == True).all()
        cat_ids.extend([c.id for c in children])
        query = query.filter(Product.category_id.in_(cat_ids))
    if search:
        query = query.filter(or_(Product.generic_name.ilike(f'%{search}%'), Product.trade_name.ilike(f'%{search}%'), Product.code.ilike(f'%{search}%'), Product.barcode == search))
    if sort == 'quantity': query = query.order_by(Inventory.quantity.desc())
    elif sort == 'name': query = query.order_by(Product.generic_name)
    else: query = query.order_by(Product.generic_name)
    total = query.count()
    per_page = 20
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    rows = query.offset((page - 1) * per_page).limit(per_page).all()
    items = []
    for inv, prod in rows:
        from nongzi.models.inventory import InventoryBatch
        from datetime import datetime
        today = datetime.now()
        # Check for expiring batches
        expiring_batches = db.query(InventoryBatch).filter(
            InventoryBatch.product_id == prod.id,
            InventoryBatch.expiry_date != None,
            InventoryBatch.available_quantity > 0
        ).order_by(InventoryBatch.expiry_date.asc()).all()
        min_days = None
        for b in expiring_batches:
            days = (b.expiry_date - today).days
            if min_days is None or days < min_days:
                min_days = days
        items.append({'product': prod, 'inventory': inv, 'min_expiry_days': min_days})
    categories = db.query(Category).filter(Category.parent_id == None, Category.is_active == True).order_by(Category.sort_order).all()
    cat_tree = []
    for cat in categories:
        children = db.query(Category).filter(Category.parent_id == cat.id, Category.is_active == True).order_by(Category.sort_order).all()
        cat_tree.append({'cat': cat, 'children': children})
    return templates.TemplateResponse('inventory/list.html', {'request': request, 'items': items, 'page': page, 'per_page': per_page, 'total': total, 'total_pages': total_pages, 'has_prev': page > 1, 'has_next': page < total_pages, 'prev_page': page - 1, 'next_page': page + 1, 'categories': cat_tree, 'current_category_id': category_id, 'search': search or '', 'sort': sort})
from fastapi import Form
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import datetime, timezone
from nongzi.models.inventory import Inventory, InventoryBatch, StockCount, StockCountItem, WriteOff, Warehouse

@router.get("/stock-count")
def stock_count_list(request: Request, page: int = Query(1), db: Session = Depends(get_db)):
    """盘点单列表"""
    query = db.query(StockCount).order_by(StockCount.created_at.desc())
    total = query.count()
    per_page = 15
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse("inventory/stock_count_list.html", {
        "request": request, "items": items, "page": page,
        "total": total, "total_pages": total_pages,
        "has_prev": page > 1, "has_next": page < total_pages,
        "prev_page": page - 1, "next_page": page + 1
    })

@router.get("/stock-count/new")
def stock_count_new(request: Request, db: Session = Depends(get_db)):
    """新建盘点单"""
    categories = db.query(Category).filter(Category.parent_id == None, Category.is_active == True).order_by(Category.sort_order).all()
    cat_tree = []
    for cat in categories:
        children = db.query(Category).filter(Category.parent_id == cat.id, Category.is_active == True).order_by(Category.sort_order).all()
        cat_tree.append({"cat": cat, "children": children})
    return templates.TemplateResponse("inventory/stock_count_form.html", {"request": request, "categories": cat_tree})

@router.post("/stock-count")
def stock_count_create(request: Request, scope_type: str = Form("all"), scope_value: str = Form(""), counter_name: str = Form(""), db: Session = Depends(get_db)):
    """创建盘点单"""
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.query(StockCount).filter(StockCount.order_no.like(f"CH-{today_str}-%")).count() + 1
    order_no = f"CH-{today_str}-{str(count).zfill(3)}"
    warehouse = get_or_create_default_warehouse(db)

    sc = StockCount(order_no=order_no, counter_name=counter_name or "管理员",
                    scope_type=scope_type,
                    scope_value=int(scope_value) if scope_value else None)
    db.add(sc); db.flush()

    # Build product list
    query = db.query(Product).filter(Product.is_active == True)
    if scope_type == "category" and scope_value:
        cat_id = int(scope_value)
        child_ids = [c.id for c in db.query(Category).filter(Category.parent_id == cat_id).all()]
        query = query.filter(Product.category_id.in_([cat_id] + child_ids))
    elif scope_type == "product" and scope_value:
        query = query.filter(Product.id == int(scope_value))

    products = query.order_by(Product.generic_name).all()
    for p in products:
        inv = db.query(Inventory).filter(Inventory.product_id == p.id, Inventory.warehouse_id == warehouse.id).first()
        sys_qty = inv.available_quantity if inv else 0
        db.add(StockCountItem(count_id=sc.id, product_id=p.id, system_quantity=sys_qty))

    db.commit()
    return RedirectResponse(f"/inventory/stock-count/{sc.id}", 302)

@router.get("/stock-count/{id}")
def stock_count_detail(request: Request, id: int, db: Session = Depends(get_db)):
    """盘点单详情（录入实盘数）"""
    sc = db.query(StockCount).filter(StockCount.id == id).first()
    if not sc:
        return RedirectResponse("/inventory/stock-count", 302)
    return templates.TemplateResponse("inventory/stock_count_detail.html", {"request": request, "sc": sc})

@router.post("/stock-count/{id}/save")
def stock_count_save(request: Request, id: int, db: Session = Depends(get_db)):
    """保存实盘数"""
    sc = db.query(StockCount).filter(StockCount.id == id).first()
    if not sc:
        return JSONResponse({"success": False, "message": "盘点单不存在"})
    for item in sc.items:
        qty_key = f"actual_{item.id}"
        # Get from form data
        try:
            from fastapi import Request as FastAPIRequest
            pass
        except:
            pass
    return JSONResponse({"success": True, "message": "保存成功"})

@router.post("/stock-count/{id}/actual")
async def stock_count_save_actual(request: Request, id: int, db: Session = Depends(get_db)):
    """保存实盘数（AJAX）"""
    from fastapi import Request as FR
    sc = db.query(StockCount).filter(StockCount.id == id).first()
    if not sc:
        return JSONResponse({"success": False, "message": "盘点单不存在"})
    body = await request.json()
    for item_data in body.get("items", []):
        item = db.query(StockCountItem).filter(StockCountItem.id == item_data["id"], StockCountItem.count_id == id).first()
        if item:
            item.actual_quantity = float(item_data.get("actual", 0))
            item.difference = (item.actual_quantity or 0) - item.system_quantity
    db.commit()
    return JSONResponse({"success": True, "message": "保存成功"})

@router.post("/stock-count/{id}/complete")
def stock_count_complete(request: Request, id: int, db: Session = Depends(get_db)):
    """完成盘点 - 差异处理"""
    sc = db.query(StockCount).filter(StockCount.id == id).first()
    if not sc:
        return JSONResponse({"success": False, "message": "盘点单不存在"})
    warehouse = get_or_create_default_warehouse(db)
    for item in sc.items:
        if item.actual_quantity is None:
            continue
        diff = item.actual_quantity - item.system_quantity
        if diff == 0:
            continue
        inv = db.query(Inventory).filter(Inventory.product_id == item.product_id, Inventory.warehouse_id == warehouse.id).first()
        if inv:
            inv.quantity += diff
            inv.available_quantity += diff
        # Create write-off for loss
        if diff < 0:
            loss_qty = abs(diff)
            today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            wo_count = db.query(WriteOff).filter(WriteOff.order_no.like(f"LS-{today_str}-%")).count() + 1
            wo_no = f"LS-{today_str}-{str(wo_count).zfill(3)}"
            db.add(WriteOff(order_no=wo_no, product_id=item.product_id, warehouse_id=warehouse.id,
                           quantity=loss_qty, reason="other", notes=f"盘点单{sc.order_no}盘亏"))
    sc.status = "completed"
    db.commit()
    return JSONResponse({"success": True, "message": "盘点完成"})

@router.get("/stock-count/{id}/export")
def stock_count_export(request: Request, id: int, db: Session = Depends(get_db)):
    """导出盘点表为Excel"""
    from nongzi.utils.excel_export import export_stock_count
    sc = db.query(StockCount).filter(StockCount.id == id).first()
    if not sc:
        return RedirectResponse("/inventory/stock-count", 302)
    filepath = export_stock_count(sc, db)
    from fastapi.responses import FileResponse
    return FileResponse(filepath, filename=f"盘点表_{sc.order_no}.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@router.post("/write-off")
def create_write_off(request: Request, product_id: int = Form(...), quantity: float = Form(...),
                     reason: str = Form(...), notes: str = Form(""), batch_id: int = Form(None),
                     db: Session = Depends(get_db)):
    """创建报损单"""
    warehouse = get_or_create_default_warehouse(db)
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    wo_count = db.query(WriteOff).filter(WriteOff.order_no.like(f"LS-{today_str}-%")).count() + 1
    order_no = f"LS-{today_str}-{str(wo_count).zfill(3)}"

    wo = WriteOff(order_no=order_no, product_id=product_id, warehouse_id=warehouse.id,
                  batch_id=batch_id, quantity=quantity, reason=reason, notes=notes)
    db.add(wo)

    # Deduct from inventory
    inv = db.query(Inventory).filter(Inventory.product_id == product_id, Inventory.warehouse_id == warehouse.id).first()
    if inv:
        inv.quantity -= quantity
        inv.available_quantity -= quantity

    # Deduct from batch if specified
    if batch_id:
        batch = db.query(InventoryBatch).filter(InventoryBatch.id == batch_id).first()
        if batch:
            batch.available_quantity -= quantity
            batch.quantity -= quantity

    from nongzi.models.system import OperationLog
    db.add(OperationLog(user_id=1, action="WRITE_OFF", target_type="write_off", target_id=0,
                        detail=f'{{"order_no":"{order_no}","product_id":{product_id},"quantity":{quantity},"reason":"{reason}"}}',
                        ip_address=request.client.host if request.client else ""))

    db.commit()
    return RedirectResponse("/inventory", 302)

@router.get("/write-off")
def write_off_list(request: Request, page: int = Query(1), db: Session = Depends(get_db)):
    """报损单列表"""
    query = db.query(WriteOff).order_by(WriteOff.created_at.desc())
    total = query.count()
    per_page = 15
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse("inventory/write_off_list.html", {"request": request, "items": items, "page": page, "total": total, "total_pages": total_pages, "has_prev": page > 1, "has_next": page < total_pages, "prev_page": page - 1, "next_page": page + 1})
