"""
Database Module for Agentic AI Customer Support
Handles all MongoDB operations - this is what the AI Agent queries
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from bson import ObjectId
from datetime import datetime
from typing import Optional, Dict, List, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import MONGODB_URI, DATABASE_NAME, COLLECTIONS


class DatabaseManager:
    """Manages all database operations for the customer support system"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure single database connection"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.client = None
        self.db = None
        self._initialized = True
        
    def connect(self) -> bool:
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(MONGODB_URI)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[DATABASE_NAME]
            print(f"✓ Connected to MongoDB: {DATABASE_NAME}")
            return True
        except ConnectionFailure as e:
            print(f"✗ Failed to connect to MongoDB: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("✓ Disconnected from MongoDB")
    
    def _check_connection(self) -> bool:
        """Check if database is connected"""
        return self.db is not None
    
    # =========================================================================
    # USER OPERATIONS (Extract from Orders)
    # =========================================================================
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Fetch user details by user ID - extracts from orders"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["orders"]]
            # Field names match CSV: User_ID, Customer_Name, Email, Billing_Address
            order = collection.find_one({"User_ID": user_id})
            if order:
                # Extract user info from order using CSV field names
                user = {
                    "_id": str(order.get("_id", "")),
                    "user_id": order.get("User_ID", user_id),
                    "name": order.get("Customer_Name", "Customer"),
                    "email": order.get("Email", ""),
                    "phone": order.get("Phone", ""),
                    "address": order.get("Billing_Address", "")
                }
                return user
            # Return basic user info if no orders found
            return None
        except PyMongoError as e:
            print(f"Error fetching user: {e}")
            return None
    
    def authenticate_user(self, user_id: str) -> Optional[Dict]:
        """Authenticate user - validates user exists"""
        return self.get_user_by_id(user_id)
    
    # =========================================================================
    # ORDER OPERATIONS
    # =========================================================================
    def get_orders_by_user(self, user_id: str) -> List[Dict]:
        """Fetch all orders for a user"""
        if not self._check_connection():
            return []
        try:
            collection = self.db[COLLECTIONS["orders"]]
            # Field name from CSV: User_ID
            orders = list(collection.find({"User_ID": user_id}))
            for order in orders:
                order["_id"] = str(order["_id"])
                # Normalize field names for frontend
                order["order_id"] = order.get("Order_ID", "")
                order["product_id"] = order.get("Product_ID", "")
                order["product_name"] = order.get("Product_Name", "")
                order["status"] = order.get("Status", "Delivered")
                order["date"] = order.get("Date_Ordered", "")
                order["price"] = order.get("Price_Inr", "")
            return orders
        except PyMongoError as e:
            print(f"Error fetching orders: {e}")
            return []
    
    def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        """Fetch specific order by order ID"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["orders"]]
            # Field name from CSV: Order_ID
            order = collection.find_one({"Order_ID": order_id})
            if order:
                order["_id"] = str(order["_id"])
                # Normalize field names
                order["order_id"] = order.get("Order_ID", "")
                order["user_id"] = order.get("User_ID", "")
                order["customer_name"] = order.get("Customer_Name", "")
                order["email"] = order.get("Email", "")
                order["product_id"] = order.get("Product_ID", "")
                order["product_name"] = order.get("Product_Name", "")
                order["order_date"] = order.get("Date_Ordered", "")
                order["price"] = order.get("Price_Inr", "")
                order["payment_method"] = order.get("Payment_Mode", "")
                order["address"] = order.get("Billing_Address", "")
                order["status"] = order.get("Status", "Delivered")
            return order
        except PyMongoError as e:
            print(f"Error fetching order: {e}")
            return None
    
    def get_recent_orders(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Fetch recent orders for a user"""
        if not self._check_connection():
            return []
        try:
            collection = self.db[COLLECTIONS["orders"]]
            # Field name from CSV: User_ID
            orders = list(collection.find({"User_ID": user_id}).limit(limit))
            for order in orders:
                order["_id"] = str(order["_id"])
                # Normalize field names
                order["order_id"] = order.get("Order_ID", "")
                order["product_id"] = order.get("Product_ID", "")
                order["product_name"] = order.get("Product_Name", "")
                order["status"] = order.get("Status", "Delivered")
                order["date"] = order.get("Date_Ordered", "")
            return orders
        except PyMongoError as e:
            print(f"Error fetching recent orders: {e}")
            return []
    
    # =========================================================================
    # PRODUCT OPERATIONS
    # =========================================================================
    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Fetch product details by product ID"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["products"]]
            # Field name from CSV: Product_ID
            product = collection.find_one({"Product_ID": product_id})
            if product:
                product["_id"] = str(product["_id"])
                # Normalize field names
                product["product_id"] = product.get("Product_ID", "")
                product["name"] = product.get("Product_Name", "")
                product["category"] = product.get("Category", "")
                product["price"] = product.get("Price_INR", "")
                product["description"] = product.get("Detailed_Description", "")
                product["risk_level"] = product.get("Risk_Level", "")
                product["return_eligible"] = product.get("Return_Eligible", False)
                product["return_days"] = product.get("Return_Days", 0)
                product["replacement_eligible"] = product.get("Replacement_Eligible", False)
                product["replacement_days"] = product.get("Replacement_Days", 0)
                product["warranty_months"] = product.get("Warranty_Months", 0)
                product["return_conditions"] = product.get("Return_Conditions", "")
                product["refund_policy"] = product.get("Refund_Policy", "")
                product["refund_method"] = product.get("Refund_Method", "")
            return product
        except PyMongoError as e:
            print(f"Error fetching product: {e}")
            return None
    
    def get_products_by_ids(self, product_ids: List[str]) -> List[Dict]:
        """Fetch multiple products by their IDs"""
        if not self._check_connection():
            return []
        try:
            collection = self.db[COLLECTIONS["products"]]
            # Field name from CSV: Product_ID
            products = list(collection.find({"Product_ID": {"$in": product_ids}}))
            for product in products:
                product["_id"] = str(product["_id"])
                product["product_id"] = product.get("Product_ID", "")
                product["name"] = product.get("Product_Name", "")
                product["category"] = product.get("Category", "")
            return products
        except PyMongoError as e:
            print(f"Error fetching products: {e}")
            return []
    
    # =========================================================================
    # POLICY OPERATIONS (For AI Agent Decision Making)
    # =========================================================================
    def get_policy_by_category(self, category: str) -> Optional[Dict]:
        """Fetch policy for a specific category"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["policies"]]
            # Field name from CSV: Category
            policy = collection.find_one({"Category": category})
            if policy:
                policy["_id"] = str(policy["_id"])
                # Normalize field names
                policy["category"] = policy.get("Category", "")
                policy["risk_level"] = policy.get("Risk_Level", "")
                policy["return_window_days"] = policy.get("Return_Days_max", 7)
                policy["replacement_window_days"] = policy.get("Replacement_Days_max", 14)
                policy["warranty_months"] = policy.get("Warranty_Months_max", 0)
            return policy
        except PyMongoError as e:
            print(f"Error fetching policy: {e}")
            return None
    
    def get_all_policies(self) -> List[Dict]:
        """Fetch all policies"""
        if not self._check_connection():
            return []
        try:
            collection = self.db[COLLECTIONS["policies"]]
            policies = list(collection.find())
            for policy in policies:
                policy["_id"] = str(policy["_id"])
                # Normalize field names
                policy["category"] = policy.get("Category", "")
                policy["return_window_days"] = policy.get("Return_Days_max", 7)
                policy["replacement_window_days"] = policy.get("Replacement_Days_max", 14)
            return policies
        except PyMongoError as e:
            print(f"Error fetching policies: {e}")
            return []
    
    def get_return_policy(self, product_id: str = None, category: str = None) -> Optional[Dict]:
        """Fetch return policy for a product or category"""
        if not self._check_connection():
            return None
        try:
            # If product_id provided, get its category first
            if product_id:
                product = self.get_product_by_id(product_id)
                if product:
                    category = product.get("category", product.get("product_category"))
            
            if category:
                policy = self.get_policy_by_category(category)
                if policy:
                    # Normalize fields
                    policy["return_window_days"] = policy.get("return_window_days", 
                                                              policy.get("return_days", 30))
                    return policy
            
            # Return default policy
            return {
                "return_window_days": 30,
                "conditions": ["Product must be unused", "Original packaging required"],
                "refund_method": "Original payment method",
                "is_default": True
            }
        except PyMongoError as e:
            print(f"Error fetching return policy: {e}")
            return None
    
    def get_replacement_policy(self, product_id: str = None) -> Optional[Dict]:
        """Fetch replacement policy"""
        if not self._check_connection():
            return None
        try:
            category = None
            if product_id:
                product = self.get_product_by_id(product_id)
                if product:
                    category = product.get("category", product.get("product_category"))
            
            if category:
                policy = self.get_policy_by_category(category)
                if policy:
                    policy["replacement_window_days"] = policy.get("replacement_window_days",
                                                                    policy.get("replacement_days", 7))
                    return policy
            
            return {
                "replacement_window_days": 7,
                "conditions": ["Defective product", "Wrong product delivered"],
                "is_default": True
            }
        except PyMongoError as e:
            print(f"Error fetching replacement policy: {e}")
            return None
    
    def get_decision_rules(self, issue_type: str = None) -> List[Dict]:
        """Fetch decision tree rules for agent"""
        if not self._check_connection():
            return []
        try:
            collection = self.db[COLLECTIONS["decision_tree"]]
            query = {"issue_type": issue_type} if issue_type else {}
            rules = list(collection.find(query))
            for rule in rules:
                rule["_id"] = str(rule["_id"])
            return rules if rules else [{"rule": "Follow standard support guidelines"}]
        except PyMongoError as e:
            print(f"Error fetching decision rules: {e}")
            return []
    
    # =========================================================================
    # SHIPMENT OPERATIONS
    # =========================================================================
    def create_shipment(self, shipment_data: Dict) -> Optional[str]:
        """Create a new shipment record"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["shipments"]]
            shipment_data["created_at"] = datetime.utcnow()
            shipment_data["updated_at"] = datetime.utcnow()
            result = collection.insert_one(shipment_data)
            return str(result.inserted_id)
        except PyMongoError as e:
            print(f"Error creating shipment: {e}")
            return None
    
    def get_shipment_by_id(self, shipment_id: str) -> Optional[Dict]:
        """Fetch shipment by ID"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["shipments"]]
            shipment = collection.find_one({"shipment_id": shipment_id})
            if shipment:
                shipment["_id"] = str(shipment["_id"])
            return shipment
        except PyMongoError as e:
            print(f"Error fetching shipment: {e}")
            return None
    
    def get_shipments_by_user(self, user_id: str) -> List[Dict]:
        """Fetch all shipments for a user"""
        if not self._check_connection():
            return []
        try:
            collection = self.db[COLLECTIONS["shipments"]]
            shipments = list(collection.find({"user_id": user_id}))
            for shipment in shipments:
                shipment["_id"] = str(shipment["_id"])
            return shipments
        except PyMongoError as e:
            print(f"Error fetching shipments: {e}")
            return []
    
    def update_shipment_status(self, shipment_id: str, status: str, stage_data: Dict = None) -> bool:
        """Update shipment status"""
        if not self._check_connection():
            return False
        try:
            collection = self.db[COLLECTIONS["shipments"]]
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            if stage_data:
                update_data["current_stage"] = stage_data
            
            result = collection.update_one(
                {"shipment_id": shipment_id},
                {"$set": update_data, "$push": {"timeline": stage_data} if stage_data else {}}
            )
            return result.modified_count > 0
        except PyMongoError as e:
            print(f"Error updating shipment: {e}")
            return False
    
    def get_all_shipments(self) -> List[Dict]:
        """Fetch all shipments (for admin view)"""
        if not self._check_connection():
            return []
        try:
            collection = self.db[COLLECTIONS["shipments"]]
            shipments = list(collection.find().sort("created_at", -1))
            for shipment in shipments:
                shipment["_id"] = str(shipment["_id"])
            return shipments
        except PyMongoError as e:
            print(f"Error fetching all shipments: {e}")
            return []
    
    # =========================================================================
    # RETURN/REPLACEMENT OPERATIONS
    # =========================================================================
    def create_return_request(self, return_data: Dict) -> Optional[str]:
        """Create a return request"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["returns"]]
            return_data["created_at"] = datetime.utcnow()
            return_data["status"] = "pending"
            result = collection.insert_one(return_data)
            return str(result.inserted_id)
        except PyMongoError as e:
            print(f"Error creating return request: {e}")
            return None
    
    def create_replacement_request(self, replacement_data: Dict) -> Optional[str]:
        """Create a replacement request"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["replacements"]]
            replacement_data["created_at"] = datetime.utcnow()
            replacement_data["status"] = "pending"
            result = collection.insert_one(replacement_data)
            return str(result.inserted_id)
        except PyMongoError as e:
            print(f"Error creating replacement request: {e}")
            return None
    
    # =========================================================================
    # CHAT HISTORY OPERATIONS
    # =========================================================================
    def save_chat_message(self, chat_data: Dict) -> Optional[str]:
        """Save a chat message"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["chat_history"]]
            chat_data["timestamp"] = datetime.utcnow()
            result = collection.insert_one(chat_data)
            return str(result.inserted_id)
        except PyMongoError as e:
            print(f"Error saving chat: {e}")
            return None
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Fetch chat history for a session"""
        if not self._check_connection():
            return []
        try:
            collection = self.db[COLLECTIONS["chat_history"]]
            chats = list(collection.find({"session_id": session_id})
                        .sort("timestamp", 1)
                        .limit(limit))
            for chat in chats:
                chat["_id"] = str(chat["_id"])
            return chats
        except PyMongoError as e:
            print(f"Error fetching chat history: {e}")
            return []
    
    def save_chat_summary(self, summary_data: Dict) -> Optional[str]:
        """Save chat summary"""
        if not self._check_connection():
            return None
        try:
            collection = self.db[COLLECTIONS["chat_history"]]
            summary_data["type"] = "summary"
            summary_data["timestamp"] = datetime.utcnow()
            result = collection.insert_one(summary_data)
            return str(result.inserted_id)
        except PyMongoError as e:
            print(f"Error saving summary: {e}")
            return None
    
    def get_all_chat_summaries(self) -> List[Dict]:
        """Fetch all chat summaries (for export)"""
        if not self._check_connection():
            return []
        try:
            collection = self.db[COLLECTIONS["chat_history"]]
            summaries = list(collection.find({"type": "summary"}).sort("timestamp", -1))
            for summary in summaries:
                summary["_id"] = str(summary["_id"])
            return summaries
        except PyMongoError as e:
            print(f"Error fetching summaries: {e}")
            return []


# Create singleton instance
db_manager = DatabaseManager()
