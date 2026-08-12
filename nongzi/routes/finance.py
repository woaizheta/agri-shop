from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from nongzi.database import get_db
from nongzi.utils.helpers import format_currency

router = APIRouter(prefix="/finance", tags=["财务管理"])

import os as _os, json
from fastapi.templating import Jinja2Templates
from nongzi.config import BASE_DIR
_td = _os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=_td)
templates.env.filters["currency"] = format_currency


@router.get("/")
def finance_index(request: Request):
    return RedirectResponse("/finance/ar", 302)


@router.get("/ar")
def ar_list(request: Request, search: str = Query(None), db: Session = Depends(get_db)):
    from nongzi.models.contact import Customer
    from nongzi.models.sale import SaleOrder
    from nongzi.models.finance import ARTransaction
    from datetime import datetime, timezone
    from sqlalchemy import func
    today = datetime.now(timezone.utc)
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    customers = db.query(Customer).filter(Customer.is_active == True)
    if search:
        customers = customers.filter(Customer.name.ilike(f"%{search}%"))
    customers = customers.order_by(Customer.name).all()
    rows = []
    for cust in customers:
        credit_sales = db.query(func.coalesce(func.sum(SaleOrder.total_amount), 0)).filter(
            SaleOrder.customer_id == cust.id, SaleOrder.payment_method == "credit",
            SaleOrder.order_date >= month_start, SaleOrder.is_reversed == False).scalar() or 0
        repayments = db.query(func.coalesce(func.sum(ARTransaction.amount), 0)).filter(
            ARTransaction.customer_id == cust.id, ARTransaction.type == "credit",
            ARTransaction.created_at >= month_start).scalar() or 0
        all_debits = db.query(func.coalesce(func.sum(ARTransaction.amount), 0)).filter(ARTransaction.customer_id == cust.id, ARTransaction.type == "debit").scalar() or 0
        all_credits = db.query(func.coalesce(func.sum(ARTransaction.amount), 0)).filter(ARTransaction.customer_id == cust.id, ARTransaction.type == "credit").scalar() or 0
        balance = round(all_debits - all_credits, 2)
        rows.append({"customer": cust, "credit_sales": credit_sales, "repayments": repayments,
                     "balance": balance})
    return templates.TemplateResponse("finance/ar_list.html",
                                      {"request": request, "rows": rows, "search": search or ""})


@router.get("/api/unpaid-orders")
def api_unpaid_orders(customer_id: int = Query(...), db: Session = Depends(get_db)):
    from nongzi.models.sale import SaleOrder
    from nongzi.models.finance import ARTransaction
    from sqlalchemy import func
    orders = db.query(SaleOrder).filter(SaleOrder.customer_id == customer_id, SaleOrder.payment_method == "credit", SaleOrder.is_reversed == False).order_by(SaleOrder.order_date.asc()).all()
    data = []
    for o in orders:
        paid = db.query(func.coalesce(func.sum(ARTransaction.amount), 0)).filter(ARTransaction.customer_id == customer_id, ARTransaction.type == "credit", (ARTransaction.sale_order_id == o.id) | (ARTransaction.sale_order_id == None)).scalar() or 0
        unpaid = o.total_amount - paid
        if unpaid <= 0: continue
        # Sync paid_amount column
        if abs((o.paid_amount or 0) - paid) > 0.01:
            o.paid_amount = paid
            o.is_paid = paid >= o.total_amount
        data.append({"id": o.id, "order_no": o.order_no, "amount": round(unpaid, 2), "date": o.order_date.strftime("%Y-%m-%d") if o.order_date else ""})
    if data:
        db.commit()
    return JSONResponse(data)

@router.post("/repay")
def repay(request: Request, customer_id: int = Form(...), amount: float = Form(0.0), sale_order_ids: str = Form(""),
          note: str = Form(""), db: Session = Depends(get_db)):
    from nongzi.models.contact import Customer
    from nongzi.models.finance import ARTransaction
    from nongzi.models.sale import SaleOrder
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust: return RedirectResponse("/finance/ar", 302)
    if amount <= 0: return RedirectResponse("/finance/ar", 302)
    unpaid = db.query(SaleOrder).filter(
        SaleOrder.customer_id == customer_id, SaleOrder.payment_method == "credit",
        SaleOrder.is_reversed == False).order_by(SaleOrder.order_date.asc()).all()
    selected_ids = []
    if sale_order_ids:
        selected_ids = [int(x.strip()) for x in sale_order_ids.split(",") if x.strip()]
    if selected_ids:
        unpaid = [o for o in unpaid if o.id in selected_ids]
    else:
        unpaid = [o for o in unpaid if not o.is_paid]
    remaining = amount
    total_balance = cust.credit_balance
    for order in unpaid:
        if remaining <= 0: break
        unpaid_amt = order.total_amount - (order.paid_amount or 0)
        if unpaid_amt <= 0: continue
        settle = min(remaining, unpaid_amt)
        order.paid_amount = (order.paid_amount or 0) + settle
        if order.paid_amount >= order.total_amount:
            order.is_paid = True
        new_balance = total_balance - settle
        db.add(ARTransaction(customer_id=customer_id, sale_order_id=order.id, type="credit",
                             amount=settle, balance_after=new_balance,
                             note=note or f"还款核销 {order.order_no}"))
        total_balance = new_balance
        remaining -= settle
    db.commit()
    return RedirectResponse("/finance/ar", 302)


