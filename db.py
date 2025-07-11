from pymongo import MongoClient, ReturnDocument
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from config import MONGO_URI
from bson.objectid import ObjectId
import hashlib
from typing import Optional, Dict, List, Union

# Initialize MongoDB connections with enhanced settings
sync_client = MongoClient(
    MONGO_URI,
    maxPoolSize=200,
    minPoolSize=50,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
    serverSelectionTimeoutMS=30000,
    waitQueueTimeoutMS=30000,
    retryWrites=True,
    retryReads=True
)

async_client = AsyncIOMotorClient(
    MONGO_URI,
    maxPoolSize=200,
    minPoolSize=50,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
    serverSelectionTimeoutMS=30000,
    waitQueueTimeoutMS=30000
)

db = sync_client.get_database('telegram_id_sell')
async_db = async_client['telegram_id_sell']

# ====================== USER MANAGEMENT ======================

def get_user(user_id: int) -> Optional[Dict]:
    """Get user by their Telegram user_id with proper error handling"""
    try:
        return db.users.find_one({"user_id": user_id})
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        return None

async def async_get_user(user_id: int) -> Optional[Dict]:
    """Async version of get_user"""
    try:
        return await async_db.users.find_one({"user_id": user_id})
    except Exception as e:
        print(f"Async error in get_user: {str(e)}")
        return None

