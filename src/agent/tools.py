"""
Agent Tools for Agentic AI Customer Support
These tools allow the AI Agent to dynamically query MongoDB
instead of loading all data into the prompt
"""
import json
from typing import Dict, List, Optional, Any
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.database.database import db_manager


# =============================================================================
# TOOL DEFINITIONS (OpenAI Function Calling Format)
# =============================================================================

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_details",
            "description": "Get customer details by user ID. Use this to fetch customer information like name, email, address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The unique user ID of the customer"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_orders",
            "description": "Get all orders for a customer. Use this to see order history and order details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The unique user ID of the customer"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of orders to return (default 5)"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_details",
            "description": "Get detailed information about a specific order by order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The unique order ID"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get product information by product ID. Use this to check product specs, warranty, return policy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The unique product ID"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_return_policy",
            "description": "Get return policy for a product or category. Use this to check if return/refund is possible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The product ID to check return policy for"
                    },
                    "category": {
                        "type": "string",
                        "description": "The category to check return policy for"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_replacement_policy",
            "description": "Get replacement policy for a product. Use this to check if replacement is available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The product ID to check replacement policy for"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_policies",
            "description": "Get all available policies and rules. Use this to understand return, replacement, and refund guidelines.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipment_status",
            "description": "Get shipment tracking information by shipment ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "shipment_id": {
                        "type": "string",
                        "description": "The unique shipment ID"
                    }
                },
                "required": ["shipment_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_shipments",
            "description": "Get all shipments for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The unique user ID"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_return_request",
            "description": "Create a return request for a product. Use when customer wants to return an item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The customer's user ID"
                    },
                    "order_id": {
                        "type": "string",
                        "description": "The order ID"
                    },
                    "product_id": {
                        "type": "string",
                        "description": "The product ID to return"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for return"
                    }
                },
                "required": ["user_id", "order_id", "product_id", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_replacement_request",
            "description": "Create a replacement request for a product. Use when customer needs a replacement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The customer's user ID"
                    },
                    "order_id": {
                        "type": "string",
                        "description": "The order ID"
                    },
                    "product_id": {
                        "type": "string",
                        "description": "The product ID to replace"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for replacement"
                    }
                },
                "required": ["user_id", "order_id", "product_id", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_pickup",
            "description": "Initiate a pickup for return. Creates shipment for picking up returned item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The customer's user ID"
                    },
                    "order_id": {
                        "type": "string",
                        "description": "The order ID"
                    },
                    "product_id": {
                        "type": "string",
                        "description": "The product ID"
                    },
                    "address": {
                        "type": "string",
                        "description": "Pickup address"
                    }
                },
                "required": ["user_id", "order_id", "product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_delivery",
            "description": "Initiate a delivery for replacement. Creates shipment for delivering replacement item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The customer's user ID"
                    },
                    "order_id": {
                        "type": "string",
                        "description": "The order ID"
                    },
                    "product_id": {
                        "type": "string",
                        "description": "The product ID"
                    },
                    "address": {
                        "type": "string",
                        "description": "Delivery address"
                    }
                },
                "required": ["user_id", "order_id", "product_id"]
            }
        }
    }
]


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

