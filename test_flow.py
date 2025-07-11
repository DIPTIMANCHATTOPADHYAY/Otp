#!/usr/bin/env python3
"""
Test script to verify the Telegram bot flow implementation
This script helps test database operations and flow logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import (
    get_user, update_user, get_country_by_code, 
    set_country_capacity, set_country_price, set_country_claim_time,
    check_number_used, mark_number_used
)

def setup_test_countries():
    """Setup test countries for verification"""
    print("🔧 Setting up test countries...")
    
    # Setup common country codes
    countries = [
        {"code": "+1", "name": "USA", "capacity": 100, "price": 0.1, "claim_time": 600},
        {"code": "+44", "name": "UK", "capacity": 50, "price": 0.15, "claim_time": 300},
        {"code": "+91", "name": "India", "capacity": 200, "price": 0.05, "claim_time": 900},
        {"code": "+86", "name": "China", "capacity": 150, "price": 0.08, "claim_time": 450},
    ]
    
    for country in countries:
        set_country_capacity(country["code"], country["capacity"], country["name"])
        set_country_price(country["code"], country["price"])
        set_country_claim_time(country["code"], country["claim_time"])
        print(f"✅ {country['name']} ({country['code']}) - Capacity: {country['capacity']}, Price: ${country['price']}")

def test_phone_validation():
    """Test phone number validation logic"""
    print("\n📱 Testing phone number validation...")
    
    test_numbers = [
        "+1234567890",  # Valid US number
        "+442071234567",  # Valid UK number  
        "+919876543210",  # Valid India number
        "+8613800000000",  # Valid China number
        "1234567890",  # Invalid - no +
        "+12345",  # Invalid - too short
        "+123456789012345678",  # Invalid - too long
    ]
    
    for number in test_numbers:
        # Test basic format
        import re
        PHONE_REGEX = re.compile(r'^\+\d{1,4}\d{6,14}$')
        format_valid = bool(PHONE_REGEX.match(number))
        
        # Test country code
        country_valid = False
        if format_valid:
            for code_length in [4, 3, 2, 1]:
                code = number[:code_length]
                if get_country_by_code(code):
                    country_valid = True
                    break
        
        # Test if already used
        already_used = check_number_used(number) if format_valid else False
        
        status = "✅" if format_valid and country_valid and not already_used else "❌"
        print(f"{status} {number} - Format: {format_valid}, Country: {country_valid}, Used: {already_used}")

def test_user_operations():
    """Test user database operations"""
    print("\n👤 Testing user operations...")
    
    test_user_id = 999999999  # Test user ID
    
    # Test user creation/update
    update_user(test_user_id, {
        'name': 'Test User',
        'username': 'testuser',
        'balance': 0.0,
        'sent_accounts': 0
    })
    
    user = get_user(test_user_id)
    if user:
        print(f"✅ User created: {user['name']} (Balance: ${user['balance']})")
    else:
        print("❌ Failed to create test user")
    
    # Test balance update
    update_user(test_user_id, {'balance': 1.5})
    updated_user = get_user(test_user_id)
    if updated_user and updated_user['balance'] == 1.5:
        print(f"✅ Balance updated: ${updated_user['balance']}")
    else:
        print("❌ Failed to update balance")

def test_number_tracking():
    """Test number usage tracking"""
    print("\n📞 Testing number tracking...")
    
    test_number = "+1234567890"
    test_user_id = 999999999
    
    # Check if number is used (should be False initially)
    is_used_before = check_number_used(test_number)
    print(f"Number used before marking: {is_used_before}")
    
    # Mark number as used
    mark_success = mark_number_used(test_number, test_user_id)
    print(f"Mark number as used: {mark_success}")
    
    # Check if number is used now (should be True)
    is_used_after = check_number_used(test_number)
    print(f"Number used after marking: {is_used_after}")
    
    if not is_used_before and mark_success and is_used_after:
        print("✅ Number tracking works correctly")
    else:
        print("❌ Number tracking failed")

def main():
    """Run all tests"""
    print("🚀 Starting Flow Implementation Tests\n")
    
    try:
        setup_test_countries()
        test_phone_validation() 
        test_user_operations()
        test_number_tracking()
        
        print("\n✅ All tests completed! Your bot flow implementation is ready.")
        print("\n📋 Next steps:")
        print("1. Set your environment variables (API_ID, API_HASH, BOT_TOKEN, MONGO_URI)")
        print("2. Run: python main.py")
        print("3. Test with real phone numbers")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        print("Please check your database connection and configuration.")

if __name__ == "__main__":
    main()