def update_user(user_id: int, data: Dict) -> bool:
    """
    Atomic update or create user with automatic registration timestamp
    Returns True if successful, False otherwise
    """
    try:
        update_data = {"$set": data}
        
        if not db.users.find_one({"user_id": user_id}):
            update_data["$setOnInsert"] = {
                'registered_at': datetime.utcnow(),
                'balance': 0.0,
                'sent_accounts': 0,
                'pending_phone': None,
                'otp_msg_id': None
            }
        
        result = db.users.update_one(
            {"user_id": user_id},
            update_data,
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        print(f"Error in update_user: {str(e)}")
        return False

async def async_update_user(user_id: int, data: Dict) -> bool:
    """Async version of update_user"""
    try:
        update_data = {"$set": data}
        
        if not await async_db.users.find_one({"user_id": user_id}):
            update_data["$setOnInsert"] = {
                'registered_at': datetime.utcnow(),
                'balance': 0.0,
                'sent_accounts': 0,
                'pending_phone': None,
                'otp_msg_id': None
            }
        
        result = await async_db.users.update_one(
            {"user_id": user_id},
            update_data,
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        print(f"Async error in update_user: {str(e)}")
        return False

def delete_user(user_id: int) -> bool:
    """Delete user by their Telegram user_id"""
    try:
        result = db.users.delete_one({"user_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error in delete_user: {str(e)}")
        return False

# ==================== WITHDRAWAL MANAGEMENT ====================

def log_withdrawal(user_id: int, amount: float, card_name: Optional[str] = None, status: str = "pending") -> Optional[str]:
    """Log a withdrawal request and return withdrawal ID"""
    try:
        withdrawal = {
            "user_id": user_id,
            "amount": amount,
            "card_name": card_name,
            "status": status,
            "timestamp": datetime.utcnow()
        }
        result = db.withdrawals.insert_one(withdrawal)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error in log_withdrawal: {str(e)}")
        return None

def get_withdrawals(user_id: int) -> List[Dict]:
    """Get all withdrawals for a user sorted by newest first"""
    try:
        return list(db.withdrawals.find({"user_id": user_id}).sort("timestamp", -1))
    except Exception as e:
        print(f"Error in get_withdrawals: {str(e)}")
        return []

def get_pending_withdrawal(user_id: int) -> Optional[Dict]:
    """Get user's pending withdrawal if exists"""
    try:
        return db.withdrawals.find_one({"user_id": user_id, "status": "pending"})
    except Exception as e:
        print(f"Error in get_pending_withdrawal: {str(e)}")
        return None

def approve_withdrawal(user_id: int) -> int:
    """Approve all pending withdrawals for a user"""
    try:
        result = db.withdrawals.update_many(
            {"user_id": user_id, "status": "pending"},
            {"$set": {"status": "approved"}}
        )
        return result.modified_count
    except Exception as e:
        print(f"Error in approve_withdrawal: {str(e)}")
        return 0

def reject_withdrawals_by_user(user_id: int) -> tuple:
    """Reject all pending withdrawals for a user and return (count, records)"""
    try:
        with sync_client.start_session() as session:
            with session.start_transaction():
                pending = list(db.withdrawals.find(
                    {"user_id": user_id, "status": "pending"},
                    session=session
                ))
                if pending:
                    db.withdrawals.update_many(
                        {"user_id": user_id, "status": "pending"},
                        {"$set": {"status": "rejected"}},
                        session=session
                    )
                return len(pending), pending
    except Exception as e:
        print(f"Error in reject_withdrawals_by_user: {str(e)}")
        return 0, []

def get_pending_withdrawals_by_card(card_name: str) -> List[Dict]:
    """Get all pending withdrawals for a specific card"""
    try:
        return list(db.withdrawals.find({"card_name": card_name, "status": "pending"}))
    except Exception as e:
        print(f"Error in get_pending_withdrawals_by_card: {str(e)}")
        return []

def approve_withdrawals_by_card(card_name: str) -> int:
    """Approve all pending withdrawals for a specific card"""
    try:
        result = db.withdrawals.update_many(
            {"card_name": card_name, "status": "pending"},
            {"$set": {"status": "approved"}}
        )
        return result.modified_count
    except Exception as e:
        print(f"Error in approve_withdrawals_by_card: {str(e)}")
        return 0

def reject_withdrawals_by_card(card_name: str) -> tuple:
    """Reject all pending withdrawals for a leader card"""
    try:
        with sync_client.start_session() as session:
            with session.start_transaction():
                pending = list(db.withdrawals.find(
                    {"card_name": card_name, "status": "pending"},
                    session=session
                ))
                if pending:
                    db.withdrawals.update_many(
                        {"card_name": card_name, "status": "pending"},
                        {"$set": {"status": "rejected"}},
                        session=session
                    )
                return len(pending), pending
    except Exception as e:
        print(f"Error in reject_withdrawals_by_card: {str(e)}")
        return 0, []

def get_card_withdrawal_stats(card_name: str) -> Dict:
    """Get statistics for withdrawals by card"""
    try:
        total_pending = db.withdrawals.count_documents({"card_name": card_name, "status": "pending"})
        total_approved = db.withdrawals.count_documents({"card_name": card_name, "status": "approved"})

        approved_pipeline = [
            {"$match": {"card_name": card_name, "status": "approved"}},
            {"$group": {"_id": None, "total_balance": {"$sum": "$amount"}}}
        ]
        approved_result = list(db.withdrawals.aggregate(approved_pipeline))
        total_approved_balance = approved_result[0]["total_balance"] if approved_result else 0.0

        pending_pipeline = [
            {"$match": {"card_name": card_name, "status": "pending"}},
            {"$group": {"_id": None, "total_balance": {"$sum": "$amount"}}}
        ]
        pending_result = list(db.withdrawals.aggregate(pending_pipeline))
        total_pending_balance = pending_result[0]["total_balance"] if pending_result else 0.0

        return {
            "pending": total_pending,
            "approved": total_approved,
            "total_pending_balance": total_pending_balance,
            "total_approved_balance": total_approved_balance
        }
    except Exception as e:
        print(f"Error in get_card_withdrawal_stats: {str(e)}")
        return {
            "pending": 0,
            "approved": 0,
            "total_pending_balance": 0.0,
            "total_approved_balance": 0.0
        }

def delete_withdrawals(user_id: int) -> int:
    """Delete all withdrawals for a user"""
    try:
        result = db.withdrawals.delete_many({"user_id": user_id})
        return result.deleted_count
    except Exception as e:
        print(f"Error in delete_withdrawals: {str(e)}")
        return 0

# ================== PHONE NUMBER MANAGEMENT ==================

def add_pending_number(user_id, phone_number, price, claim_time):
    """Conflict-resistant pending number creation"""
    try:
        existing = db.pending_numbers.find_one({
            "phone_number": phone_number,
            "status": "pending"
        })
        
        if existing:
            if existing["user_id"] == user_id:
                db.pending_numbers.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "price": price,
                        "claim_time": claim_time,
                        "last_updated": datetime.utcnow()
                    }}
                )
                return str(existing["_id"])
            return None

        pending = {
            "user_id": user_id,
            "phone_number": phone_number,
            "price": price,
            "claim_time": claim_time,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow()
        }
        result = db.pending_numbers.insert_one(pending)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error in add_pending_number: {str(e)}")
        return None

