from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from nongzi.database import get_db
from nongzi.utils.helpers import format_currency

router = APIRouter(prefix="/reports", tags=["报表"])

import os as _os
from fastapi.templating import Jinja2Templates
from nongzi.config import BASE_DIR
_td = _os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=_td)
templates.env.filters["currency"] = format_currency


@router.get("/")
def reports_index(request: Request):
    from nongzi.models.sale import SaleOrder
    from sqlalchemy import func
    return templates.TemplateResponse("reports/index.html", {"request": request})


@router.get("/purchase-ledger")
def purchase_ledger(request: Request, date_from: str = Query(None), date_to: str = Query(None),
                    supplier_id: int = Query(None), batch_no: str = Query(None),
                    page: int = Query(1), export: str = Query(None),
                    db: Session = Depends(get_db)):
    from nongzi.models.purchase import PurchaseOrder, PurchaseItem
    from nongzi.models.product import Product
    from nongzi.models.contact import Supplier
    from datetime import datetime as dt
    query = db.query(PurchaseItem).join(PurchaseItem.order).join(PurchaseItem.product).join(
        Supplier, PurchaseOrder.supplier_id == Supplier.id)
    if date_from:
        try:
            d = dt.strptime(date_from, "%Y-%m-%d")
            query = query.filter(PurchaseOrder.order_date >= d)
        except: pass
    if date_to:
        try:
            d = dt.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(PurchaseOrder.order_date <= d)
        except: pass
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    if batch_no:
        query = query.filter(PurchaseItem.batch_no.ilike(f"%{batch_no}%"))
    query = query.order_by(PurchaseOrder.order_date.desc())

    if export == "1":
        from nongzi.utils.excel_export import export_to_excel
        from fastapi.responses import FileResponse
        rows_q = query.all()
        headers = ["日期", "供应商", "商品", "批号", "数量", "单价", "金额"]
        data = []
        for item in rows_q:
            data.append([
                item.order.order_date.strftime("%Y-%m-%d") if item.order.order_date else "",
                item.order.supplier.name,
                item.product.generic_name + (" " + item.product.trade_name if item.product.trade_name else ""),
                item.batch_no or "", item.quantity, item.unit_price, item.amount,
            ])
        fn = f"purchase_ledger_{date_from or 'all'}_{date_to or 'all'}.xlsx"
        path = export_to_excel(headers, data, fn)
        return FileResponse(path, filename=fn,
                          media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    total = query.count()
    per_page = 50
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    rows = []
    for item in items:
        rows.append({
            "order_date": item.order.order_date.strftime("%Y-%m-%d") if item.order.order_date else "",
            "supplier_name": item.order.supplier.name,
            "product_name": item.product.generic_name + (
                " " + item.product.trade_name if item.product.trade_name else ""),
            "batch_no": item.batch_no or "", "quantity": item.quantity,
            "unit_price": item.unit_price, "amount": item.amount,
        })
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.name).all()
    return templates.TemplateResponse("reports/purchase_ledger.html", {
        "request": request, "rows": rows, "page": page, "per_page": per_page,
        "total": total, "total_pages": total_pages, "has_prev": page > 1, "has_next": page < total_pages,
        "prev_page": page - 1, "next_page": page + 1,
        "date_from": date_from or "", "date_to": date_to or "",
        "current_supplier_id": supplier_id, "batch_no": batch_no or "",
        "suppliers": suppliers,
    })


