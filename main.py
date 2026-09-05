from database import engine,sessionlocal,base
from model import Payment,Product,Order,Bundle,Recommendation,AuditLog
import os
import razorpay
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI,Request,HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from ai.agent import agent,structured_llm,RecommendationOutput,save_recommendation
from ai.tools import analyze_growth
load_dotenv()
app=FastAPI()
template=Jinja2Templates(directory="template")

base.metadata.create_all(bind=engine)

key_id=os.getenv("RAZORPAY_KEY_ID")
key_secret=os.getenv("RAZORPAY_KEY_SECRET")

client=razorpay.Client(
    auth=(key_id,key_secret)
    )
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

class orderrequest(BaseModel):
    amount:int
    product_id:int
    quantity: int
class productrequest(BaseModel):
    name: str
    price: int
    category: str
    stock: int
class chatrequest(BaseModel):
    message:str

@app.get("/razorpay-key")
def get_razorpay_key():
    return {
        "key_id": key_id
    }
@app.post('/order')
def req(ord:orderrequest):
    data={
        "amount":ord.amount,
        "currency":"INR",
        "receipt":"test001",
        "notes": {
        "product_id": str(ord.product_id),
        "quantity": str(ord.quantity)
        }
    }
    
    order=client.order.create(data=data)
    return order
class paymentverification(BaseModel):
    razorpay_payment_id:str
    razorpay_order_id:str
    razorpay_signature:str

@app.post('/verify-payment')
def verify_payment(payment:paymentverification):
    db=sessionlocal()
    
    try:
        existing_payment=db.query(Payment).filter(
            Payment.payment_id==payment.razorpay_payment_id
        ).first()
        if existing_payment:
            raise HTTPException(
                status_code=409,
                detail="Payment Already Processed"
            )
        client.utility.verify_payment_signature({
            "razorpay_order_id": payment.razorpay_order_id,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "razorpay_signature": payment.razorpay_signature

        })
        order_details=client.order.fetch(
            payment.razorpay_order_id
        )
        amount=order_details["amount"]
        currency=order_details["currency"]
        product_id = int(
            order_details["notes"]["product_id"]
        )

        quantity = int(
            order_details["notes"]["quantity"]
        )
        product = db.query(Product).filter(
                Product.id == product_id
            ).first()
        if product is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        if product.stock < quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient stock"
            )

        product.stock -= quantity
        new_payment=Payment(
            order_id=payment.razorpay_order_id,
            payment_id=payment.razorpay_payment_id,
            amount=amount,
            currency=currency,
            status="verified"
        )
        db.add(new_payment)
        new_order = Order(

            product_id=product_id,

            quantity=quantity,

            amount=amount,

            status="paid"

        )

        db.add(new_order)
        db.commit()
        return{
            "Status":"success",
            "Message":"Payment Verified successfully"
        }
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Payment Verfication Failed"
        )
    finally:
        db.close()



@app.get('/payment')
def get_payments():
    db=sessionlocal()

    try:
        payments=db.query(Payment).all()
        return payments
    finally:
        db.close()

@app.post('/product')
def create_product(product:productrequest):
    db=sessionlocal()
    try:
        new_product=Product(
            name=product.name,
            price=product.price,
            category=product.category,
            stock=product.stock
        )
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

        return new_product
    finally:
        db.close()
@app.get('/product')
def get_product():
    db=sessionlocal()
    try:
        products=db.query(Product).all()
        return products
    finally:
        db.close()

