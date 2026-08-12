from nongzi.database import SessionLocal
from nongzi.models.product import Product
db = SessionLocal()
a = db.query(Product).filter(Product.is_active == True).count()
i = db.query(Product).filter(Product.is_active == False).count()
print(f"active={a} inactive={i}")
db.close()