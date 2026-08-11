from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone
from nongzi.database import get_db
from nongzi.models.product import Category, Product
from nongzi.models.inventory import Inventory
from nongzi.utils.helpers import format_currency, paginate, get_or_create_default_warehouse

router = APIRouter(prefix="/products", tags=["商品管理"])

import os
from fastapi.templating import Jinja2Templates
from nongzi.config import BASE_DIR
_td = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=_td)
templates.env.filters["currency"] = format_currency

def _float_or_none(val: str):
    try: return float(val)
    except (ValueError, TypeError): return None

def _int_or_none(val: str):
    try: return int(val)
    except (ValueError, TypeError): return None

def _gen_product_code(db: Session):
    from sqlalchemy import func
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.query(func.count(Product.id)).filter(Product.code.like(f"SP-{today}-%")).scalar() or 0
    return f"SP-{today}-{str(count + 1).zfill(3)}"

def _product_suggestion(p, inv):
    return {
        "id": p.id, "code": p.code, "name": p.generic_name,
        "tradeName": p.trade_name or "", "spec": p.spec or "",
        "baseUnit": p.base_unit, "splitUnit": p.split_unit or "",
        "conversionRate": p.conversion_rate or 0,
        "retailPrice": p.retail_price or 0,
        "stock": round(inv.available_quantity, 2) if inv else 0,
        "isRestricted": p.is_restricted
    }

@router.get("/")
def list_products(request: Request, category_id: int = Query(None), search: str = Query(None), page: int = Query(1), db: Session = Depends(get_db)):
    query = db.query(Product)
    if category_id:
        cat_ids = [category_id]
        children = db.query(Category).filter(Category.parent_id == category_id, Category.is_active == True).all()
        cat_ids.extend([c.id for c in children])
        query = query.filter(Product.category_id.in_(cat_ids))
    if search:
        if search.startswith("SP-"):
            query = query.filter(Product.code == search)
        else:
            query = query.filter(or_(Product.generic_name.ilike(f"%{search}%"), Product.trade_name.ilike(f"%{search}%"), Product.barcode == search, Product.code.ilike(f"%{search}%")))
    query = query.filter(Product.is_active == True).order_by(Product.code.desc())
    result = paginate(query, page, 20)
    categories = db.query(Category).filter(Category.parent_id == None, Category.is_active == True).order_by(Category.sort_order).all()
    cat_tree = []
    for cat in categories:
        children = db.query(Category).filter(Category.parent_id == cat.id, Category.is_active == True).order_by(Category.sort_order).all()
        cat_tree.append({"cat": cat, "children": children})
    return templates.TemplateResponse("products/list.html", {"request": request, **result, "categories": cat_tree, "current_category_id": category_id, "search": search or ""})

@router.get("/search")
def search_products(request: Request, q: str = Query(""), db: Session = Depends(get_db)):
    if not q: return JSONResponse([])
    results = db.query(Product).filter(Product.is_active == True, or_(Product.barcode == q, Product.generic_name.ilike(f"%{q}%"), Product.trade_name.ilike(f"%{q}%"), Product.code.ilike(f"%{q}%"))).limit(10).all()
    data = []
    for p in results:
        inv = p.inventories[0] if p.inventories else None
        data.append({"id": p.id, "code": p.code, "name": p.generic_name, "tradeName": p.trade_name or "", "spec": p.spec or "", "baseUnit": p.base_unit, "splitUnit": p.split_unit or "", "conversionRate": p.conversion_rate or 0, "retailPrice": p.retail_price or 0, "stock": round(inv.available_quantity, 2) if inv else 0, "isRestricted": p.is_restricted})
    return JSONResponse(data)

@router.get("/api/by-barcode/{barcode}")
def api_by_barcode(barcode: str, db: Session = Depends(get_db)):
    """扫码枪条码查询API"""
    product = db.query(Product).filter(Product.barcode == barcode, Product.is_active == True).first()
    if not product:
        product = db.query(Product).filter(Product.code == barcode, Product.is_active == True).first()
    if not product:
        raise HTTPException(404, detail="未找到该条码商品")
    warehouse = get_or_create_default_warehouse(db)
    inv = db.query(Inventory).filter(Inventory.product_id == product.id, Inventory.warehouse_id == warehouse.id).first()
    return JSONResponse(_product_suggestion(product, inv))

@router.get("/api/suggestions")
def product_suggestions(q: str = Query(""), db: Session = Depends(get_db)):
    """搜索建议（拼音首字母+模糊匹配）"""
    if not q or len(q) < 1:
        return JSONResponse([])
    warehouse = get_or_create_default_warehouse(db)
    results = []
    seen_ids = set()
    # 1. 条码精确匹配
    exact = db.query(Product).filter(Product.barcode == q, Product.is_active == True).first()
    if exact:
        inv = db.query(Inventory).filter(Inventory.product_id == exact.id, Inventory.warehouse_id == warehouse.id).first()
        results.append(_product_suggestion(exact, inv))
        seen_ids.add(exact.id)
    # 2. 拼音首字母搜索
    try:
        from nongzi.utils.pinyin_search import search_by_pinyin as pinyin_fn
        pinyin_matches = pinyin_fn(db, Product, "generic_name", q)
        for p in pinyin_matches:
            if p.id in seen_ids: continue
            inv = db.query(Inventory).filter(Inventory.product_id == p.id, Inventory.warehouse_id == warehouse.id).first()
            results.append(_product_suggestion(p, inv))
            seen_ids.add(p.id)
    except Exception:
        pass
    # 3. 名称/编码模糊匹配
    fuzzy = db.query(Product).filter(Product.is_active == True, or_(
        Product.generic_name.ilike(f"%{q}%"),
        Product.trade_name.ilike(f"%{q}%"),
        Product.code.ilike(f"%{q}%")
    )).limit(8).all()
    for p in fuzzy:
        if p.id in seen_ids: continue
        inv = db.query(Inventory).filter(Inventory.product_id == p.id, Inventory.warehouse_id == warehouse.id).first()
        results.append(_product_suggestion(p, inv))
        seen_ids.add(p.id)
    return JSONResponse(results[:15])