@app.post("/price change approval")
def price_change_approval(recommendation_id:int):
    db=sessionlocal()
    
    try:
        recommendation=db.query(Recommendation).filter(Recommendation.id==recommendation_id).first()
        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail="recommendation not found"
                
            )
        if recommendation.status!="pending":
            raise HTTPException(
                status_code=400,
                detail="recommendation is not pending"
            )
        if recommendation.action not in ["increase_price", "decrease_price"]:
            raise HTTPException(
                status_code=400,
                detail="recommendation action is invalid"
            )
        
        product=db.query(Product).filter(Product.id==recommendation.product_id).first()
        
        if not product:
            raise HTTPException(
                status_code=400,
                detail="product not found"
            )
        if product.price !=recommendation.current_price:
            raise HTTPException(
                status_code=400,
                detail="product price has changed since recommendation"
            )
        max_change=recommendation.current_price*0.10
        price_diff=abs(recommendation.suggested_price-recommendation.current_price)
        
        if price_diff>max_change:
            audit = AuditLog(
            recommendation_id=recommendation.id,
            action=recommendation.action,
            product_id=product.id,
            old_price=product.price,
            new_price=recommendation.suggested_price,
            status="blocked",
            reason="Price change exceeds the allowed 10% limit"
        )

            db.add(audit)
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="price chamge exceeds the allowed 10% limit"
            )
        old_price=product.price
        product.price=recommendation.suggested_price
        recommendation.status="approved"
        audit=AuditLog(
            recommendation_id=recommendation.id,
            action=recommendation.action,
            product_id=product.id,
            old_price=old_price,
            new_price=product.price,
            status="success",
            reason=recommendation.reason
        )
        db.add(audit)
        db.commit()
        db.refresh(product)
        db.refresh(recommendation)
        return {
            "status": "success",
            "message": "Price recommendation approved",
            "recommendation_id": recommendation.id,
            "product_id": product.id,
            "product_name": product.name,
            "old_price": old_price,
            "new_price": product.price,
            "recommendation_status": recommendation.status
        }
        
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        
        raise HTTPException(
            status_code=500,
            detail="failed to approve price recommendation"
        )
    finally:
        db.close()

@app.get("/audit logs")
def get_audit_logs():
    db=sessionlocal()
    
    try:
        logs=db.query(AuditLog).all()
        
        return[{
            "id": log.id,
            "recommendation_id": log.recommendation_id,
            "action": log.action,
            "product_id": log.product_id,
            "old_price": log.old_price,
            "new_price": log.new_price,
            "status": log.status,
            "reason": log.reason
            }
               for log in logs   
        ]
    finally:
        db.close()
        
@app.get("/recommendations")
def get_recommendation():

    db = sessionlocal()

    try:
        recommendations = db.query(Recommendation).filter(
            Recommendation.status == "pending"
        ).all()

        result = []

        for recommendation in recommendations:

            product = db.query(Product).filter(
                Product.id == recommendation.product_id
            ).first()

            if not product:
                continue

            
            if product.price != recommendation.current_price:
                continue

            
            max_change = recommendation.current_price // 10

            price_diff = abs(
                recommendation.suggested_price -
                recommendation.current_price
            )

            
            if price_diff > max_change:
                continue

            result.append({
                "id": recommendation.id,
                "action": recommendation.action,
                "product_id": recommendation.product_id,
                "current_price": recommendation.current_price,
                "suggested_price": recommendation.suggested_price,
                "reason": recommendation.reason,
                "status": recommendation.status
            })

        return result

    finally:
        db.close()

@app.post("/reject recommendation")
def reject(recommendation_id:int):
    db=sessionlocal()
    try:
        recommendation=db.query(Recommendation).filter(Recommendation.id==recommendation_id).first()
        
        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail="recommendation not found"
            )
        if recommendation.status!="pending":
            raise HTTPException(
                status_code=400,
                detail="recommendation is not pending"
            )
        recommendation.status="rejected"
        audit = AuditLog(
            recommendation_id=recommendation.id,
            action=recommendation.action,
            product_id=recommendation.product_id,
            old_price=recommendation.current_price,
            new_price=recommendation.suggested_price,
            status="rejected",
            reason="Merchant rejected the recommendation"
        )

        db.add(audit)
        db.commit()
        db.refresh(recommendation)
        
        return{
            "status": "success",
            "message": "Recommendation rejected",
            "recommendation_id": recommendation.id,
            "recommendation_status": recommendation.status
        }
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="failed to reject"
        )
    finally:
        db.close()
    
@app.get('/dashboard')
def dash(request:Request):
    return template.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "key_id":key_id
        }
    )
