import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Quivers API Config
API_KEY = "586d0e63-1175-40df-82e4-da32c3fedb6e"
BUSINESS_ID = "M18106_USATN_7DC23AE3"
Email_count=0
# Email Config
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = "punhani.yatin2002@gmail.com"
EMAIL_HOST_PASSWORD = "qqwa dhae btpp tlao"  # App Password
EMAIL_RECEIVER = "punhani.yatin2002@gmail.com"

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

# Start time (UTC)
last_updated_time = datetime.utcnow() - timedelta(minutes=10)  # Start 5 min in past

while True:
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
        continue

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
        print("Non economy orders",email_body)
        Email_count=Email_count+1
        print(Email_count)
    else:
        if order_ref_ids_with_status_40:
            email_body = "\n🔍 Orders with Status 40:\n"
            for order_id in order_ref_ids_with_status_40:
                email_body += f"- {order_id}\n"
            # send_email(email_body)
            # Email_count=Email_count+1
            # print(Email_count)
            print("Order with lineitem status 40",order_ref_ids_with_status_40)
        print("✅ No non-economy shipping orders found.")

    print("⏳ Waiting 5 minutes for next check...\n")
    time.sleep(300)  # Sleep for 5 minutes before next iteration
