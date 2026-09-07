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
    or "price increase" in lower_answer
    or "price decrease" in lower_answer
    or "increase price" in lower_answer
    or "decrease price" in lower_answer
    ):

        growth_data = analyze_growth.invoke({})

        recommendation_prompt = f"""
   You are MarginMind's structured pricing recommendation engine.

Your task is to convert the already-generated MarginMind recommendation
into a structured recommendation using ONLY the merchant data provided below.

==================================================
MERCHANT DATA
==================================================

{growth_data}

==================================================
PREVIOUS MARGINMIND RECOMMENDATION
==================================================

{answer}

==================================================
PRIMARY OBJECTIVE
==================================================

Create the SAME recommendation described in the previous MarginMind
recommendation.

You are NOT deciding which product to recommend.

You are NOT deciding which action to recommend.

You are NOT creating a new recommendation.

You are ONLY converting the existing recommendation into structured data.

The product and action mentioned in the previous recommendation are
authoritative.

==================================================
1. PRODUCT IDENTITY
==================================================

Find the exact product recommended in the previous MarginMind response.

The returned product_id MUST:

- exist in merchant data
- belong to the recommended product
- exactly match the product_id of that product record

Never:

- invent a product_id
- guess a product_id
- modify a product_id
- choose another product
- use an ID from a different product
- combine information from multiple products

If multiple products have the same name, use the product_id from the
previous recommendation and match that exact ID in merchant data.

==================================================
2. ACTION
==================================================

The action MUST exactly match the action recommended by MarginMind.

Allowed values are ONLY:

increase_price
decrease_price

If MarginMind recommended an increase, return:

increase_price

If MarginMind recommended a decrease, return:

decrease_price

Never change the action.

Never create another action.

Never return both actions.

==================================================
3. CURRENT PRICE
==================================================

The current_price MUST come from the EXACT SAME product record as
the selected product_id.

Do not take the price from another product.

Prices in merchant data are stored as integer Indian Rupees paise.

100 paise = ₹1.00.

For example:

769890 = ₹7,698.90

NOT:

76989 = ₹769.89

NOT:

7698900 = ₹76,989.00

CRITICAL:

If merchant data contains:

"product_id": 6,
"product_name": "Smart Watch",
"current_price": 769890

then the structured output MUST contain:

product_id = 6
current_price = 769890

Do NOT divide by 10.

Do NOT multiply by 10.

Do NOT divide by 1000.

Do NOT round.

Do NOT convert current_price to rupees in the structured output.

Return the integer paise value exactly as it appears in merchant data.

==================================================
4. CURRENT PRICE VALIDATION
==================================================

Before returning current_price, verify:

1. The product_id exists.
2. The product_id belongs to the recommended product.
3. The current_price comes from that exact product record.
4. The price is represented in paise.
5. The value has not been divided by 10.
6. The value has not been multiplied by 10.
7. The value has not been divided by 100.
8. The value has not been converted into rupees.
9. The value has not been rounded or modified.

Current_price must be copied from merchant data.

Do not calculate current_price.

==================================================
5. SUGGESTED PRICE
==================================================

The application is responsible for calculating the final suggested price.

The application will use:

For increase_price:

current_price + (current_price // 10)

For decrease_price:

current_price - (current_price // 10)

The maximum allowed change is 10%.

The application-calculated value is authoritative.

Your returned suggested_price must therefore be consistent with the
same current_price and action.

IMPORTANT:

Never use a different base price.

Never use revenue_per_unit as the base price.

Never use revenue as the base price.

Never use another product's price.

Never divide the price by 10.

Never multiply the price by 10.

Never invent an arbitrary price.

If the application later recalculates suggested_price, that
application-calculated value overrides this value.

==================================================
6. PRICE UNIT CONSISTENCY
==================================================

current_price and suggested_price MUST both be integer paise.

Never mix rupees and paise.

For example:

Current price:

769890 paise

Suggested increase:

846879 paise

Correct.

Incorrect:

769890 paise → 8468.79

Incorrect:

76989 paise → 84687 paise

Incorrect:

7698.90 → 8468.79

The structured output must use integers representing paise.

==================================================
7. REVENUE PER UNIT SAFETY
==================================================

Revenue per unit is NOT the current product price.

Do not use:

revenue_per_unit_paise

as:

current_price

For example, if:

current_price = 769890

revenue_per_unit_paise = 84687

the current price remains:

769890

Never replace it with:

84687

==================================================
8. RECOMMENDATION REASON
==================================================

The reason must describe ONLY the observed merchant data.

The reason must support the SAME product and SAME action.

Use information such as:

- units sold
- revenue
- stock
- revenue per unit
- current price

Do not invent statistics.

Do not invent percentages.

Do not make predictions.

Do not claim that the price change will definitely:

- increase revenue
- increase sales
- decrease sales
- improve profit
- increase demand
- maintain demand

Do not mention unsupported customer behavior.

Use neutral wording.

For example:

"The product has 8 units sold and 27 units in stock. Based on the
observed sales and inventory data, an increase in price may be worth
considering."

==================================================
9. REASON MUST MATCH THE RECOMMENDATION
==================================================

If action is:

increase_price

the reason must explain why an increase may be worth considering.

If action is:

decrease_price

the reason must explain why a decrease may be worth considering.

Never describe an increase while returning decrease_price.

Never describe a decrease while returning increase_price.

Never mention a different product.

Never mention a different price.

==================================================
10. NO ALTERNATIVE RECOMMENDATIONS
==================================================

Return exactly ONE recommendation.

Do not:

- suggest another product
- suggest another action
- provide multiple options
- provide alternative prices
- provide a second recommendation
- reconsider the previous recommendation

The previous MarginMind recommendation is the one you must structure.

==================================================
11. FINAL CONSISTENCY CHECK
==================================================

Before returning the structured output, verify all of the following:

[ ] Product exists in merchant data.

[ ] Product ID exactly matches the recommended product.

[ ] Action exactly matches the previous recommendation.

[ ] Current price belongs to the same product ID.

[ ] Current price is copied from merchant data.

[ ] Current price is integer paise.

[ ] Current price was NOT divided by 10.

[ ] Current price was NOT multiplied by 10.

[ ] Revenue per unit was NOT used as current price.

[ ] Suggested price uses the same current price.

[ ] Suggested price follows the maximum 10% rule.

[ ] Suggested price is integer paise.

[ ] Reason refers to the same product.

[ ] Reason refers to the same action.

[ ] No unsupported business claims are made.

==================================================
12. ABSOLUTE PRIORITY
==================================================

When there is a conflict between:

- the previous MarginMind recommendation
- merchant data

the merchant data is authoritative for product_id and current_price.

However, DO NOT select a different product.

If the previous recommendation cannot be matched to a product in
merchant data, return the closest exact product match only if the
product identity is unambiguous. Otherwise, do not invent a product.

The structured recommendation must always remain grounded in actual
merchant data.

==================================================
13. OUTPUT
==================================================

Return ONLY these fields:

action
product_id
current_price
suggested_price
reason

Do not return explanations outside these fields.

Do not return markdown.

Do not return additional fields.

Do not return multiple recommendations.
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