class ToolExecutor:
    """Executes agent tools and returns results"""
    
    def __init__(self):
        self.shipment_manager = None  # Will be set by main
    
    def set_shipment_manager(self, manager):
        """Set the shipment manager instance"""
        self.shipment_manager = manager
    
    def execute_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool by name with given arguments"""
        tool_map = {
            "get_user_details": self._get_user_details,
            "get_user_orders": self._get_user_orders,
            "get_order_details": self._get_order_details,
            "get_product_details": self._get_product_details,
            "get_return_policy": self._get_return_policy,
            "get_replacement_policy": self._get_replacement_policy,
            "get_all_policies": self._get_all_policies,
            "get_shipment_status": self._get_shipment_status,
            "get_user_shipments": self._get_user_shipments,
            "create_return_request": self._create_return_request,
            "create_replacement_request": self._create_replacement_request,
            "initiate_pickup": self._initiate_pickup,
            "initiate_delivery": self._initiate_delivery,
        }
        
        if tool_name in tool_map:
            try:
                result = tool_map[tool_name](arguments)
                return {"success": True, "data": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    def _get_user_details(self, args: Dict) -> Dict:
        """Get user details"""
        user_id = args.get("user_id")
        user = db_manager.get_user_by_id(user_id)
        if user:
            return user
        return {"user_id": user_id, "name": "Customer", "message": "User not found in orders"}
    
    def _get_user_orders(self, args: Dict) -> List[Dict]:
        """Get user orders"""
        user_id = args.get("user_id")
        limit = args.get("limit", 5)
        orders = db_manager.get_recent_orders(user_id, limit)
        return orders if orders else []
    
    def _get_order_details(self, args: Dict) -> Dict:
        """Get specific order details"""
        order_id = args.get("order_id")
        order = db_manager.get_order_by_id(order_id)
        return order if order else {"error": "Order not found"}
    
    def _get_product_details(self, args: Dict) -> Dict:
        """Get product details"""
        product_id = args.get("product_id")
        product = db_manager.get_product_by_id(product_id)
        return product if product else {"error": "Product not found"}
    
    def _get_return_policy(self, args: Dict) -> Dict:
        """Get return policy"""
        product_id = args.get("product_id")
        category = args.get("category")
        policy = db_manager.get_return_policy(product_id, category)
        if not policy:
            return {
                "return_window_days": 30,
                "conditions": ["Product must be unused", "Original packaging required"],
                "refund_method": "Original payment method",
                "is_default": True
            }
        return policy
    
    def _get_replacement_policy(self, args: Dict) -> Dict:
        """Get replacement policy"""
        product_id = args.get("product_id")
        policy = db_manager.get_replacement_policy(product_id)
        if not policy:
            return {
                "replacement_window_days": 7,
                "conditions": ["Defective product", "Wrong product delivered"],
                "is_default": True
            }
        return policy
    
    def _get_all_policies(self, args: Dict) -> List[Dict]:
        """Get all policies"""
        policies = db_manager.get_all_policies()
        if not policies:
            return [{
                "type": "general",
                "return_window_days": 30,
                "replacement_window_days": 7,
                "description": "Standard return and replacement policy"
            }]
        return policies
    
    def _get_shipment_status(self, args: Dict) -> Dict:
        """Get shipment status"""
        shipment_id = args.get("shipment_id")
        shipment = db_manager.get_shipment_by_id(shipment_id)
        return shipment if shipment else {"error": "Shipment not found"}
    
    def _get_user_shipments(self, args: Dict) -> List[Dict]:
        """Get all user shipments"""
        user_id = args.get("user_id")
        shipments = db_manager.get_shipments_by_user(user_id)
        return shipments
    
    def _create_return_request(self, args: Dict) -> Dict:
        """Create a return request"""
        return_data = {
            "user_id": args.get("user_id"),
            "order_id": args.get("order_id"),
            "product_id": args.get("product_id"),
            "reason": args.get("reason"),
            "type": "return"
        }
        result_id = db_manager.create_return_request(return_data)
        if result_id:
            return {
                "return_id": result_id,
                "status": "pending",
                "message": "Return request created successfully"
            }
        return {"error": "Failed to create return request"}
    
    def _create_replacement_request(self, args: Dict) -> Dict:
        """Create a replacement request"""
        replacement_data = {
            "user_id": args.get("user_id"),
            "order_id": args.get("order_id"),
            "product_id": args.get("product_id"),
            "reason": args.get("reason"),
            "type": "replacement"
        }
        result_id = db_manager.create_replacement_request(replacement_data)
        if result_id:
            return {
                "replacement_id": result_id,
                "status": "pending",
                "message": "Replacement request created successfully"
            }
        return {"error": "Failed to create replacement request"}
    
    def _initiate_pickup(self, args: Dict) -> Dict:
        """Initiate pickup shipment"""
        if self.shipment_manager:
            result = self.shipment_manager.create_pickup(
                user_id=args.get("user_id"),
                order_id=args.get("order_id"),
                product_id=args.get("product_id"),
                address=args.get("address")
            )
            return result
        return {"error": "Shipment manager not initialized"}
    
    def _initiate_delivery(self, args: Dict) -> Dict:
        """Initiate delivery shipment"""
        if self.shipment_manager:
            result = self.shipment_manager.create_delivery(
                user_id=args.get("user_id"),
                order_id=args.get("order_id"),
                product_id=args.get("product_id"),
                address=args.get("address")
            )
            return result
        return {"error": "Shipment manager not initialized"}


# Create singleton instance
tool_executor = ToolExecutor()