@router.get("/sales-ledger")
def sales_ledger(request: Request, date_from: str = Query(None), date_to: str = Query(None),
                 product_id: int = Query(None), buyer: str = Query(None),
                 page: int = Query(1), export: str = Query(None),
                 db: Session = Depends(get_db)):
    from nongzi.models.sale import SaleOrder, SaleItem, RestrictedSale
    from nongzi.models.product import Product
    from nongzi.models.contact import Customer
    from nongzi.models.inventory import InventoryBatch
    from datetime import datetime as dt
    query = db.query(SaleItem).join(SaleItem.order).join(SaleItem.product).outerjoin(
        Customer, SaleOrder.customer_id == Customer.id)
    if date_from:
        try:
            d = dt.strptime(date_from, "%Y-%m-%d")
            query = query.filter(SaleOrder.order_date >= d)
        except: pass
    if date_to:
        try:
            d = dt.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(SaleOrder.order_date <= d)
        except: pass
    if product_id:
        query = query.filter(SaleItem.product_id == product_id)
    if buyer:
        query = query.filter(Customer.name.ilike(f"%{buyer}%"))
    query = query.order_by(SaleOrder.order_date.desc())

    if export == "1":
        from nongzi.utils.excel_export import export_to_excel
        from fastapi.responses import FileResponse
        rows_q = query.all()
        headers = ["日期", "购买人", "商品", "批号", "数量", "单价", "金额", "用途"]
        data = []
        for item in rows_q:
            bn = ""
            if item.batch_id:
                batch = db.query(InventoryBatch).filter(InventoryBatch.id == item.batch_id).first()
                bn = batch.batch_no if batch else ""
            purpose = ""
            rs = db.query(RestrictedSale).filter(
                RestrictedSale.sale_order_id == item.order_id,
                RestrictedSale.product_id == item.product_id).first()
            if rs: purpose = rs.usage_purpose or ""
            data.append([
                item.order.order_date.strftime("%Y-%m-%d") if item.order.order_date else "",
                item.order.customer.name if item.order.customer else "零售",
                item.product.generic_name + (" " + item.product.trade_name if item.product.trade_name else ""),
                bn, item.quantity, item.unit_price, item.amount, purpose,
            ])
        fn = f"sales_ledger_{date_from or 'all'}_{date_to or 'all'}.xlsx"
        path = export_to_excel(headers, data, fn)
        return FileResponse(path, filename=fn,
                          media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    total = query.count()
    per_page = 50
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    rows = []
    for item in items:
        bn = ""
        if item.batch_id:
            batch = db.query(InventoryBatch).filter(InventoryBatch.id == item.batch_id).first()
            bn = batch.batch_no if batch else ""
        purpose = ""
        rs = db.query(RestrictedSale).filter(
            RestrictedSale.sale_order_id == item.order_id,
            RestrictedSale.product_id == item.product_id).first()
        if rs: purpose = rs.usage_purpose or ""
        rows.append({
            "order_date": item.order.order_date.strftime("%Y-%m-%d") if item.order.order_date else "",
            "buyer": item.order.customer.name if item.order.customer else "零售",
            "product_name": item.product.generic_name + (
                " " + item.product.trade_name if item.product.trade_name else ""),
            "batch_no": bn, "quantity": item.quantity, "unit_price": item.unit_price,
            "amount": item.amount, "purpose": purpose,
        })
    return templates.TemplateResponse("reports/sales_ledger.html", {
        "request": request, "rows": rows, "page": page, "per_page": per_page,
        "total": total, "total_pages": total_pages, "has_prev": page > 1, "has_next": page < total_pages,
        "prev_page": page - 1, "next_page": page + 1,
        "date_from": date_from or "", "date_to": date_to or "",
        "product_id": product_id, "buyer": buyer or "",
    })


@router.get("/sales-report")
def sales_report(request: Request, period: str = Query("daily"), selected_date: str = Query(None),
                 page: int = Query(1), db: Session = Depends(get_db)):
    from nongzi.models.sale import SaleOrder, SaleItem
    from nongzi.models.product import Product
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func
    import json
    today = datetime.now(timezone.utc)
    if not selected_date:
        selected_date = today.strftime("%Y-%m-%d")
    try:
        sd = datetime.strptime(selected_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except:
        sd = today
    sd_start = sd.replace(hour=0, minute=0, second=0, microsecond=0)
    sd_end = sd.replace(hour=23, minute=59, second=59, microsecond=999999)

    rows = []
    total = 0
    chart_json = "{}"
    prod_rank = []

    if period == "daily":
        orders = db.query(SaleOrder).filter(
            SaleOrder.order_date >= sd_start, SaleOrder.order_date <= sd_end,
            SaleOrder.is_reversed == False).order_by(SaleOrder.order_date.desc()).all()
        total = sum(o.total_amount for o in orders)
        for o in orders:
            rows.append({"label": o.order_date.strftime("%H:%M"), "order_no": o.order_no,
                         "customer": o.customer.name if o.customer else "零售",
                         "amount": o.total_amount, "payment": o.payment_method})
    elif period == "monthly":
        try:
            y, m = int(selected_date[:4]), int(selected_date[5:7])
        except:
            y, m = today.year, today.month
        ms = datetime(y, m, 1, tzinfo=timezone.utc)
        if m == 12:
            me = datetime(y + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        else:
            me = datetime(y, m + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        results = db.query(func.date(SaleOrder.order_date), func.sum(SaleOrder.total_amount),
                           func.count(SaleOrder.id)).filter(
            SaleOrder.order_date >= ms, SaleOrder.order_date <= me,
            SaleOrder.is_reversed == False).group_by(func.date(SaleOrder.order_date)).order_by(
            func.date(SaleOrder.order_date)).all()
        chart_labels = []
        chart_data = []
        for d, amt, cnt in results:
            chart_labels.append(str(d))
            chart_data.append(round(amt, 2))
            total += amt
        chart_json = json.dumps({"labels": chart_labels, "data": chart_data})
        top_products = db.query(Product.generic_name, func.sum(SaleItem.quantity),
                                func.sum(SaleItem.amount)).join(SaleItem).join(SaleOrder).filter(
            SaleOrder.order_date >= ms, SaleOrder.order_date <= me,
            SaleOrder.is_reversed == False).group_by(Product.id).order_by(
            func.sum(SaleItem.amount).desc()).limit(20).all()
        prod_rank = [{"name": p[0], "qty": round(p[1], 2), "amount": round(p[2], 2)} for p in top_products]
    elif period == "yearly":
        try:
            y = int(selected_date[:4])
        except:
            y = today.year
        results = db.query(func.strftime("%Y-%m", SaleOrder.order_date),
                           func.sum(SaleOrder.total_amount)).filter(
            SaleOrder.order_date >= f"{y}-01-01", SaleOrder.order_date <= f"{y}-12-31",
            SaleOrder.is_reversed == False).group_by(func.strftime("%Y-%m", SaleOrder.order_date)).order_by(func.strftime("%Y-%m", SaleOrder.order_date)).all()
        chart_labels = []
        chart_data = []
        for mm, amt in results:
            chart_labels.append(mm)
            chart_data.append(round(amt, 2))
            total += amt
        chart_json = json.dumps({"labels": chart_labels, "data": chart_data})

    return templates.TemplateResponse("reports/sales_report.html", {
        "request": request, "period": period, "selected_date": selected_date, "total": total,
        "chart_json": chart_json, "prod_rank": prod_rank, "rows": rows,
    })