@app.get("/dashboard summary")
def summary():
    db=sessionlocal()
    
    try:
        orders=db.query(Order).filter(Order.status=="paid").all()
        total_revenue=sum(order.amount for order in orders)
        total_orders=len(orders)
        units_sold=sum(order.quantity for order in orders)
        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "units_sold": units_sold
        }
    finally:
        db.close()
        
chat_history = []
pending_recommendation = None
recommendation_saved = False


@app.post("/chat")
def chat(request: chatrequest):

    global pending_recommendation
    global recommendation_saved

    user_message = request.message.strip()
    lower_message = user_message.lower()

    YES_MESSAGES = [
        "yes",
        "yes please",
        "proceed",
        "go ahead",
        "do it",
        "ok","okay"
    ]

    NO_MESSAGES = [
        "no",
        "no thanks",
        "cancel"
    ]

    if (
        pending_recommendation is not None
        and lower_message in YES_MESSAGES
    ):

        db = sessionlocal()

        try:

            product = db.query(Product).filter(
                Product.id == pending_recommendation.product_id
            ).first()

    
            if product is None:

                pending_recommendation = None
                recommendation_saved = False

                answer = """
 Recommendation is no longer valid.

The product no longer exists.

Please ask me for a new pricing recommendation.
"""

            
            

            elif (
                product.price
                != pending_recommendation.current_price
            ):

                pending_recommendation = None
                recommendation_saved = False

                answer = """
 Recommendation is no longer valid.

The product price has changed since the recommendation
was created.

The old recommendation was NOT saved.

Please ask me for a new pricing recommendation.
"""


            else:

                saved = save_recommendation(
                    pending_recommendation
                )

                pending_recommendation = None
                recommendation_saved = True

                answer = f"""
 Recommendation prepared.

Product ID: {saved.product_id}

Action: {saved.action}

Current Price: ₹{saved.current_price / 100:.2f}

Suggested Price: ₹{saved.suggested_price / 100:.2f}

 Reason

{saved.reason}

 Status

Pending Merchant Approval

The price has NOT been changed.

Please approve or reject this recommendation
from the Recommendations page.
"""

        finally:
            db.close()

        chat_history.append({
            "role": "user",
            "content": user_message
        })

        chat_history.append({
            "role": "assistant",
            "content": answer
        })

        return {
            "response": answer
        }



    if (
        pending_recommendation is not None
        and lower_message in NO_MESSAGES
    ):

        pending_recommendation = None
        recommendation_saved = False

        answer = """
Okay, I won't prepare the recommendation.

You can ask me about another product or business metric.
"""

        chat_history.append({
            "role": "user",
            "content": user_message
        })

        chat_history.append({
            "role": "assistant",
            "content": answer
        })

        return {
            "response": answer
        }

    if (
        recommendation_saved
        and lower_message in YES_MESSAGES
    ):

        answer = """
The pricing recommendation is already prepared.

Please approve or reject it from the Recommendations page.

The price has NOT been changed.
"""

        chat_history.append({
            "role": "user",
            "content": user_message
        })

        chat_history.append({
            "role": "assistant",
            "content": answer
        })

        return {
            "response": answer
        }



    chat_history.append({
        "role": "user",
        "content": user_message
    })

    response = agent.invoke({
        "messages": chat_history
    })

    answer = response["messages"][-1].content



    lower_answer = answer.lower()

    if (
        "pricing recommendation" in lower_answer
        and (
            "increase price" in lower_answer
            or "decrease price" in lower_answer
        )
    ):

        growth_data = analyze_growth.invoke({})

        recommendation_prompt = f"""
    You are MarginMind's pricing recommendation engine.

    Merchant data:

    {growth_data}

    The MarginMind assistant has already analyzed the merchant data
    and recommended a product:

    {answer}

    Create the SAME recommendation described by the assistant.

    IMPORTANT:

    1. Do NOT choose a different product.

    2. Do NOT choose a different action.

    3. Use the exact product and action mentioned in the assistant's
    recommendation.

    4. The product_id MUST exactly match the product_id of the
    recommended product in merchant data.

    5. Do NOT invent, calculate, guess, or modify the product_id.

    6. The current_price MUST exactly match the current_price of
    the recommended product in merchant data.

    7. Do NOT calculate, estimate, round, modify, or invent
    current_price.

    8. The product_id and current_price MUST come from the same
    product record in merchant data.

    9. Prices are stored in paise.

    10. 100 paise = ₹1.00.

    11. Never divide prices by 1000.

    12. Never add or subtract arbitrary amounts from current_price.

    Allowed actions:

    - increase_price
    - decrease_price

    Pricing rules:

    13. The application will calculate suggested_price,
        Do not calculate suggested_price yourself,
        Return the product_id and action based on the merchant data,
        Return current_price from the merchant data
    14. The maximum allowed price change is 10%.

    15. For increase_price, the suggested price is:

    current_price + (current_price // 10)

    16. For decrease_price, the suggested price is:

    current_price - (current_price // 10)

    17. Never exceed the 10% limit.

    18. Use only actual merchant data.

    19. Never invent sales, revenue, stock, prices, product IDs,
    or other business data.

    20. Do not assume customer behavior or price elasticity.

    21. Do not claim that a price change will definitely increase
    sales or revenue.

    Reason rules:

    22. The reason must be based only on the actual merchant data.

    23. Do not invent statistics or business facts.

    24. Do not state an incorrect percentage.

    25. Do not describe the paise difference as a percentage.

    26. Do not say 1% unless the actual recommendation is a 1% change.

    27. Do not calculate or estimate the percentage change in the
    reason.

    28. Simply explain that the price is being increased or
    decreased within the allowed 10% limit.

    29. The reason must not contain a different price from the
    calculated recommendation.

    30. Do not create alternative recommendations.

    The assistant's recommendation and the structured recommendation
    must refer to the same product and same action.

    Return ONLY:

    - action
    - product_id
    - current_price
    - suggested_price
    - reason
"""

        recommendation = structured_llm.invoke(recommendation_prompt)

        product_data = next(
            (
                product
                for product in growth_data
                if product["product_id"] == recommendation.product_id
            ),
            None
        )

        if product_data is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid product recommendation"
            )

        recommendation.current_price = product_data["current_price"]

        if recommendation.action == "increase_price":
            recommendation.suggested_price = (
                recommendation.current_price
                + recommendation.current_price // 10
            )

        elif recommendation.action == "decrease_price":
            recommendation.suggested_price = (
                recommendation.current_price
                - recommendation.current_price // 10
            )


        pending_recommendation = recommendation
        recommendation_saved = False



    chat_history.append({
        "role": "assistant",
        "content": answer
    })

    return {
        "response": answer
    }