@router.get("/ap")
def ap_list(request: Request, search: str = Query(None), db: Session = Depends(get_db)):
    from nongzi.models.contact import Supplier
    from nongzi.models.purchase import PurchaseOrder
    from nongzi.models.finance import APTransaction
    from datetime import datetime, timezone
    from sqlalchemy import func
    today = datetime.now(timezone.utc)
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    suppliers = db.query(Supplier).filter(Supplier.is_active == True)
    if search: suppliers = suppliers.filter(Supplier.name.ilike(f"%{search}%"))
    suppliers = suppliers.order_by(Supplier.name).all()
    rows = []
    for sup in suppliers:
        purchases = db.query(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).filter(
            PurchaseOrder.supplier_id == sup.id, PurchaseOrder.order_date >= month_start,
            PurchaseOrder.is_reversed == False).scalar() or 0
        payments = db.query(func.coalesce(func.sum(APTransaction.amount), 0)).filter(
            APTransaction.supplier_id == sup.id, APTransaction.type == "debit",
            APTransaction.created_at >= month_start).scalar() or 0
        total_p = db.query(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).filter(
            PurchaseOrder.supplier_id == sup.id, PurchaseOrder.is_reversed == False).scalar() or 0
        total_pay = db.query(func.coalesce(func.sum(APTransaction.amount), 0)).filter(
            APTransaction.supplier_id == sup.id, APTransaction.type == "debit").scalar() or 0
        rows.append({"supplier": sup, "purchases": purchases, "payments": payments,
                     "balance": round(total_p - total_pay, 2)})
    return templates.TemplateResponse("finance/ap_list.html",
                                      {"request": request, "rows": rows, "search": search or ""})


@router.get("/api/unpaid-purchases")
def api_unpaid_purchases(supplier_id: int = Query(...), db: Session = Depends(get_db)):
    from sqlalchemy import func
    from nongzi.models.finance import APTransaction
    from nongzi.models.purchase import PurchaseOrder
    orders = db.query(PurchaseOrder).filter(PurchaseOrder.supplier_id == supplier_id, PurchaseOrder.is_reversed == False).order_by(PurchaseOrder.order_date.asc()).all()
    data = []
    for o in orders:
        paid = db.query(func.coalesce(func.sum(APTransaction.amount), 0)).filter(APTransaction.purchase_order_id == o.id, APTransaction.type == "payment").scalar() or 0
        unpaid = o.total_amount - paid
        if unpaid <= 0: continue
        data.append({"id": o.id, "order_no": o.order_no, "amount": round(unpaid, 2), "date": o.order_date.strftime("%Y-%m-%d") if o.order_date else ""})
    return JSONResponse(data)

@router.post("/pay")
def pay_supplier(request: Request, supplier_id: int = Form(...), amount: float = Form(...),
                 note: str = Form(""), db: Session = Depends(get_db)):
    from nongzi.models.finance import APTransaction
    from nongzi.models.purchase import PurchaseOrder
    from sqlalchemy import func
    if amount <= 0: return RedirectResponse("/finance/ap", 302)
    total_p = db.query(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).filter(
        PurchaseOrder.supplier_id == supplier_id, PurchaseOrder.is_reversed == False).scalar() or 0
    total_pay = db.query(func.coalesce(func.sum(APTransaction.amount), 0)).filter(
        APTransaction.supplier_id == supplier_id, APTransaction.type == "debit").scalar() or 0
    new_balance = total_p - total_pay - amount
    db.add(APTransaction(supplier_id=supplier_id, type="debit", amount=amount,
                         balance_after=new_balance, note=note or "付款"))
    db.commit()
    return RedirectResponse("/finance/ap", 302)


@router.get("/expenses")
def expense_list(request: Request, month: str = Query(None), db: Session = Depends(get_db)):
    from nongzi.models.finance import Expense
    from datetime import datetime, timezone
    from sqlalchemy import func
    today = datetime.now(timezone.utc)
    if not month: month = today.strftime("%Y-%m")
    try: y, m = int(month[:4]), int(month[5:7])
    except: y, m = today.year, today.month
    start = datetime(y, m, 1, tzinfo=timezone.utc)
    if m == 12: end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else: end = datetime(y, m + 1, 1, tzinfo=timezone.utc)
    expenses = db.query(Expense).filter(
        Expense.expense_date >= start, Expense.expense_date < end).order_by(Expense.expense_date.desc()).all()
    total = sum(e.amount for e in expenses)
    cat_totals = {}
    for e in expenses:
        cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount
    pie_data = json.dumps([{"category": k, "amount": v} for k, v in cat_totals.items()])
    return templates.TemplateResponse("finance/expenses.html",
                                      {"request": request, "expenses": expenses, "total": total,
                                       "month": month, "pie_data": pie_data})


