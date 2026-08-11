"""丰收农资店管理系统 - FastAPI 入口"""
import os as _os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from nongzi.database import engine, Base, SessionLocal
from nongzi.config import STORE_NAME, BASE_DIR, DATA_DIR, VERSION
from nongzi.utils.helpers import format_currency


def seed_database():
    """初始化种子数据：默认仓库、用户、分类"""
    from nongzi.models.inventory import Warehouse
    from nongzi.models.system import User, SystemConfig
    from nongzi.models.product import Category

    db = SessionLocal()
    try:
        if not db.query(Warehouse).filter(Warehouse.is_default == True).first():
            db.add(Warehouse(name="默认仓库", is_default=True))
            print("[Seed] 创建默认仓库")
        if not db.query(User).filter(User.username == "admin").first():
            pw_hash = User.hash_password("admin123")
            db.add(User(username="admin", password_hash=pw_hash, role="admin", display_name="管理员"))
            print("[Seed] 创建管理员用户 (admin / admin123)")
        cat_names = ["种子", "农药", "化肥", "农膜", "饲料", "农具", "其他"]
        for i, name in enumerate(cat_names):
            if not db.query(Category).filter(Category.name == name, Category.parent_id == None).first():
                db.add(Category(name=name, sort_order=i, parent_id=None))
        db.flush()
        pesticide = db.query(Category).filter(Category.name == "农药", Category.parent_id == None).first()
        if pesticide:
            for i, name in enumerate(["杀虫剂", "杀菌剂", "除草剂", "植物生长调节剂"]):
                if not db.query(Category).filter(Category.name == name, Category.parent_id == pesticide.id).first():
                    db.add(Category(name=name, sort_order=i, parent_id=pesticide.id))
        db.commit()
        print("[Seed] 初始化完成")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _os.makedirs(_os.path.join(DATA_DIR, "exports"), exist_ok=True)
    _os.makedirs(_os.path.join(DATA_DIR, "backups"), exist_ok=True)
    seed_database()
    yield


app = FastAPI(title=f"{STORE_NAME}管理系统", version=VERSION, lifespan=lifespan)

app.mount("/static", StaticFiles(directory=_os.path.join(BASE_DIR, "static")), name="static")

templates = Jinja2Templates(directory=_os.path.join(BASE_DIR, "templates"))
templates.env.filters["currency"] = format_currency

from nongzi.routes.products import router as products_router
from nongzi.routes.contacts import router as contacts_router
from nongzi.routes.purchases import router as purchases_router
from nongzi.routes.sales import router as sales_router
from nongzi.routes.inventory import router as inventory_router
from nongzi.routes.finance import router as finance_router
from nongzi.routes.reports import router as reports_router
from nongzi.routes.system import router as system_router
from nongzi.routes.trace import router as trace_router

app.include_router(products_router)
app.include_router(contacts_router)
app.include_router(purchases_router)
app.include_router(sales_router)
app.include_router(inventory_router)
app.include_router(finance_router)
app.include_router(reports_router)
app.include_router(system_router)
app.include_router(trace_router)