@app.get("/insights-page", response_class=HTMLResponse)
def insights_page(request: Request):
    return template.TemplateResponse(
        request=request,
        name="insights.html"
    )


@app.get("/recommendations-page", response_class=HTMLResponse)
def recommendations_page(request: Request):
    return template.TemplateResponse(
        request=request,
        name="recommendations.html"
    )


@app.get("/chatbot", response_class=HTMLResponse)
def chatbot_page(request: Request):
    return template.TemplateResponse(
        request=request,
        name="chatbot.html"
    )


@app.get("/audit-page", response_class=HTMLResponse)
def audit_page(request: Request):
    return template.TemplateResponse(
        request=request,
        name="audit.html"
    )
@app.get("/debug-recommendations")
def debug_recommendations():

    db = sessionlocal()

    try:
        recommendations = db.query(Recommendation).all()

        result = []

        for r in recommendations:
            result.append({
                "id": r.id,
                "product_id": r.product_id,
                "action": r.action,
                "current_price": r.current_price,
                "suggested_price": r.suggested_price,
                "status": r.status
            })

        return result

    finally:
        db.close()
        
@app.put("/test-change-price/{product_id}")
def test_change_price(product_id: int, new_price: int):
    db = sessionlocal()

    try:
        product = db.query(Product).filter(
            Product.id == product_id
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        product.price = new_price

        db.commit()
        db.refresh(product)

        return {
            "message": "Test price updated",
            "product_id": product.id,
            "new_price": product.price
        }

    finally:
        db.close()