async def async_add_pending_number(user_id, phone_number, price, claim_time):
    """Async version of add_pending_number"""
    try:
        existing = await async_db.pending_numbers.find_one({
            "phone_number": phone_number,
            "status": "pending"
        })
        
        if existing:
            if existing["user_id"] == user_id:
                await async_db.pending_numbers.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "price": price,
                        "claim_time": claim_time,
                        "last_updated": datetime.utcnow()
                    }}
                )
                return str(existing["_id"])
            return None

        pending = {
            "user_id": user_id,
            "phone_number": phone_number,
            "price": price,
            "claim_time": claim_time,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow()
        }
        result = await async_db.pending_numbers.insert_one(pending)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Async error in add_pending_number: {str(e)}")
        return None

def update_pending_number_status(pending_id, status):
    """Atomic status update with conflict checking"""
    try:
        result = db.pending_numbers.update_one(
            {
                "_id": ObjectId(pending_id),
                "status": "pending"
            },
            {
                "$set": {
                    "status": status,
                    "last_updated": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error in update_pending_number_status: {str(e)}")
        return False

async def async_update_pending_number_status(pending_id, status):
    """Async version of update_pending_number_status"""
    try:
        result = await async_db.pending_numbers.update_one(
            {
                "_id": ObjectId(pending_id),
                "status": "pending"
            },
            {
                "$set": {
                    "status": status,
                    "last_updated": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Async error in update_pending_number_status: {str(e)}")
        return False

def delete_pending_numbers(user_id: int) -> int:
    """Delete all pending numbers for a user"""
    try:
        result = db.pending_numbers.delete_many({"user_id": user_id})
        return result.deleted_count
    except Exception as e:
        print(f"Error in delete_pending_numbers: {str(e)}")
        return 0

def check_number_used(phone_number: str) -> bool:
    """Check if phone number was already used with hashing"""
    try:
        number_hash = hashlib.sha256(phone_number.encode()).hexdigest()
        return db.used_numbers.find_one({"number_hash": number_hash}) is not None
    except Exception as e:
        print(f"Error in check_number_used: {str(e)}")
        return True

async def async_check_number_used(phone_number: str) -> bool:
    """Async version of check_number_used"""
    try:
        number_hash = hashlib.sha256(phone_number.encode()).hexdigest()
        return await async_db.used_numbers.find_one({"number_hash": number_hash}) is not None
    except Exception as e:
        print(f"Async error in check_number_used: {str(e)}")
        return True

def mark_number_used(phone_number: str, user_id: int) -> bool:
    """Mark a phone number as used with hashing"""
    try:
        number_hash = hashlib.sha256(phone_number.encode()).hexdigest()
        db.used_numbers.insert_one({
            "number_hash": number_hash,
            "user_id": user_id,
            "timestamp": datetime.utcnow()
        })
        return True
    except Exception as e:
        print(f"Error in mark_number_used: {str(e)}")
        return False

def unmark_number_used(phone_number: str) -> bool:
    """Remove a phone number from used numbers (for cancellation)"""
    try:
        number_hash = hashlib.sha256(phone_number.encode()).hexdigest()
        result = db.used_numbers.delete_one({"number_hash": number_hash})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error in unmark_number_used: {str(e)}")
        return False

async def async_mark_number_used(phone_number: str, user_id: int) -> bool:
    """Async version of mark_number_used"""
    try:
        number_hash = hashlib.sha256(phone_number.encode()).hexdigest()
        await async_db.used_numbers.insert_one({
            "number_hash": number_hash,
            "user_id": user_id,
            "timestamp": datetime.utcnow()
        })
        return True
    except Exception as e:
        print(f"Async error in mark_number_used: {str(e)}")
        return False

# ================= COUNTRY/CAPACITY MANAGEMENT =================

def set_country_capacity(country_code: str, capacity: int, name: Optional[str] = None, flag: Optional[str] = None) -> bool:
    """Set capacity for a country"""
    try:
        update = {"capacity": capacity}
        if name: update["name"] = name
        if flag: update["flag"] = flag
        
        result = db.countries.update_one(
            {"country_code": country_code},
            {"$set": update},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        print(f"Error in set_country_capacity: {str(e)}")
        return False

def set_country_price(country_code: str, price: float) -> bool:
    """Set price for a country's numbers"""
    try:
        result = db.countries.update_one(
            {"country_code": country_code},
            {"$set": {"price": price}},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        print(f"Error in set_country_price: {str(e)}")
        return False

def set_country_claim_time(country_code: str, claim_time: int) -> bool:
    """Set claim time for a country's numbers"""
    try:
        result = db.countries.update_one(
            {"country_code": country_code},
            {"$set": {"claim_time": claim_time}},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        print(f"Error in set_country_claim_time: {str(e)}")
        return False

def get_country_capacities() -> List[Dict]:
    """Get all countries with their capacities"""
    try:
        return list(db.countries.find({}))
    except Exception as e:
        print(f"Error in get_country_capacities: {str(e)}")
        return []

def get_country_by_code(country_code: str) -> Optional[Dict]:
    """Get country details by country code"""
    try:
        return db.countries.find_one({"country_code": country_code})
    except Exception as e:
        print(f"Error in get_country_by_code: {str(e)}")
        return None

async def async_get_country_by_code(country_code: str) -> Optional[Dict]:
    """Async version of get_country_by_code"""
    try:
        return await async_db.countries.find_one({"country_code": country_code})
    except Exception as e:
        print(f"Async error in get_country_by_code: {str(e)}")
        return None

def remove_country_by_code(country_code: str) -> bool:
    """Remove a country from the database"""
    try:
        result = db.countries.delete_one({"country_code": country_code})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error in remove_country_by_code: {str(e)}")
        return False

# ==================== LEADER CARD MANAGEMENT ====================

def add_leader_card(card_name: str) -> bool:
    """Add a new leader card"""
    try:
        result = db.cards.update_one(
            {"card_name": card_name},
            {"$set": {"card_name": card_name}},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        print(f"Error in add_leader_card: {str(e)}")
        return False

def check_leader_card(card_name: str) -> Optional[Dict]:
    """Check if a leader card exists"""
    try:
        return db.cards.find_one({"card_name": card_name})
    except Exception as e:
        print(f"Error in check_leader_card: {str(e)}")
        return None

def delete_leader_card(card_name: str) -> bool:
    """Delete a leader card"""
    try:
        result = db.cards.delete_one({"card_name": card_name})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error in delete_leader_card: {str(e)}")
        return False

# ====================== CLEANUP FUNCTIONS ======================

def clean_user_data(user_id: int) -> bool:
    """Completely remove all user data from the system"""
    try:
        with sync_client.start_session() as session:
            with session.start_transaction():
                delete_withdrawals(user_id)
                delete_pending_numbers(user_id)
                delete_user(user_id)
                return True
    except Exception as e:
        print(f"Error in clean_user_data: {str(e)}")
        return False

# ====================== NEW OPTIMIZED FUNCTIONS ======================

def bulk_mark_numbers_used(phone_numbers: List[str], user_id: int) -> int:
    """Bulk mark multiple numbers as used"""
    try:
        documents = [{
            "number_hash": hashlib.sha256(num.encode()).hexdigest(),
            "user_id": user_id,
            "timestamp": datetime.utcnow()
        } for num in phone_numbers]
        
        result = db.used_numbers.insert_many(documents)
        return len(result.inserted_ids)
    except Exception as e:
        print(f"Error in bulk_mark_numbers_used: {str(e)}")
        return 0

async def async_bulk_mark_numbers_used(phone_numbers: List[str], user_id: int) -> int:
    """Async version of bulk_mark_numbers_used"""
    try:
        documents = [{
            "number_hash": hashlib.sha256(num.encode()).hexdigest(),
            "user_id": user_id,
            "timestamp": datetime.utcnow()
        } for num in phone_numbers]
        
        result = await async_db.used_numbers.insert_many(documents)
        return len(result.inserted_ids)
    except Exception as e:
        print(f"Async error in bulk_mark_numbers_used: {str(e)}")
        return 0

def get_user_numbers(user_id: int, limit: int = 100) -> List[Dict]:
    """Get all numbers used by a user"""
    try:
        return list(db.used_numbers.find(
            {"user_id": user_id},
            {"_id": 0, "number_hash": 1, "timestamp": 1}
        ).sort("timestamp", -1).limit(limit))
    except Exception as e:
        print(f"Error in get_user_numbers: {str(e)}")
        return []

def get_pending_numbers(limit: int = 100) -> List[Dict]:
    """Get all pending numbers with basic info"""
    try:
        return list(db.pending_numbers.find(
            {"status": "pending"},
            {"_id": 1, "user_id": 1, "phone_number": 1, "created_at": 1}
        ).sort("created_at", -1).limit(limit))
    except Exception as e:
        print(f"Error in get_pending_numbers: {str(e)}")
        return []

def get_user_balance(user_id: int) -> float:
    """Get user balance efficiently"""
    try:
        user = db.users.find_one(
            {"user_id": user_id},
            {"_id": 0, "balance": 1}
        )
        return user.get("balance", 0.0) if user else 0.0
    except Exception as e:
        print(f"Error in get_user_balance: {str(e)}")
        return 0.0

# ====================== INDEX MANAGEMENT ======================

def initialize_indexes():
    """Create all recommended indexes for optimal performance"""
    try:
        # User indexes
        db.users.create_index("user_id", unique=True)
        db.users.create_index("balance")
        db.users.create_index("registered_at")
        
        # Withdrawal indexes
        db.withdrawals.create_index("user_id")
        db.withdrawals.create_index([("status", 1), ("timestamp", -1)])
        db.withdrawals.create_index("card_name")
        db.withdrawals.create_index("amount")
        
        # Pending numbers indexes
        db.pending_numbers.create_index("user_id")
        db.pending_numbers.create_index("status")
        db.pending_numbers.create_index("created_at")
        db.pending_numbers.create_index("phone_number", unique=True)
        
        # Used numbers indexes
        db.used_numbers.create_index("number_hash", unique=True)
        db.used_numbers.create_index("user_id")
        db.used_numbers.create_index("timestamp")
        
        # Country indexes
        db.countries.create_index("country_code", unique=True)
        db.countries.create_index("capacity")
        db.countries.create_index("price")
        
        # Card indexes
        db.cards.create_index("card_name", unique=True)
        
        print("✅ All database indexes created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating indexes: {str(e)}")
        return False

# Create indexes when this module is imported
initialize_indexes()