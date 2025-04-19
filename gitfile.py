import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

# Quivers API Config
API_KEY = "586d0e63-1175-40df-82e4-da32c3fedb6e"
BUSINESS_ID = "M18106_USATN_7DC23AE3"

# Email Config (use environment variables in GitHub Actions)
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = os.environ.get("EMAIL_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", EMAIL_HOST_USER)

def send_email(body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_HOST_USER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = "🚚 Quivers Orders with Non-Economy Shipping"
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.sendmail(EMAIL_HOST_USER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("📧 Email sent successfully.")
    except Exception as e:
        print("❌ Failed to send email:", e)

def check_orders():
    # Start time (UTC)
    last_updated_time = datetime.utcnow() - timedelta(minutes=15)

    # Step 1: Update LastUpdatedOnUtc param
    last_updated_time += timedelta(minutes=5)
    formatted_time = last_updated_time.isoformat()

    print(f"\n🔁 Checking orders updated after: {formatted_time}")

    search_url = "https://cloudhub.quivers.com/api/v1/private/BusinessOrders/Search"
    params = {
        "refId": BUSINESS_ID,
        "Statuses": "ReadyToShip",
        "orderBy": "orderAsc",
        "currentPage": 1,
        "orderDesc": "True",
        "pageSize": 200,
        "LastUpdatedOnUtc": formatted_time
    }
    headers = {
        "Authorization": f"apikey {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print("❌ Failed to fetch from Quivers Search API:", e)
        return

    order_ref_ids_with_status_40 = []
    mappingdict = {}

    for order in data.get("_embedded", []):
        customer_order_id = order.get("CustomerOrderId")
        quivers_order_id = order.get("CustomerOrderRefId")
        for brand_order in order.get("BrandOrders", []):
            for line_item in brand_order.get("LineItems", []):
                if line_item.get("LineItemStatus", {}).get("Value") == 40:
                    order_ref_ids_with_status_40.append(customer_order_id)
                    mappingdict[customer_order_id] = quivers_order_id
                    break

    # Step 2: Filter non-economy shipping methods
    non_economy_ids = []
    non_economy_ids_dict = {}

    for order_id in order_ref_ids_with_status_40:
        url = f"https://api.quivers.com/v1/CustomerOrders/ById?business={BUSINESS_ID}&orderId={order_id}&includeOrderProductVariants=true"

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                order_data = resp.json()
                shipping_method = order_data.get("result", {}).get("preferredShippingMethodName", "").lower()
                if "economy" not in shipping_method:
                    non_economy_ids.append(order_id)
                    non_economy_ids_dict[order_id] = shipping_method
        except Exception as e:
            print(f"Error for order {order_id}: {e}")
        time.sleep(0.5)

    # Step 3: Send email if any non-economy orders found
    if non_economy_ids:
        email_body = "🚚 *Non-Economy Shipping Orders:*\n\n"
        for order_id in non_economy_ids:
            shipping_method = non_economy_ids_dict.get(order_id)
            quivers_order_id = mappingdict.get(order_id)
            email_body += f"CustomerOrderId: {order_id}, QuiversOrderId: {quivers_order_id}, Method: {shipping_method}\n"
        email_body += "\n🔍 Orders with Status 40:\n"
        for order_id in order_ref_ids_with_status_40:
            email_body += f"- {order_id}\n"
        send_email(email_body)
        print("Non economy orders", email_body)
    else:
        if order_ref_ids_with_status_40:
            email_body = "\n🔍 Orders with Status 40:\n"
            for order_id in order_ref_ids_with_status_40:
                email_body += f"- {order_id}\n"
            print("Order with lineitem status 40", order_ref_ids_with_status_40)
        print("✅ No non-economy shipping orders found.")

if __name__ == "__main__":
    check_orders()
