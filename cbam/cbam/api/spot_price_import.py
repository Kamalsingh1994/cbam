# cbam/cbam/cbam/api/spot_price_import.py

import frappe
import requests
from datetime import datetime, timedelta
from frappe.utils import now_datetime
from frappe.utils.password import get_decrypted_password
import json

@frappe.whitelist()
def fetch_daily_spot_prices():
    """
    Daily import of EUA spot prices from Matflixx API
    
    Fills these fields in ETS Carbon Price:
    - price_date (Date)
    - price (Currency)
    - custom_data_source (Select: Automated Import)
    - ets_price_type (Select: Spot Price)
    """
    
    config = frappe.get_single("Spot Price Settings")
    
    if not config.is_active:
        return {"status": "skipped", "message": "Import is disabled"}
    
    try:
        username = config.username
        password = get_decrypted_password("Spot Price Settings", "Spot Price Settings", "password")
        
        # Step 1: Login and get JWT token
        # TODO: Update this URL if your login endpoint is different
        login_url = f"{config.website_url}/api/v1/auth/login"
        
        login_response = requests.post(
            login_url,
            json={
                "email": username,
                "password": password
            },
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout=30
        )
        
        if login_response.status_code not in [200, 201]:
            raise Exception(
                f"Login failed: HTTP {login_response.status_code}\n"
                f"Response: {login_response.text}"
            )
        
        # Extract JWT token from nested response
        login_data = login_response.json()
        
        if login_data.get('isError'):
            raise Exception(f"Login error: {login_data.get('message')}")
        
        # Token is in login_data['data']['token']
        data = login_data.get('data', {})
        jwt_token = data.get('token')
        
        if not jwt_token:
            raise Exception(f"No JWT token found in login response")
        
        frappe.logger().info(f"Login successful for: {data.get('email')}")
        
        # Step 2: Fetch spot prices
        api_url = f"{config.website_url}/api/v1/course/courseHistoryV6"
        
        payload = {
            "data": [{
                "id": "7e831956-3fc7-4bc2-8587-0755e3bbf0a0",
                "symbol": "FEUA/CONT",
                "boerse": "eex",
                "waehrung": "EUR",
                "unit": "",
                "year": ""
            }],
            "percentageTotal": False,
            "span": config.filter_settings or "1y"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-access-token': jwt_token
        }
        
        data_response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=60
        )
        
        if data_response.status_code not in [200, 201]:
            raise Exception(
                f"API call failed: HTTP {data_response.status_code}\n"
                f"Response: {data_response.text[:500]}"
            )
        
        frappe.logger().info(f"API response received: {len(data_response.content)} bytes")
        
        # Step 3: Parse response
        json_data = data_response.json()
        
        if json_data.get('isError'):
            raise Exception(f"API error: {json_data.get('message')}")
        
        prices = json_data.get('data', {}).get('data', [])
        
        if not prices:
            raise Exception("No price data in response")
        
        frappe.logger().info(f"Fetched {len(prices)} records from API")
        
        # Step 4: Import
        result = import_to_ets_carbon_price(prices)
        
        # Step 5: Update config
        config.last_sync_date = now_datetime()
        config.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            **result,
            "timestamp": now_datetime()
        }
        
    except Exception as e:
        handle_error(str(e), config)
        return {"status": "failed", "error": str(e)}


def import_to_ets_carbon_price(prices):
    """
    Import prices to ETS Carbon Price DocType
    
    Field mapping:
    - API 'date' → 'price_date'
    - API 'priceFEUA/CONT-eex-0' → 'price'
    - Static 'Automated Import' → 'custom_data_source'
    - Static 'Spot Price' → 'ets_price_type'
    """
    imported = 0
    skipped = 0
    errors = []
    
    for price_data in prices:
        try:
            # Extract date (remove time)
            date_str = price_data.get('date', '')
            price_date = date_str.split(' ')[0] if date_str else None
            
            # Extract price
            price_value = price_data.get('priceFEUA/CONT-eex-0')
            
            if not price_date or price_value is None:
                errors.append(f"Missing data: date={date_str}, price={price_value}")
                continue
            
            # Check for duplicates
            exists = frappe.db.exists("ETS Carbon Price", {
                "price_date": price_date,
                "ets_price_type": "Spot Price",
                "custom_data_source": "Automated Import"
            })
            
            if exists:
                skipped += 1
                continue
            
            # Create new record
            doc = frappe.get_doc({
                "doctype": "ETS Carbon Price",
                "price_date": price_date,
                "price": float(price_value),
                "ets_price_type": "Spot Price",
                "custom_data_source": "Automated Import",
                "carbon_price_source": None
            })
            
            doc.insert(ignore_permissions=True)
            imported += 1
            
            frappe.logger().debug(f"Imported: {price_date} = {price_value}")
            
        except Exception as e:
            errors.append(f"{price_data.get('date')}: {str(e)}")
            frappe.logger().error(f"Import error: {str(e)}")
            continue
    
    frappe.logger().info(
        f"Import complete: {imported} imported, {skipped} skipped, {len(errors)} errors"
    )
    
    return {
        "imported": imported,
        "skipped": skipped,
        "total": len(prices),
        "errors": errors[:10]
    }


def handle_error(error_msg, config):
    """Log error and send notification"""
    
    diagnostic_info = f"""
    SPOT PRICE IMPORT FAILED
    
    Error: {error_msg}
    
    Configuration:
    - API: {config.website_url}
    - Username: {config.username}
    - Filter: {config.filter_settings}
    - Last Success: {config.last_sync_date or 'Never'}
    - Time: {now_datetime()}
    
    Stack Trace:
    {frappe.get_traceback()}
    """
    
    frappe.log_error(
        title="Spot Price Import Failed",
        message=diagnostic_info
    )
    
    # TODO: Update email recipient below
    try:
        frappe.sendmail(
            recipients=["ulrich.fofe@gallehr,de"],  # ← CHANGE THIS EMAIL!
            subject="Spot Price Import Failed",
            message=f"<p><strong>Error:</strong> {error_msg}</p><p><strong>Time:</strong> {now_datetime()}</p>",
            now=True
        )
    except Exception as email_error:
        frappe.logger().error(f"Failed to send email: {email_error}")
