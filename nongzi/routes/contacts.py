from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone
from nongzi.database import get_db
from nongzi.models.contact import Supplier, Customer
from nongzi.utils.helpers import format_currency, paginate, mask_id_card


def _float_or_none(val: str):
    try: return float(val)
    except (ValueError, TypeError): return None

router = APIRouter(prefix='/contacts', tags=['往来单位'])

@router.get("/api/customers")
def api_customers(q: str = Query(""), db: Session = Depends(get_db)):
    from nongzi.models.contact import Customer
    from nongzi.models.finance import ARTransaction
    if not q or len(q) < 1: return JSONResponse([])
    customers = db.query(Customer).filter(Customer.is_active == True, Customer.name.ilike(f"%{q}%")).limit(10).all()
    data = []
    for c in customers:
        balance = sum(t.amount if t.type == "debit" else -t.amount for t in db.query(ARTransaction).filter(ARTransaction.customer_id == c.id).all())
        data.append({"id": c.id, "name": c.name, "phone": c.phone or "", "balance": round(balance, 2)})
    return JSONResponse(data)

import os
from fastapi.templating import Jinja2Templates
from nongzi.config import BASE_DIR
_td = os.path.join(BASE_DIR, 'templates')
templates = Jinja2Templates(directory=_td)
templates.env.filters['currency'] = format_currency
templates.env.filters['mask_id'] = mask_id_card


@router.get('/suppliers')
def supplier_list(request: Request, search: str = Query(None), page: int = Query(1), db: Session = Depends(get_db)):
    query = db.query(Supplier).filter(Supplier.is_active == True)
    if search: query = query.filter(or_(Supplier.name.ilike(f'%{search}%'), Supplier.contact.ilike(f'%{search}%'), Supplier.phone.ilike(f'%{search}%')))
    query = query.order_by(Supplier.name)
    result = paginate(query, page, 20)
    return templates.TemplateResponse('contacts/supplier_list.html', {'request': request, 'tab': 'suppliers', **result, 'search': search or ''})


@router.get('/suppliers/new')
def new_supplier_form(request: Request):
    return templates.TemplateResponse('contacts/supplier_form.html', {'request': request, 'supplier': None})


@router.get('/suppliers/{id}/edit')
def edit_supplier_form(request: Request, id: int, db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.id == id).first()
    if not s: return RedirectResponse('/contacts/suppliers', 302)
    return templates.TemplateResponse('contacts/supplier_form.html', {'request': request, 'supplier': s})


@router.post('/suppliers')
def create_supplier(name: str = Form(...), credit_code: str = Form(''), contact: str = Form(''), phone: str = Form(''), address: str = Form(''), pesticide_lic_no: str = Form(''), note: str = Form(''), db: Session = Depends(get_db)):
    db.add(Supplier(name=name, credit_code=credit_code, contact=contact, phone=phone, address=address, pesticide_lic_no=pesticide_lic_no, note=note))
    db.commit()
    return RedirectResponse('/contacts/suppliers', 302)


@router.post('/suppliers/{id}')
def update_supplier(id: int, name: str = Form(...), credit_code: str = Form(''), contact: str = Form(''), phone: str = Form(''), address: str = Form(''), pesticide_lic_no: str = Form(''), note: str = Form(''), db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.id == id).first()
    if not s: return RedirectResponse('/contacts/suppliers', 302)
    s.name = name; s.credit_code = credit_code; s.contact = contact; s.phone = phone
    s.address = address; s.pesticide_lic_no = pesticide_lic_no; s.note = note
    s.updated_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse('/contacts/suppliers', 302)


@router.get('/suppliers/{id}/delete')
def delete_supplier(id: int, db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.id == id).first()
    if s: s.is_active = False; db.commit()
    return RedirectResponse('/contacts/suppliers', 302)


@router.get('/customers')
def customer_list(request: Request, search: str = Query(None), page: int = Query(1), db: Session = Depends(get_db)):
    query = db.query(Customer).filter(Customer.is_active == True)
    if search: query = query.filter(or_(Customer.name.ilike(f'%{search}%'), Customer.phone.ilike(f'%{search}%'), Customer.id_card.ilike(f'%{search}%')))
    query = query.order_by(Customer.name)
    result = paginate(query, page, 20)
    return templates.TemplateResponse('contacts/customer_list.html', {'request': request, 'tab': 'customers', **result, 'search': search or ''})


@router.get('/customers/new')
def new_customer_form(request: Request):
    return templates.TemplateResponse('contacts/customer_form.html', {'request': request, 'customer': None})


@router.get('/customers/{id}')
def customer_detail(request: Request, id: int, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == id).first()
    if not c: return RedirectResponse('/contacts/customers', 302)
    return templates.TemplateResponse('contacts/customer_detail.html', {'request': request, 'customer': c})


@router.get('/customers/{id}/edit')
def edit_customer_form(request: Request, id: int, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == id).first()
    if not c: return RedirectResponse('/contacts/customers', 302)
    return templates.TemplateResponse('contacts/customer_form.html', {'request': request, 'customer': c})


@router.post('/customers')
def create_customer(name: str = Form(...), phone: str = Form(...), id_card: str = Form(''), address: str = Form(''), tag: str = Form('farmer'), crops: str = Form(''), farm_area: str = Form(''), db: Session = Depends(get_db)):
    db.add(Customer(name=name, phone=phone, id_card=id_card, address=address, tag=tag, crops=crops, farm_area=_float_or_none(farm_area)))
    db.commit()
    return RedirectResponse('/contacts/customers', 302)


@router.post('/customers/{id}')
def update_customer(id: int, name: str = Form(...), phone: str = Form(...), id_card: str = Form(''), address: str = Form(''), tag: str = Form('farmer'), crops: str = Form(''), farm_area: str = Form(''), db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == id).first()
    if not c: return RedirectResponse('/contacts/customers', 302)
    c.name = name; c.phone = phone; c.id_card = id_card; c.address = address
    c.tag = tag; c.crops = crops; c.farm_area = _float_or_none(farm_area)
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse('/contacts/customers', 302)


@router.get('/customers/{id}/delete')
def delete_customer(id: int, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == id).first()
    if c: c.is_active = False; db.commit()
    return RedirectResponse('/contacts/customers', 302)