@router.get("/new")
def new_product_form(request: Request, db: Session = Depends(get_db)):
    categories = db.query(Category).filter(Category.is_active == True).order_by(Category.parent_id, Category.sort_order).all()
    return templates.TemplateResponse("products/form.html", {"request": request, "product": None, "categories": categories, "toxicity_levels": [("", "无"), ("低毒", "低毒"), ("中等毒", "中等毒"), ("高毒", "高毒"), ("剧毒", "剧毒")]})

@router.get("/{id}")
def product_detail(request: Request, id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product: return RedirectResponse("/products", 302)
    return templates.TemplateResponse("products/detail.html", {"request": request, "product": product})

@router.get("/{id}/edit")
def edit_product_form(request: Request, id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product: return RedirectResponse("/products", 302)
    categories = db.query(Category).filter(Category.is_active == True).order_by(Category.parent_id, Category.sort_order).all()
    return templates.TemplateResponse("products/form.html", {"request": request, "product": product, "categories": categories, "toxicity_levels": [("", "无"), ("低毒", "低毒"), ("中等毒", "中等毒"), ("高毒", "高毒"), ("剧毒", "剧毒")]})

@router.post("/")
def create_product(request: Request, generic_name: str = Form(...), trade_name: str = Form(""), barcode: str = Form(""), spec: str = Form(""), formulation: str = Form(""), content: str = Form(""), toxicity: str = Form(""), reg_cert_no: str = Form(""), produce_lic_no: str = Form(""), manufacturer: str = Form(""), brand: str = Form(""), base_unit: str = Form(...), split_unit: str = Form(""), conversion_rate: str = Form(""), ref_cost: str = Form(""), retail_price: str = Form(""), wholesale_price: str = Form(""), member_price: str = Form(""), category_id: str = Form(""), db: Session = Depends(get_db)):
    code = _gen_product_code(db)
    is_restricted = toxicity in ["高毒", "剧毒"]
    product = Product(code=code, generic_name=generic_name, trade_name=trade_name, barcode=barcode, spec=spec, formulation=formulation, content=content, toxicity=toxicity, reg_cert_no=reg_cert_no, produce_lic_no=produce_lic_no, manufacturer=manufacturer, brand=brand, base_unit=base_unit, split_unit=split_unit, conversion_rate=_float_or_none(conversion_rate), ref_cost=_float_or_none(ref_cost), retail_price=_float_or_none(retail_price), wholesale_price=_float_or_none(wholesale_price), member_price=_float_or_none(member_price), is_restricted=is_restricted, category_id=_int_or_none(category_id))
    db.add(product)
    db.commit()
    return RedirectResponse("/products", 302)

@router.post("/{id}")
def update_product(request: Request, id: int, generic_name: str = Form(...), trade_name: str = Form(""), barcode: str = Form(""), spec: str = Form(""), formulation: str = Form(""), content: str = Form(""), toxicity: str = Form(""), reg_cert_no: str = Form(""), produce_lic_no: str = Form(""), manufacturer: str = Form(""), brand: str = Form(""), base_unit: str = Form(...), split_unit: str = Form(""), conversion_rate: str = Form(""), ref_cost: str = Form(""), retail_price: str = Form(""), wholesale_price: str = Form(""), member_price: str = Form(""), category_id: str = Form(""), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product: return RedirectResponse("/products", 302)
    product.generic_name = generic_name; product.trade_name = trade_name; product.barcode = barcode
    product.spec = spec; product.formulation = formulation; product.content = content
    product.toxicity = toxicity; product.reg_cert_no = reg_cert_no; product.produce_lic_no = produce_lic_no
    product.manufacturer = manufacturer; product.brand = brand; product.base_unit = base_unit
    product.split_unit = split_unit; product.conversion_rate = _float_or_none(conversion_rate); product.ref_cost = _float_or_none(ref_cost)
    product.retail_price = _float_or_none(retail_price); product.wholesale_price = _float_or_none(wholesale_price); product.member_price = _float_or_none(member_price)
    product.is_restricted = toxicity in ["高毒", "剧毒"]
    product.category_id = _int_or_none(category_id)
    product.updated_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse("/products", 302)

@router.get("/{id}/toggle")
def toggle_product(request: Request, id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if product:
        product.is_active = not product.is_active
        product.updated_at = datetime.now(timezone.utc)
        db.commit()
    return RedirectResponse("/products", 302)
