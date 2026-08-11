from datetime import datetime, timezone
from typing import Tuple


def generate_order_no(prefix: str, db_session) -> str:
    """???????: PO/SO-YYYYMMDD-XXX"""
    from sqlalchemy import func
    from nongzi.models.purchase import PurchaseOrder
    from nongzi.models.sale import SaleOrder
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    if prefix == "PO":
        model = PurchaseOrder
    elif prefix == "SO":
        model = SaleOrder
    else:
        raise ValueError(f"Unknown prefix: {prefix}")
    q = db_session.query(func.max(model.id)).filter(
        model.order_no.like(f"{prefix}-{today}-%")
    )
    max_id = q.scalar() or 0
    count = db_session.query(model).filter(
        model.order_no.like(f"{prefix}-{today}-%")
    ).count()
    seq = str(count + 1).zfill(3)
    return f"{prefix}-{today}-{seq}"


def mask_id_card(id_card: str) -> str:
    """????????: 3201****1234"""
    if not id_card or len(id_card) < 8:
        return id_card
    return f"{id_card[:4]}****{id_card[-4:]}"


def format_currency(amount: float) -> str:
    """???????"""
    if amount is None:
        return "0.00"
    return f"{amount:,.2f}"


def paginate(query, page: int = 1, per_page: int = 20) -> dict:
    """??????"""
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }


def get_or_create_default_warehouse(db_session):
    """?????????"""
    from nongzi.models.inventory import Warehouse
    wh = db_session.query(Warehouse).filter(Warehouse.is_default == True).first()
    if not wh:
        wh = Warehouse(name="????", is_default=True)
        db_session.add(wh)
        db_session.commit()
        db_session.refresh(wh)
    return wh