@app.get("/")
def index(request: Request):
    """首页仪表盘 - 升级版"""
    from datetime import datetime, timedelta, date
    from sqlalchemy import func
    from nongzi.models.sale import SaleOrder
    from nongzi.models.product import Product
    from nongzi.models.inventory import Inventory, InventoryBatch
    from nongzi.models.contact import Customer
    from nongzi.models.finance import ARTransaction
    from nongzi.models.system import SystemConfig
    import json

    db = SessionLocal()
    try:
        today = datetime.now()
        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        
        today_sales = db.query(func.coalesce(func.sum(SaleOrder.total_amount), 0)).filter(
            SaleOrder.order_date >= today_start, SaleOrder.is_reversed == False).scalar() or 0
        today_order_count = db.query(func.count(SaleOrder.id)).filter(
            SaleOrder.order_date >= today_start, SaleOrder.is_reversed == False).scalar() or 0
        product_count = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar() or 0
        
        # AR total
        ar_total = db.query(func.coalesce(func.sum(ARTransaction.amount), 0)).filter(ARTransaction.type == "debit").scalar() or 0
        ar_paid = db.query(func.coalesce(func.sum(ARTransaction.amount), 0)).filter(ARTransaction.type == "credit").scalar() or 0
        ar_balance = ar_total - ar_paid
        
        # Expiry warning: batches expiring within 30 days
        thirty_days = today + timedelta(days=30)
        expiring = db.query(func.count(InventoryBatch.id)).filter(
            InventoryBatch.expiry_date <= thirty_days,
            InventoryBatch.expiry_date >= today,
            InventoryBatch.available_quantity > 0
        ).scalar() or 0
        
        # Low stock count
        low_stock_count = 0
        all_inv = db.query(Inventory, Product).join(Product).filter(Product.is_active == True, Inventory.available_quantity > 0).all()
        for inv, prod in all_inv:
            if prod.stock_min and inv.available_quantity < prod.stock_min:
                low_stock_count += 1
        
        # 7-day sales trend
        chart_labels = []
        chart_data = []
        for i in range(6, -1, -1):
            d = (today - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            d_end = d.replace(hour=23, minute=59, second=59, microsecond=999999)
            sd = db.query(func.coalesce(func.sum(SaleOrder.total_amount), 0)).filter(
                SaleOrder.order_date >= d, SaleOrder.order_date <= d_end, SaleOrder.is_reversed == False
            ).scalar() or 0
            chart_labels.append(d.strftime("%m/%d"))
            chart_data.append(round(sd, 2))
        
        # Expiring products table
        expiring_batches = db.query(InventoryBatch, Product).join(Product).filter(
            InventoryBatch.expiry_date <= thirty_days,
            InventoryBatch.expiry_date >= today,
            InventoryBatch.available_quantity > 0
        ).order_by(InventoryBatch.expiry_date.asc()).limit(10).all()
        expiring_rows = []
        for b, p in expiring_batches:
            days_left = (b.expiry_date - today).days
            expiring_rows.append({"product": p, "batch": b, "days_left": days_left})

        # License reminders
        license_warnings = []
        configs = {c.key: c.value for c in db.query(SystemConfig).all()}
        remind_days = int(configs.get("license_remind_days", "30"))
        today_date = today.date()

        pesticide_expiry_str = configs.get("license_pesticide_expiry", "")
        if pesticide_expiry_str:
            try:
                pe_date = date.fromisoformat(pesticide_expiry_str)
                days_left = (pe_date - today_date).days
                if 0 <= days_left <= remind_days:
                    license_warnings.append({"type": "农药经营许可证", "expiry": pesticide_expiry_str, "days_left": days_left})
                elif days_left < 0:
                    license_warnings.append({"type": "农药经营许可证", "expiry": pesticide_expiry_str, "days_left": days_left, "expired": True})
            except (ValueError, TypeError):
                pass

        biz_expiry_str = configs.get("license_business_expiry", "")
        if biz_expiry_str:
            try:
                be_date = date.fromisoformat(biz_expiry_str)
                days_left = (be_date - today_date).days
                if 0 <= days_left <= remind_days:
                    license_warnings.append({"type": "营业执照", "expiry": biz_expiry_str, "days_left": days_left})
                elif days_left < 0:
                    license_warnings.append({"type": "营业执照", "expiry": biz_expiry_str, "days_left": days_left, "expired": True})
            except (ValueError, TypeError):
                pass

        chart_json = json.dumps({"labels": chart_labels, "data": chart_data})
        
        return templates.TemplateResponse("index.html", {
            "request": request, "today_sales": today_sales,
            "today_order_count": today_order_count, "product_count": product_count,
            "low_stock_count": low_stock_count, "ar_balance": ar_balance,
            "expiry_count": expiring, "chart_json": chart_json,
            "expiring_rows": expiring_rows,
            "license_warnings": license_warnings,
            "version": VERSION,
        })
    finally:
        db.close()


@app.get("/setup")
def setup_page(request: Request):
    """首次运行引导页"""
    from nongzi.config import DATABASE_PATH, STORE_NAME as cfg_name, STORE_ADDRESS as cfg_addr, STORE_PHONE as cfg_phone
    templates_setup = Jinja2Templates(directory=_os.path.join(BASE_DIR, "templates"))
    return templates_setup.TemplateResponse("system/setup.html", {
        "request": request,
        "store_name": cfg_name,
        "store_address": cfg_addr,
        "store_phone": cfg_phone,
    })
from fastapi import Form
from fastapi.responses import JSONResponse

@app.post("/api/setup/init")
async def setup_init(
    store_name: str = Form(""), store_address: str = Form(""),
    store_phone: str = Form(""), load_demo: str = Form("0")
):
    """首次运行初始化"""
    from nongzi.models.system import SystemConfig
    from nongzi.config import DATABASE_PATH
    db = SessionLocal()
    try:
        # Save store info
        if store_name:
            _set_or_create(db, "store_name", store_name)
        if store_address:
            _set_or_create(db, "store_address", store_address)
        if store_phone:
            _set_or_create(db, "store_phone", store_phone)

        # Load demo data if requested
        if load_demo == "1":
            from nongzi.utils.demo_data import load_demo_data
            load_demo_data(db)

        db.commit()
        return JSONResponse({"success": True, "message": "初始化完成！"})
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "message": f"初始化失败: {str(e)}"})
    finally:
        db.close()

def _set_or_create(db, key, value):
    from nongzi.models.system import SystemConfig
    cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if cfg:
        cfg.value = value
    else:
        db.add(SystemConfig(key=key, value=value))
