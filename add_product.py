import requests

URL = "https://marginmind-5bt5.onrender.com/product"

products = [
    {
        "name": "Power Bank",
        "price": 199900,
        "category": "Chargers",
        "stock": 70
    },
    {
        "name": "Gaming Mouse",
        "price": 179900,
        "category": "Accessories",
        "stock": 45
    },
    {
        "name": "Laptop Stand",
        "price": 149900,
        "category": "Accessories",
        "stock": 55
    }
]

for product in products:
    try:
        response = requests.post(
            URL,
            json=product,
            timeout=90
        )

        if response.status_code in [200, 201]:
            print(f"Added: {product['name']}")
        else:
            print(f"Failed: {product['name']}")
            print(response.text)

    except requests.exceptions.Timeout:
        print(f"Timeout: {product['name']}")