from database import sessionlocal
from model import Product

db = sessionlocal()

try:

    product = db.query(Product).filter(
        Product.id == 5
    ).first()

    if product:

        db.delete(product)
        db.commit()

        print("Duplicate product deleted successfully.")

    else:

        print("Product with ID 5 not found.")

finally:

    db.close()