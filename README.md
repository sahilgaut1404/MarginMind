# MarginMind

## AI Powered Merchant Revenue Growth Assistant

MarginMind is an AI powered merchant assistant that helps online merchants understand their business data and decide what to do next.

**AI recommends, merchant decides.**

## Problem

Merchants can see products, orders, revenue and inventory, but the difficult question is:

> What should I actually do next to grow my revenue?

MarginMind focuses on turning business data into clear next steps.

## Solution

MarginMind can:

- Analyze product performance
- Analyze sales and revenue
- Check inventory and stock
- Answer business questions
- Identify pricing opportunities
- Prepare pricing recommendations
- Let merchants approve or reject recommendations
- Record approved actions in audit logs
- Process payments using Razorpay Test Mode
- Update orders and inventory after successful payments

## Key Features

### AI Merchant Assistant

Merchants can ask:

- How is my business performing?
- Which product sells the most?
- Which product should I change the price for?
- Which product has excess stock?
- What can I do to increase sales?
- Show me my product performance.

### Pricing Recommendations

MarginMind can identify products that may be candidates for pricing adjustments.

Example:

```text
Product: USB C Charger
Current Price: ₹3,000
Recommended Action: Decrease Price
Suggested Price: ₹2,700
```

The recommendation is limited to a maximum 10% price change. The price is not changed automatically.

### Merchant Approval Workflow

```text
Business Data
     ↓
AI Analysis
     ↓
Recommendation
     ↓
Merchant Review
     ↓
Approve / Reject
     ↓
Action
     ↓
Audit Log
```

### Razorpay Payments

MarginMind uses Razorpay Test Mode to demonstrate payments.

```text
Payment
   ↓
Payment Verification
   ↓
Order Created
   ↓
Stock Updated
   ↓
Business Data Updated
```

### Audit Logs

Important merchant actions are recorded in an audit log.

## Agentic Workflow

```text
Merchant
   ↓
AI Assistant
   ↓
Business Tools
   ↓
Merchant Data
   ↓
Mistral Reasoning
   ↓
Recommendation
   ↓
Merchant Approval
   ↓
Approved Action
   ↓
Audit Log
```

## Business Data Tools

MarginMind currently uses:

```text
get_products()
get_sales_summary()
get_product_sales()
analyze_growth()
```

These tools provide product, price, category, stock, order, sales and revenue information.

## Technology Stack

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Mistral AI
- LangChain
- HTML
- CSS
- JavaScript
- Razorpay Test Mode
- Render

## Project Structure

```text
MarginMind/
│
├── ai/
│   ├── agent.py
│   └── tools.py
├── template/
│   ├── dashboard.html
│   ├── insights.html
│   ├── recommendations.html
│   ├── chat.html
│   └── audit.html
├── static/
│   ├── style.css
│   └── script.js
├── database.py
├── main.py
├── model.py
├── requirements.txt
└── README.md
```

## Main Pages

- **Dashboard** — Products and purchasing
- **Insights** — Business and product performance
- **Recommendations** — Review and approve or reject pricing recommendations
- **AI Assistant** — Ask questions about the business
- **Audit Logs** — View important merchant actions

## Future Scope

### Product Bundle Suggestions

Identify complementary products using sales, stock and product data and suggest bundles that merchants can review and approve.

Example:

```text
Wireless Keyboard
        +
Laptop Stand
        ↓
Work From Home Bundle
```

### Marketing Recommendations

Suggest promotions and offers for products that need more attention.

### Sales Forecasting

Use historical sales data to help merchants plan inventory and business decisions.

### Customer Insights

Analyze purchasing patterns to provide better product insights.

### More Merchant Actions

Expand MarginMind from recommendations to more merchant approved business actions.

## Why MarginMind?

Most business dashboards answer:

> What happened?

MarginMind focuses on:

> What should I do next?

It connects business data, AI analysis, merchant approval and business actions into one workflow.

## Demo

Live application:

https://marginmind-5bt5.onrender.com

Main pages:

```text
/dashboard
/insights-page
/recommendations-page
/chatbot
/audit-page
```

Razorpay is configured in Test Mode for demonstration purposes.

## Getting Started

### Clone the repository

```bash
git clone https://github.com/sahilgaut1404/MarginMind.git
cd MarginMind
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```env
DATABASE_URL=your_database_url
MISTRAL_API_KEY=your_mistral_api_key
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
```

Do not commit your `.env` file or API keys to GitHub.

### Run the application

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

## Project Goal

MarginMind aims to turn merchant business data into clear decisions while keeping the merchant in control.

> **From business data to better decisions.**
