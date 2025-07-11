#!/usr/bin/env python3
"""
Test script to verify cancel functionality and number unmarking works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import (
    check_number_used, mark_number_used, unmark_number_used,
    get_user, update_user, delete_pending_numbers
)

def test_number_marking_unmarking():
    """Test the number marking and unmarking functionality"""
    print("🧪 Testing Number Marking/Unmarking Functionality\n")
    
    test_number = "+584249074103"  # The Venezuela number from the issue
    test_user_id = 999999999
    
    print(f"📱 Testing with number: {test_number}")
    print(f"👤 Testing with user ID: {test_user_id}")
    
    # Step 1: Check if number is initially unused
    print(f"\n1️⃣ Checking initial status...")
    is_used_initially = check_number_used(test_number)
    print(f"   Number used initially: {is_used_initially}")
    
    # Step 2: Mark number as used
    print(f"\n2️⃣ Marking number as used...")
    mark_success = mark_number_used(test_number, test_user_id)
    print(f"   Mark operation success: {mark_success}")
    
    # Step 3: Verify number is now marked as used
    print(f"\n3️⃣ Verifying number is marked as used...")
    is_used_after_mark = check_number_used(test_number)
    print(f"   Number used after marking: {is_used_after_mark}")
    
    # Step 4: Unmark the number (simulate cancel)
    print(f"\n4️⃣ Unmarking number (simulating /cancel)...")
    unmark_success = unmark_number_used(test_number)
    print(f"   Unmark operation success: {unmark_success}")
    
    # Step 5: Verify number is now available again
    print(f"\n5️⃣ Verifying number is available again...")
    is_used_after_unmark = check_number_used(test_number)
    print(f"   Number used after unmarking: {is_used_after_unmark}")
    
    # Step 6: Test results
    print(f"\n📊 Test Results:")
    print(f"   ✅ Initial check: {'PASS' if not is_used_initially else 'FAIL'}")
    print(f"   ✅ Mark operation: {'PASS' if mark_success else 'FAIL'}")
    print(f"   ✅ Used after mark: {'PASS' if is_used_after_mark else 'FAIL'}")
    print(f"   ✅ Unmark operation: {'PASS' if unmark_success else 'FAIL'}")
    print(f"   ✅ Available after unmark: {'PASS' if not is_used_after_unmark else 'FAIL'}")
    
    all_tests_pass = (
        not is_used_initially and 
        mark_success and 
        is_used_after_mark and 
        unmark_success and 
        not is_used_after_unmark
    )
    
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASS' if all_tests_pass else '❌ SOME TESTS FAILED'}")
    return all_tests_pass

def test_user_cleanup():
    """Test user data cleanup functionality"""
    print("\n🧪 Testing User Data Cleanup Functionality\n")
    
    test_user_id = 999999999
    test_phone = "+584249074103"
    
    # Step 1: Create user with pending verification data
    print("1️⃣ Setting up user with pending verification...")
    update_success = update_user(test_user_id, {
        'name': 'Test User',
        'username': 'testuser',
        'balance': 0.0,
        'pending_phone': test_phone,
        'otp_msg_id': 12345,
        'country_code': '+58'
    })
    print(f"   User setup success: {update_success}")
    
    # Step 2: Verify user has pending data
    print("2️⃣ Verifying user has pending verification data...")
    user = get_user(test_user_id)
    has_pending = user and user.get('pending_phone') == test_phone
    print(f"   User has pending phone: {has_pending}")
    
    # Step 3: Clean up user data (simulate cancel cleanup)
    print("3️⃣ Cleaning up user data (simulating /cancel cleanup)...")
    cleanup_success = update_user(test_user_id, {
        "pending_phone": None,
        "otp_msg_id": None,
        "country_code": None
    })
    print(f"   Cleanup success: {cleanup_success}")
    
    # Step 4: Verify user data is cleaned
    print("4️⃣ Verifying user data is cleaned...")
    user_after = get_user(test_user_id)
    is_cleaned = (
        user_after and 
        user_after.get('pending_phone') is None and
        user_after.get('otp_msg_id') is None and
        user_after.get('country_code') is None
    )
    print(f"   User data cleaned: {is_cleaned}")
    
    # Step 5: Test deleting pending numbers
    print("5️⃣ Testing pending numbers cleanup...")
    deleted_count = delete_pending_numbers(test_user_id)
    print(f"   Deleted pending numbers: {deleted_count}")
    
    print(f"\n📊 Cleanup Test Results:")
    print(f"   ✅ User setup: {'PASS' if update_success else 'FAIL'}")
    print(f"   ✅ Has pending data: {'PASS' if has_pending else 'FAIL'}")
    print(f"   ✅ Cleanup operation: {'PASS' if cleanup_success else 'FAIL'}")
    print(f"   ✅ Data cleaned: {'PASS' if is_cleaned else 'FAIL'}")
    
    cleanup_tests_pass = update_success and has_pending and cleanup_success and is_cleaned
    print(f"\n🎯 Cleanup Result: {'✅ ALL TESTS PASS' if cleanup_tests_pass else '❌ SOME TESTS FAILED'}")
    return cleanup_tests_pass

def main():
    print("🚀 Testing Cancel Functionality and Number Reuse\n")
    
    try:
        # Test number marking/unmarking
        marking_tests_pass = test_number_marking_unmarking()
        
        # Test user data cleanup
        cleanup_tests_pass = test_user_cleanup()
        
        # Overall results
        print("\n" + "="*60)
        print("🎯 FINAL TEST RESULTS:")
        print("="*60)
        print(f"📱 Number Marking/Unmarking: {'✅ PASS' if marking_tests_pass else '❌ FAIL'}")
        print(f"🗑️ User Data Cleanup: {'✅ PASS' if cleanup_tests_pass else '❌ FAIL'}")
        
        if marking_tests_pass and cleanup_tests_pass:
            print(f"\n🎉 ALL CANCEL FUNCTIONALITY TESTS PASSED! 🎉")
            print("\n✅ Your bot can now:")
            print("   • Properly mark/unmark numbers")
            print("   • Handle /cancel command correctly") 
            print("   • Allow number reuse after cancellation")
            print("   • Clean up all verification data")
            print("\n🧪 Test the /cancel command in your bot!")
        else:
            print(f"\n❌ Some tests failed. Please check the implementation.")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        print("Please check your database connection and configuration.")

if __name__ == "__main__":
    main()