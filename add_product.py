import requests

URL = "https://marginmind-5bt5.onrender.com/product"

products = [
    {
        "name": "Noise Cancelling Headphones",
        "price": 1099900,
        "category": "Audio",
        "stock": 25
    },
    {
        "name": "Wireless Earbuds",
        "price": 249900,
        "category": "Audio",
        "stock": 50
    },
    {
        "name": "Phone Case",
        "price": 99900,
        "category": "Accessories",
        "stock": 100
    },
    {
        "name": "Wireless Keyboard",
        "price": 249900,
        "category": "Accessories",
        "stock": 40
    },
    {
        "name": "USB C Charger",
        "price": 159900,
        "category": "Chargers",
        "stock": 60
    },
    {
        "name": "Bluetooth Speaker",
        "price": 329900,
        "category": "Audio",
        "stock": 30
    },
    {
        "name": "Smart Watch",
        "price": 499900,
        "category": "Wearables",
        "stock": 35
    },
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
            data = response.json()

            print(
                f"Added: {data.get('name', product['name'])} "
                f"| Product ID: {data.get('id', 'auto-generated')}"
            )
        else:
            print(f"Failed: {product['name']}")
            print(response.text)

    except requests.exceptions.Timeout:
        print(f"Timeout: {product['name']}")

    except requests.exceptions.RequestException as e:
        print(f"Error adding {product['name']}: {e}")