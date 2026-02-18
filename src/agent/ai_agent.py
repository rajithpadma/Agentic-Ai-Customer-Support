"""
AI Agent for Agentic Customer Support
Uses OpenRouter API with DeepSeek model
Dynamically queries MongoDB instead of loading data into prompts
"""
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import (
    OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL,
    MAX_TOKENS, TEMPERATURE, AGENT_SYSTEM_PROMPT
)
from src.agent.tools import AGENT_TOOLS, tool_executor
from src.database.database import db_manager


class CustomerSupportAgent:
    """
    Agentic AI Customer Support Agent using OpenRouter API
    
    Key Features:
    - Uses OpenRouter API with DeepSeek model
    - Dynamically queries database only when needed
    - Maintains conversation context efficiently
    - Generates summaries for chat sessions
    - Fallback responses when API unavailable
    """
    
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.api_url = f"{OPENROUTER_API_URL}/chat/completions"
        self.model = OPENROUTER_MODEL
        self.api_available = bool(self.api_key and self.api_key != "your-openrouter-api-key-here")
        
        if self.api_available:
            print(f"✓ OpenRouter API configured with model: {self.model}")
        else:
            print("⚠ OpenRouter API not configured - using fallback responses")
        
        self.max_tokens = MAX_TOKENS
        self.temperature = TEMPERATURE
        self.conversation_history: Dict[str, List[Dict]] = {}
        self.session_context: Dict[str, Dict] = {}
    
    def initialize_session(self, session_id: str, user_id: str = None) -> Dict:
        """Initialize a new chat session"""
        self.conversation_history[session_id] = []
        self.session_context[session_id] = {
            "user_id": user_id,
            "session_id": session_id,
            "started_at": datetime.utcnow().isoformat(),
            "issue_type": None,
            "resolution": None
        }
        return {"status": "initialized", "session_id": session_id}
    
    def set_selected_order(self, session_id: str, order_id: str):
        """Set the selected order for this session"""
        if session_id in self.session_context:
            self.session_context[session_id]["selected_order_id"] = order_id
    
    def chat(self, session_id: str, user_message: str, user_id: str = None, 
             image_analysis: Dict = None, selected_order_id: str = None) -> Dict:
        """Process user message and generate response using the AI Agent"""
        # Initialize session if not exists
        if session_id not in self.conversation_history:
            self.initialize_session(session_id, user_id)
        
        # Update session context with user_id if provided
        if user_id:
            self.session_context[session_id]["user_id"] = user_id
        
        # Update selected order if provided
        if selected_order_id:
            self.session_context[session_id]["selected_order_id"] = selected_order_id
        
        # Build the message with context
        context_message = user_message
        if image_analysis:
            context_message += f"\n\n[Image Analysis Result: Category: {image_analysis.get('category')}, "
            context_message += f"Confidence: {image_analysis.get('confidence', 0):.2%}]"
        
        # Add user message to history
        self.conversation_history[session_id].append({
            "role": "user",
            "content": context_message
        })
        
        # Prepare messages for API call
        messages = self._prepare_messages(session_id)
        
        # Call the AI or use fallback
        if self.api_available:
            response = self._call_openrouter_api(messages, session_id)
        else:
            response = self._fallback_response(user_message, session_id)
        
        # Add assistant response to history
        self.conversation_history[session_id].append({
            "role": "assistant",
            "content": response["message"]
        })
        
        # Save chat to database
        self._save_chat(session_id, user_message, response["message"])
        
        return response
    
    def _prepare_messages(self, session_id: str) -> List[Dict]:
        """Prepare messages for API call with COMPLETE context from database"""
        context = self.session_context.get(session_id, {})
        user_id = context.get("user_id")
        selected_order_id = context.get("selected_order_id")
        
        # Build enhanced system prompt with user data
        system_content = AGENT_SYSTEM_PROMPT
        
        if user_id:
            system_content += f"\n\n========== USER CONTEXT (USE ONLY THIS DATA) =========="
            system_content += f"\nUser ID: {user_id}"
            
            # Fetch user's data
            user_data = db_manager.get_user_by_id(user_id)
            if user_data:
                system_content += f"\nCustomer Name: {user_data.get('name', 'N/A')}"
                system_content += f"\nEmail: {user_data.get('email', 'N/A')}"
                system_content += f"\nPhone: {user_data.get('phone', 'N/A')}"
                system_content += f"\nAddress: {user_data.get('address', 'N/A')}"
            
            # If selected order, show FULL details of that order and its product
            if selected_order_id:
                system_content += f"\n\n========== SELECTED ORDER (CURRENT DISCUSSION) =========="
                order = db_manager.get_order_by_id(selected_order_id)
                if order:
                    system_content += f"\nOrder ID: {order.get('order_id', selected_order_id)}"
                    system_content += f"\nOrder Date: {order.get('order_date', order.get('date', 'N/A'))}"
                    system_content += f"\nOrder Status: {order.get('status', order.get('order_status', 'N/A'))}"
                    system_content += f"\nProduct ID: {order.get('product_id', 'N/A')}"
                    system_content += f"\nProduct Name: {order.get('product_name', order.get('name', 'N/A'))}"
                    system_content += f"\nProduct Category: {order.get('category', order.get('product_category', 'N/A'))}"
                    system_content += f"\nQuantity: {order.get('quantity', 1)}"
                    system_content += f"\nPrice: {order.get('price', order.get('total', 'N/A'))}"
                    system_content += f"\nPayment Method: {order.get('payment_method', 'N/A')}"
                    
                    # Get full product details
                    product_id = order.get('product_id')
                    if product_id:
                        product = db_manager.get_product_by_id(product_id)
                        if product:
                            system_content += f"\n\n--- PRODUCT DETAILS ---"
                            system_content += f"\nProduct Name: {product.get('name', product.get('product_name', 'N/A'))}"
                            system_content += f"\nDescription: {product.get('description', 'N/A')}"
                            system_content += f"\nCategory: {product.get('category', product.get('product_category', 'N/A'))}"
                            system_content += f"\nBrand: {product.get('brand', 'N/A')}"
                            system_content += f"\nPrice: {product.get('price', 'N/A')}"
                            system_content += f"\nWarranty: {product.get('warranty', 'N/A')}"
                            
                            # Get policies for this product category
                            category = product.get('category', product.get('product_category'))
                            if category:
                                policy = db_manager.get_policy_by_category(category)
                                if policy:
                                    system_content += f"\n\n--- APPLICABLE POLICIES FOR {category.upper()} ---"
                                    system_content += f"\nReturn Window: {policy.get('return_window_days', policy.get('return_days', 30))} days"
                                    system_content += f"\nReplacement Window: {policy.get('replacement_window_days', policy.get('replacement_days', 7))} days"
                                    system_content += f"\nRefund Method: {policy.get('refund_method', 'Original payment method')}"
                                    conditions = policy.get('conditions', policy.get('return_conditions', []))
                                    if conditions:
                                        system_content += f"\nConditions: {', '.join(conditions) if isinstance(conditions, list) else conditions}"
            else:
                # Show all orders if no specific order selected
                orders = db_manager.get_orders_by_user(user_id)
                if orders:
                    system_content += f"\n\n========== CUSTOMER'S ORDERS =========="
                    for order in orders:
                        system_content += f"\n- Order ID: {order.get('order_id')} | Product: {order.get('product_name', order.get('product_id', 'N/A'))} | Status: {order.get('status', 'N/A')}"
            
            # Fetch active shipments for this user
            shipments = db_manager.get_shipments_by_user(user_id)
            if shipments:
                system_content += "\n\n========== ACTIVE SHIPMENTS =========="
                for ship in shipments:
                    system_content += f"\nShipment ID: {ship.get('shipment_id')} | Type: {ship.get('type')} | Status: {ship.get('status')} | Order: {ship.get('order_id', 'N/A')}"
        
        # Add general policies if no specific product policy
        if not selected_order_id:
            policies = db_manager.get_all_policies()
            if policies:
                system_content += "\n\n========== GENERAL POLICIES =========="
                for policy in policies[:5]:
                    cat = policy.get('category', policy.get('product_category', 'General'))
                    system_content += f"\n{cat}: Return {policy.get('return_window_days', policy.get('return_days', 30))} days, Replacement {policy.get('replacement_window_days', policy.get('replacement_days', 7))} days"
        
        system_content += "\n\n========== END OF CONTEXT =========="
        system_content += "\nREMEMBER: Only discuss the order, product, and policies shown above. Do not invent any information."
        
        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history (last 10 messages)
        history = self.conversation_history.get(session_id, [])
        messages.extend(history[-10:])
        
        return messages
    
    def _call_openrouter_api(self, messages: List[Dict], session_id: str) -> Dict:
        """Call OpenRouter API and get response"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "Agentic AI Customer Support"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                assistant_message = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if assistant_message:
                    # Process any actions mentioned in the response
                    actions = self._process_response_actions(assistant_message, session_id)
                    return {
                        "message": assistant_message,
                        "actions": actions
                    }
            
            # API call failed
            print(f"OpenRouter API error: {response.status_code} - {response.text}")
            return self._fallback_response(
                self.conversation_history[session_id][-1]["content"], 
                session_id
            )
            
        except Exception as e:
            print(f"Error calling OpenRouter API: {e}")
            return self._fallback_response(
                self.conversation_history[session_id][-1]["content"], 
                session_id
            )
    
    def _process_response_actions(self, response: str, session_id: str) -> List[Dict]:
        """Process and execute any actions mentioned in AI response"""
        actions = []
        context = self.session_context.get(session_id, {})
        user_id = context.get("user_id")
        response_lower = response.lower()
        
        # Detect if AI is confirming actions that should be executed
        if user_id and "pickup" in response_lower and ("scheduled" in response_lower or "initiated" in response_lower):
            actions.append({"tool": "pickup_mentioned", "status": "detected"})
        
        if user_id and "delivery" in response_lower and ("scheduled" in response_lower or "initiated" in response_lower):
            actions.append({"tool": "delivery_mentioned", "status": "detected"})
        
        return actions
    
    def _fallback_response(self, user_message: str, session_id: str) -> Dict:
        """Generate fallback responses when API is unavailable"""
        message_lower = user_message.lower()
        context = self.session_context.get(session_id, {})
        user_id = context.get("user_id")
        actions = []
        
        # Greetings
        if any(g in message_lower for g in ["hi", "hello", "hey", "good morning", "good afternoon"]):
            if user_id:
                user_data = db_manager.get_user_by_id(user_id)
                name = user_data.get("name", "Customer") if user_data else "Customer"
                return {
                    "message": f"Hello {name}! Welcome to Customer Support. I can help you with:\n\n• **Order inquiries**\n• **Returns & Refunds**\n• **Replacements**\n• **Shipment tracking**\n\nHow can I assist you today?",
                    "actions": []
                }
            return {
                "message": "Hello! Welcome to Customer Support. How can I help you today?",
                "actions": []
            }
        
        # Orders
        if any(w in message_lower for w in ["order", "orders", "purchase"]):
            if user_id:
                orders = db_manager.get_recent_orders(user_id, 5)
                if orders:
                    order_list = "\n".join([f"• **{o.get('order_id')}** - {o.get('status', 'N/A')}" for o in orders])
                    return {"message": f"Your recent orders:\n\n{order_list}\n\nNeed details about any order?", "actions": []}
            return {"message": "Please provide your Order ID to check order status.", "actions": []}
        
        # Returns
        if any(w in message_lower for w in ["return", "refund"]):
            policy = db_manager.get_return_policy()
            return {
                "message": f"**Return Policy:**\n• Returns within **{policy.get('return_window_days', 30)} days**\n• Product must be unused\n• Original packaging required\n\nProvide Order ID and reason to initiate return.",
                "actions": []
            }
        
        # Replacements
        if any(w in message_lower for w in ["replace", "damaged", "defective", "broken"]):
            policy = db_manager.get_replacement_policy()
            return {
                "message": f"**Replacement Policy:**\n• Within **{policy.get('replacement_window_days', 7)} days**\n• For defective/damaged products\n\nProvide Order ID and describe the issue.",
                "actions": []
            }
        
        # Tracking
        if any(w in message_lower for w in ["track", "shipping", "shipment", "delivery", "where"]):
            if user_id:
                shipments = db_manager.get_shipments_by_user(user_id)
                if shipments:
                    ship_list = "\n".join([f"• **{s.get('shipment_id')}** - {s.get('status')}" for s in shipments[:5]])
                    return {"message": f"Your shipments:\n\n{ship_list}\n\nView 'Shipments' page for details.", "actions": []}
            return {"message": "Provide Shipment ID or Order ID to track.", "actions": []}
        
        # Help
        if any(w in message_lower for w in ["help", "support"]):
            return {
                "message": "I can help with:\n\n📦 **Orders** - Check status\n↩️ **Returns** - Initiate returns\n🔄 **Replacements** - Request replacement\n🚚 **Tracking** - Track shipments\n\nWhat do you need?",
                "actions": []
            }
        
        # Thanks
        if any(w in message_lower for w in ["thank", "thanks"]):
            return {"message": "You're welcome! Anything else I can help with?", "actions": []}
        
        # Bye
        if any(w in message_lower for w in ["bye", "goodbye"]):
            return {"message": "Thank you for contacting us! Have a great day! 👋", "actions": []}
        
        # Default
        return {
            "message": "I'm here to help! Please specify:\n• Order ID for order queries\n• Issue type (return/replacement/tracking)\n\nWhat do you need assistance with?",
            "actions": []
        }
    
    def _save_chat(self, session_id: str, user_message: str, assistant_message: str):
        """Save chat messages to database"""
        context = self.session_context.get(session_id, {})
        
        db_manager.save_chat_message({
            "session_id": session_id,
            "user_id": context.get("user_id"),
            "role": "user",
            "content": user_message
        })
        
        db_manager.save_chat_message({
            "session_id": session_id,
            "user_id": context.get("user_id"),
            "role": "assistant",
            "content": assistant_message
        })
    
    def generate_summary(self, session_id: str) -> Dict:
        """Generate a summary of the chat session"""
        history = self.conversation_history.get(session_id, [])
        context = self.session_context.get(session_id, {})
        
        if not history:
            return {"error": "No conversation history found"}
        
        # Try AI summary
        if self.api_available:
            try:
                summary_prompt = "Analyze this customer support conversation. Return JSON with: issue_type, issue_description, proposed_solution, resolution_status, customer_sentiment, action_items.\n\nConversation:\n"
                for msg in history:
                    summary_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
                
                response = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:5000"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Return only valid JSON."},
                            {"role": "user", "content": summary_prompt}
                        ],
                        "max_tokens": 500
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    try:
                        summary = json.loads(summary_text)
                    except:
                        import re
                        match = re.search(r'\{.*\}', summary_text, re.DOTALL)
                        summary = json.loads(match.group()) if match else {"raw": summary_text}
                    
                    summary.update({
                        "session_id": session_id,
                        "user_id": context.get("user_id"),
                        "timestamp": datetime.utcnow().isoformat(),
                        "message_count": len(history)
                    })
                    
                    db_manager.save_chat_summary(summary)
                    return summary
            except Exception as e:
                print(f"AI summary error: {e}")
        
        # Fallback summary
        return self._generate_fallback_summary(session_id, history, context)
    
    def _generate_fallback_summary(self, session_id: str, history: List, context: Dict) -> Dict:
        """Generate basic summary without AI"""
        all_text = " ".join([m.get("content", "") for m in history]).lower()
        
        issue_type = "inquiry"
        if any(w in all_text for w in ["return", "refund"]): issue_type = "return"
        elif any(w in all_text for w in ["replace", "damaged"]): issue_type = "replacement"
        elif any(w in all_text for w in ["track", "shipping"]): issue_type = "tracking"
        
        sentiment = "neutral"
        if any(w in all_text for w in ["thank", "great"]): sentiment = "satisfied"
        elif any(w in all_text for w in ["angry", "upset"]): sentiment = "dissatisfied"
        
        summary = {
            "session_id": session_id,
            "user_id": context.get("user_id"),
            "issue_type": issue_type,
            "issue_description": f"Customer inquiry: {issue_type}",
            "proposed_solution": "pending",
            "resolution_status": "pending",
            "customer_sentiment": sentiment,
            "action_items": ["Review conversation"],
            "timestamp": datetime.utcnow().isoformat(),
            "message_count": len(history)
        }
        
        db_manager.save_chat_summary(summary)
        return summary
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        return self.conversation_history.get(session_id, [])
    
    def clear_session(self, session_id: str):
        self.conversation_history.pop(session_id, None)
        self.session_context.pop(session_id, None)


# Create singleton instance
support_agent = CustomerSupportAgent()
