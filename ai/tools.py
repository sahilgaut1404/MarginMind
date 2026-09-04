from langchain_core.tools import tool

from database import sessionlocal
from model import Product,Order,Bundle,Recommendation


@tool
def get_products():
    """Get all products available in the merchant catalog"""
    try:
        db=sessionlocal()
        products=db.query(Product).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "category": p.category,
                "stock": p.stock
            }
            for p in products
        ]
    finally:
        db.close()

@tool
def get_sales_summary():
   """Get sales summary from paid orders"""
   try:
    db=sessionlocal()
    orders=db.query(Order).filter(Order.status=="paid").all()
    total_orders = len(orders)
    total_units = sum(order.quantity for order in orders) 
    total_revenue = sum(order.amount for order in orders) 
    return{
       "Total Order":total_orders,
       "Total Units":total_units,
       "Total Revenue in Paise":total_revenue,
       "Total Revenue in Rupees":total_revenue/100
    }
   finally:
      db.close()
   
       
@tool
def get_product_sales():
   """Get sales performance for each product."""
   db=sessionlocal()

   try:
      products=db.query(Product).all()
      result=[]
      for product in products:
         orders=db.query(Order).filter(
            Order.product_id==product.id,
            Order.status=="paid"
         ).all()

         units_sold=sum(order.quantity for order in orders)
         revenue=sum(order.amount for order in orders)
         result.append({
            "product_id": product.id,
                "product_name": product.name,
                "units_sold": units_sold,
                "revenue_paise": revenue,
                "currency": "INR"
         })
    
      return result
   finally:
      db.close()





@tool
def analyze_growth():
    """Analyze product sales and identify revenue growth opportunities."""

    db = sessionlocal()

    try:
        products = db.query(Product).all()
        result = []

        for product in products:
            orders = db.query(Order).filter(
                Order.product_id == product.id,
                Order.status == "paid"
            ).all()

            units_sold = sum(order.quantity for order in orders)

            revenue_paise = sum(
                order.amount for order in orders
            )

            revenue_per_unit = (
                revenue_paise / units_sold
                if units_sold > 0
                else 0
            )

            result.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "units_sold": units_sold,
                    "current_price": product.price,
                    "current_price_inr": product.price / 100,
                    "revenue_paise": revenue_paise,
                    "revenue_inr": revenue_paise / 100,
                    "revenue_per_unit_paise": revenue_per_unit,
                    "revenue_per_unit_inr": revenue_per_unit / 100,
                    "stock": product.stock,
                    "currency": "INR"
                }
            )

        return result

    finally:
        db.close()


def create_bundle(
   name:str,
   product_1_id:int,
   product_2_id:int,
   bundle_price:int
):
   db=sessionlocal()
   try:
      product_1=db.query(Product).filter(Product.id==product_1_id).first()
      product_2=db.query(Product).filter(Product.id==product_2_id).first()
      
      if not product_1 or not product_2:
         raise ValueError("One or both products not found")
      if bundle_price<=0:
         raise ValueError("Bundle Price must be greater than 0")
      
      new_bundle=Bundle(
         name=name,
         product_1_id=product_1_id,
         product_2_id=product_2_id,
         bundle_price=bundle_price,
         status="pending"
      )
      db.add(new_bundle)
      db.commit()
      db.refresh(new_bundle)
      
      return{
         "status": "success",
         "bundle_id": new_bundle.id,
         "bundle_name": new_bundle.name,
         "bundle_price": new_bundle.bundle_price,
         "products": [
               product_1.name,
               product_2.name
            ]
      }
      
   except Exception:
      db.rollback()
      raise
   finally:
      db.close()


def update_product_price(product_id:int,new_price:int):
   db=sessionlocal()
   try:
      product=db.query(Product).filter(Product.id==product_id).first()
      
      if not product:
         raise ValueError("product not found")
      if new_price<0:
         raise ValueError("price must be greater than 0")
      old_price=product.price
      product.price=new_price
      
      db.commit()
      db.refresh(product)
      
      return {
         "status": "success",
         "product_id": product.id,
         "product_name": product.name,
         "old_price": old_price,
         "new_price": product.price,
         "currency": "INR"
        }
   except Exception:
      db.rollback()
      raise
   finally:
      db.close()
      


if __name__ == "__main__":
    db = sessionlocal()

    try:
        test_recommendation = Recommendation(
            action="increase_price",
            product_id=3,
            current_price=119900,
            suggested_price=150000,
            reason="Test recommendation for bounded action",
            status="pending"
        )

        db.add(test_recommendation)
        db.commit()
        db.refresh(test_recommendation)

        print({
            "id": test_recommendation.id,
            "current_price": test_recommendation.current_price,
            "suggested_price": test_recommendation.suggested_price,
            "status": test_recommendation.status
        })

    finally:
        db.close()