@router.post("/expenses")
def add_expense(request: Request, category: str = Form(...), amount: float = Form(...),
                expense_date: str = Form(...), note: str = Form(""), db: Session = Depends(get_db)):
    from nongzi.models.finance import Expense
    from datetime import datetime as dt
    ed = dt.strptime(expense_date, "%Y-%m-%d") if expense_date else None
    db.add(Expense(category=category, amount=amount, expense_date=ed, note=note))
    db.commit()
    return RedirectResponse("/finance/expenses", 302)


@router.get("/profit")
def profit_view(request: Request, period: str = Query("week"), date_from: str = Query(None),
                date_to: str = Query(None), db: Session = Depends(get_db)):
    from nongzi.models.sale import SaleOrder, SaleItem
    from nongzi.models.finance import Expense
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func
    today = datetime.now(timezone.utc)
    if not date_to: date_to = today.strftime("%Y-%m-%d")
    try: end_date = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except: end_date = today
    if period == "week": start_date = end_date - timedelta(days=6)
    elif period == "month": start_date = end_date - timedelta(days=29)
    else:
        start_date = datetime(end_date.year, 1, 1, tzinfo=timezone.utc)
    if date_from:
        try: start_date = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except: pass
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    sales = db.query(func.coalesce(func.sum(SaleOrder.total_amount), 0)).filter(
        SaleOrder.order_date >= start_date, SaleOrder.order_date <= end_date,
        SaleOrder.is_reversed == False).scalar() or 0
    cost = db.query(func.coalesce(func.sum(SaleItem.quantity * SaleItem.cost_price_at_sale), 0)).join(SaleOrder).filter(
        SaleOrder.order_date >= start_date, SaleOrder.order_date <= end_date,
        SaleOrder.is_reversed == False).scalar() or 0
    expenses = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.expense_date >= start_date, Expense.expense_date <= end_date).scalar() or 0
    
    gross = sales - cost
    net = gross - expenses
    
    chart_labels, chart_sales, chart_cost, chart_expense = [], [], [], []
    if period in ("week", "month"):
        for i in range((end_date - start_date).days + 1):
            d = start_date + timedelta(days=i)
            de = d.replace(hour=23, minute=59, second=59, microsecond=999999)
            sd = db.query(func.coalesce(func.sum(SaleOrder.total_amount), 0)).filter(
                SaleOrder.order_date >= d, SaleOrder.order_date <= de, SaleOrder.is_reversed == False).scalar() or 0
            cd = db.query(func.coalesce(func.sum(SaleItem.quantity * SaleItem.cost_price_at_sale), 0)).join(SaleOrder).filter(
                SaleOrder.order_date >= d, SaleOrder.order_date <= de, SaleOrder.is_reversed == False).scalar() or 0
            ed = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
                Expense.expense_date >= d, Expense.expense_date <= de).scalar() or 0
            chart_labels.append(d.strftime("%Y-%m-%d"))
            chart_sales.append(round(sd, 2)); chart_cost.append(round(cd, 2)); chart_expense.append(round(ed, 2))
    else:
        m, y = start_date.month, start_date.year
        while datetime(y, m, 1, tzinfo=timezone.utc) <= end_date:
            ms = datetime(y, m, 1, tzinfo=timezone.utc)
            me = (datetime(y, m+1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)) if m < 12 else datetime(y+1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
            sd = db.query(func.coalesce(func.sum(SaleOrder.total_amount), 0)).filter(
                SaleOrder.order_date >= ms, SaleOrder.order_date <= me, SaleOrder.is_reversed == False).scalar() or 0
            cd = db.query(func.coalesce(func.sum(SaleItem.quantity * SaleItem.cost_price_at_sale), 0)).join(SaleOrder).filter(
                SaleOrder.order_date >= ms, SaleOrder.order_date <= me, SaleOrder.is_reversed == False).scalar() or 0
            ed = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
                Expense.expense_date >= ms, Expense.expense_date <= me).scalar() or 0
            chart_labels.append(f"{y}-{m:02d}")
            chart_sales.append(round(sd, 2)); chart_cost.append(round(cd, 2)); chart_expense.append(round(ed, 2))
            m += 1
            if m > 12: m = 1; y += 1
    
    chart_data = json.dumps({"labels": chart_labels, "sales": chart_sales, "cost": chart_cost, "expense": chart_expense})
    return templates.TemplateResponse("finance/profit.html", {
        "request": request, "sales": sales, "cost": cost, "expenses": expenses,
        "gross": gross, "net": net, "period": period,
        "date_from": start_date.strftime("%Y-%m-%d"), "date_to": end_date.strftime("%Y-%m-%d"),
        "chart_data": chart_data,
    })
