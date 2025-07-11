#!/usr/bin/env python3
"""
Setup script for Venezuela country code and fix database issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import set_country_capacity, set_country_price, set_country_claim_time, get_country_by_code

def setup_venezuela():
    """Setup Venezuela country code"""
    print("🇻🇪 Setting up Venezuela (+58)...")
    
    # Setup Venezuela
    country_code = "+58"
    capacity = 100
    price = 0.12  # Higher price for Venezuela
    claim_time = 600  # 10 minutes
    
    # Set country configuration
    result1 = set_country_capacity(country_code, capacity, "Venezuela", "🇻🇪")
    result2 = set_country_price(country_code, price)
    result3 = set_country_claim_time(country_code, claim_time)
    
    if result1 and result2 and result3:
        print(f"✅ Venezuela ({country_code}) configured:")
        print(f"   - Capacity: {capacity}")
        print(f"   - Price: ${price} USDT")
        print(f"   - Claim Time: {claim_time} seconds")
        
        # Verify setup
        country = get_country_by_code(country_code)
        if country:
            print(f"✅ Verification successful: {country}")
        else:
            print("❌ Failed to verify Venezuela setup")
            
    else:
        print("❌ Failed to setup Venezuela")

def setup_common_countries():
    """Setup other common country codes"""
    print("\n🌍 Setting up common countries...")
    
    countries = [
        {"+1": {"name": "USA", "capacity": 200, "price": 0.10, "claim_time": 600}},
        {"+44": {"name": "UK", "capacity": 100, "price": 0.15, "claim_time": 300}},
        {"+91": {"name": "India", "capacity": 300, "price": 0.05, "claim_time": 900}},
        {"+86": {"name": "China", "capacity": 250, "price": 0.08, "claim_time": 450}},
        {"+7": {"name": "Russia", "capacity": 150, "price": 0.12, "claim_time": 600}},
        {"+33": {"name": "France", "capacity": 80, "price": 0.18, "claim_time": 400}},
        {"+49": {"name": "Germany", "capacity": 90, "price": 0.20, "claim_time": 350}},
        {"+55": {"name": "Brazil", "capacity": 120, "price": 0.14, "claim_time": 500}},
        {"+52": {"name": "Mexico", "capacity": 100, "price": 0.11, "claim_time": 550}},
        {"+234": {"name": "Nigeria", "capacity": 180, "price": 0.06, "claim_time": 800}},
    ]
    
    for country_dict in countries:
        for code, info in country_dict.items():
            set_country_capacity(code, info["capacity"], info["name"])
            set_country_price(code, info["price"])
            set_country_claim_time(code, info["claim_time"])
            print(f"✅ {info['name']} ({code}) - Capacity: {info['capacity']}, Price: ${info['price']}")

def test_phone_number():
    """Test the Venezuela phone number from the error"""
    print("\n📱 Testing Venezuela phone number...")
    
    test_number = "+584249074103"
    
    # Check format
    import re
    PHONE_REGEX = re.compile(r'^\+\d{1,4}\d{6,14}$')
    format_valid = bool(PHONE_REGEX.match(test_number))
    
    # Check country code
    country_valid = False
    country_code = None
    for code_length in [4, 3, 2, 1]:
        code = test_number[:code_length]
        country = get_country_by_code(code)
        if country:
            country_valid = True
            country_code = code
            break
    
    print(f"Number: {test_number}")
    print(f"Format Valid: {format_valid}")
    print(f"Country Valid: {country_valid}")
    print(f"Country Code: {country_code}")
    
    if country_valid:
        country_info = get_country_by_code(country_code)
        print(f"Country Info: {country_info}")
    
    return format_valid and country_valid

if __name__ == "__main__":
    print("🚀 Setting up countries and fixing database issues...\n")
    
    try:
        setup_venezuela()
        setup_common_countries()
        
        # Test the specific number
        if test_phone_number():
            print("\n✅ Venezuela phone number validation successful!")
        else:
            print("\n❌ Venezuela phone number validation failed!")
            
        print("\n✅ Setup completed successfully!")
        print("You can now use Venezuela numbers like +584249074103")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        print("Please check your database connection.")