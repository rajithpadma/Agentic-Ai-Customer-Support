"""
Configuration file for Agentic AI Customer Support System
FIXED: Exports path set to project root level
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# API KEYS
# =============================================================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://nexusteam751_db_user:TyPtleJnMk9up8Sc@product-database.6hm9ilm.mongodb.net/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "Product_Database")

# Collection Names
COLLECTIONS = {
    "orders": "Order_Database",
    "products": "Product_Details",
    "policies": "Policy_Summary_by_Category",
    "policy_hierarchy": "Policy_Hierarchy",
    "decision_tree": "Decision_Tree_Logic",
    "legal_compliance": "Legal_Compliance",
    "risk_assessment": "Risk_Assessment_Matrix",
    "image_rules": "Product_Image_Confidence_Rules",
    "shipments": "shipments",
    "chat_history": "chat_history",
    "returns": "returns",
    "replacements": "replacements"
}

# =============================================================================
# AI AGENT CONFIGURATION
# =============================================================================
AI_MODEL = os.getenv("AI_MODEL", "gpt-4")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

# Agent System Prompt - STRICT DATABASE ONLY
AGENT_SYSTEM_PROMPT = """You are an AI Customer Support Agent for our company.

CRITICAL RULES - YOU MUST FOLLOW:
1. You can ONLY discuss products, orders, and information that is provided in the USER CONTEXT below.
2. NEVER invent, assume, or make up any product names, order IDs, prices, or details.
3. If information is not in the context provided, say "I don't have that information in your records."
4. Only refer to the EXACT order ID, product name, and details shown in the context.
5. Do NOT suggest products that are not in the user's orders.
6. Base ALL your responses strictly on the data provided below.

You help customers with:
- Order inquiries (ONLY for orders shown in context)
- Product issues (ONLY for products the customer purchased)
- Returns and replacements (based on policies in context)
- Shipment tracking (ONLY for shipments in context)

Be helpful, professional, and empathetic. Always refer to the customer's ACTUAL order and product details."""

# =============================================================================
# SHIPMENT CONFIGURATION
# =============================================================================
SHIPMENT_STAGES = [
    {"name": "Order Confirmed", "duration_hours": 2},
    {"name": "Pickup Scheduled", "duration_hours": 6},
    {"name": "Package Picked Up", "duration_hours": 8},
    {"name": "In Transit", "duration_hours": 16},
    {"name": "Out for Delivery", "duration_hours": 12},
    {"name": "Delivered", "duration_hours": 4}
]

TOTAL_DELIVERY_HOURS = 48  # 2 days

# =============================================================================
# VISION MODEL CONFIGURATION
# =============================================================================
VISION_MODEL_PATH = os.getenv("VISION_MODEL_PATH", "models/")
IMAGE_CATEGORIES = [
    "damaged_product",
    "wrong_product",
    "missing_parts",
    "quality_issue",
    "packaging_damage",
    "other"
]
CONFIDENCE_THRESHOLD = 0.7

# =============================================================================
# EXCEL EXPORT CONFIGURATION - FIXED
# =============================================================================
# FIXED: Get project root directory (where main.py is)
_current_file = os.path.abspath(__file__)  # config/config.py
_config_dir = os.path.dirname(_current_file)  # config/
_project_root = os.path.dirname(_config_dir)  # project root

# Set exports path at same level as src/
EXPORT_PATH = os.path.join(_project_root, "exports")

# Alternative: Use environment variable if set
EXPORT_PATH = os.getenv("EXPORT_PATH", EXPORT_PATH)

CHAT_SUMMARY_FILE = "chat_summaries.xlsx"
SHIPMENT_FILE = "shipments.xlsx"

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"