"""
Main Entry Point for Agentic AI Customer Support System
FIXED: Tracking ID generation and Excel exports
"""
import os
import sys
import secrets
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import HOST, PORT, DEBUG, EXPORT_PATH
from src.database.database import db_manager
from src.auth.credentials import credentials_manager
from src.agent.ai_agent import support_agent
from src.agent.tools import tool_executor
from src.vision.vision import vision_analyzer
from src.shipment.shipment import shipment_manager
from src.utils.excel_generator import excel_generator


app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')
app.secret_key = secrets.token_hex(32)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

tool_executor.set_shipment_manager(shipment_manager)


# =============================================================================
# FRONTEND ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/chat')
def chat_page():
    return render_template('index.html')

@app.route('/shipments')
def shipments_page():
    return render_template('shipments.html')


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    orders = db_manager.get_orders_by_user(user_id)
    
    if not orders:
        return jsonify({"success": False, "error": "No orders found for this User ID"}), 404
    
    session_id = secrets.token_urlsafe(16)
    session['session_id'] = session_id
    session['user_id'] = user_id
    
    user_info = db_manager.get_user_by_id(user_id)
    
    formatted_orders = []
    for order in orders:
        formatted_orders.append({
            "order_id": order.get('order_id', ''),
            "product_id": order.get('product_id', ''),
            "product_name": order.get('product_name', 'Unknown Product'),
            "status": order.get('status', 'Delivered'),
            "date": str(order.get('date', 'N/A')),
            "price": order.get('price', 'N/A')
        })
    
    return jsonify({
        "success": True,
        "user_id": user_id,
        "session_id": session_id,
        "user_info": user_info,
        "orders": formatted_orders,
        "order_count": len(formatted_orders)
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})


# =============================================================================
# CHAT ENDPOINTS
# =============================================================================

@app.route('/api/chat', methods=['POST'])
def chat():
    session_id = None
    try:
        data = request.json or {}
        message = data.get('message', '')
        user_id = data.get('user_id') or session.get('user_id')
        session_id = data.get('session_id') or session.get('session_id')
        image_analysis = data.get('image_analysis')
        selected_order_id = data.get('selected_order_id') or session.get('selected_order_id')
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        if not session_id:
            session_id = secrets.token_urlsafe(16)
            session['session_id'] = session_id
        
        if selected_order_id:
            session['selected_order_id'] = selected_order_id
        
        response = support_agent.chat(
            session_id=session_id,
            user_message=message,
            user_id=user_id,
            image_analysis=image_analysis,
            selected_order_id=selected_order_id
        )
        
        return jsonify({
            "response": response.get('message', 'How can I help you?'),
            "session_id": session_id,
            "actions": response.get('actions', [])
        })
    except Exception as e:
        import traceback
        print(f"Chat error: {e}")
        traceback.print_exc()
        return jsonify({
            "response": "I apologize for the inconvenience. How can I help you?",
            "session_id": session_id,
            "actions": []
        })

@app.route('/api/chat/end', methods=['POST'])
def end_chat():
    """
    FIXED: End chat - Auto-generates summary, creates shipment, exports Excel
    Returns tracking ID to user
    """
    data = request.json or {}
    session_id = data.get('session_id') or session.get('session_id')
    user_id = data.get('user_id') or session.get('user_id')
    selected_order_id = data.get('selected_order_id') or session.get('selected_order_id')
    
    if not session_id:
        return jsonify({"error": "No active session"}), 400
    
    print("\n" + "="*80)
    print("  END CHAT - AUTOMATED PROCESSING")
    print("="*80)
    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")
    print(f"Order ID: {selected_order_id}")
    print("="*80 + "\n")
    
    result = {
        "success": True,
        "session_id": session_id,
        "user_id": user_id,
        "message": "Thank you for contacting us! Your request has been processed."
    }
    
    try:
        # STEP 1: Generate summary
        print("📋 Generating chat summary...")
        summary = support_agent.generate_summary(session_id)
        print(f"✅ Summary generated: {summary.get('issue_type', 'N/A')}")
        
        # STEP 2: Get order details
        order = None
        if selected_order_id:
            order = db_manager.get_order_by_id(selected_order_id)
            print(f"📦 Order retrieved: {order.get('order_id', 'N/A') if order else 'Not found'}")
        
        if not order and user_id:
            orders = db_manager.get_recent_orders(user_id, 1)
            if orders:
                order = orders[0]
                print(f"📦 Using recent order: {order.get('order_id', 'N/A')}")
        
        # STEP 3: Create shipment based on solution
        shipment_created = False
        tracking_id = None
        shipment_type = None
        
        if order:
            proposed = summary.get("proposed_solution", "").lower()
            print(f"💡 Proposed solution: {proposed}")
            
            # Check for return/refund
            if "return" in proposed or "refund" in proposed:
                print("🚚 Creating PICKUP shipment for return...")
                shipment_result = shipment_manager.create_pickup(
                    user_id=user_id,
                    order_id=order.get("order_id", selected_order_id),
                    product_id=order.get("product_id", "")
                )
                
                if shipment_result.get("success"):
                    shipment_created = True
                    tracking_id = shipment_result.get("shipment_id")
                    shipment_type = "pickup"
                    print(f"✅ Pickup shipment created: {tracking_id}")
            
            # Check for replacement
            elif "replace" in proposed or "replacement" in proposed:
                print("🚚 Creating DELIVERY shipment for replacement...")
                shipment_result = shipment_manager.create_delivery(
                    user_id=user_id,
                    order_id=order.get("order_id", selected_order_id),
                    product_id=order.get("product_id", "")
                )
                
                if shipment_result.get("success"):
                    shipment_created = True
                    tracking_id = shipment_result.get("shipment_id")
                    shipment_type = "delivery"
                    print(f"✅ Delivery shipment created: {tracking_id}")
        
        # STEP 4: Update summary with shipment info
        if shipment_created and tracking_id:
            summary["shipment_id"] = tracking_id
            summary["shipment_type"] = shipment_type
            db_manager.save_chat_summary(summary)
            print(f"✅ Summary updated with tracking ID: {tracking_id}")
        
        # STEP 5: Generate Excel reports
        print("\n📊 Generating Excel reports...")
        try:
            chat_file = excel_generator.generate_chat_summaries_report()
            print(f"✅ Chat summaries: {chat_file}")
            
            shipment_file = excel_generator.generate_shipments_report()
            print(f"✅ Shipments: {shipment_file}")
        except Exception as e:
            print(f"⚠️  Excel export error: {e}")
            import traceback
            traceback.print_exc()
        
        # STEP 6: Prepare response for user
        if shipment_created and tracking_id:
            result["tracking_id"] = tracking_id
            result["shipment_type"] = shipment_type
            
            shipment_type_text = "Return Pickup" if shipment_type == "pickup" else "Replacement Delivery"
            result["message"] = f"Thank you for contacting us! Your {shipment_type_text} has been scheduled.\n\nTracking ID: {tracking_id}\n\nYou can track your shipment on the Shipments page."
            
            print(f"\n✅ TRACKING ID GENERATED: {tracking_id}")
            print(f"✅ Type: {shipment_type_text}")
        
        print("\n" + "="*80)
        print("  ✅ END CHAT PROCESSING COMPLETE")
        print("="*80 + "\n")
                    
    except Exception as e:
        print(f"\n❌ Error during end chat processing: {e}")
        import traceback
        traceback.print_exc()
    
    # Clear session
    support_agent.clear_session(session_id)
    session.pop('selected_order_id', None)
    
    return jsonify(result)


# =============================================================================
# IMAGE ANALYSIS ENDPOINTS
# =============================================================================

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    """FIXED: Analyze uploaded image using product-specific H5 model"""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Get product info from request
    product_id = request.form.get('product_id')
    product_name = request.form.get('product_name')
    order_id = request.form.get('order_id')
    
    print(f"\n📷 Image Analysis Request:")
    print(f"   Product ID: {product_id}")
    print(f"   Product Name: {product_name}")
    print(f"   Order ID: {order_id}\n")
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        # Use product-specific model based on product_name
        result = vision_analyzer.analyze_image(
            filepath, 
            product_id=product_id,
            product_name=product_name
        )
        os.remove(filepath)
        return jsonify(result)
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        print(f"❌ Image analysis error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =============================================================================
# SHIPMENT ENDPOINTS
# =============================================================================

@app.route('/api/shipments', methods=['GET'])
def get_shipments():
    user_id = request.args.get('user_id') or session.get('user_id')
    
    if user_id:
        shipments = db_manager.get_shipments_by_user(user_id)
    else:
        shipments = db_manager.get_all_shipments()
    
    return jsonify({"shipments": shipments})

@app.route('/api/shipments/<shipment_id>', methods=['GET'])
def get_shipment(shipment_id):
    shipment = shipment_manager.get_shipment_status(shipment_id)
    return jsonify(shipment)

@app.route('/api/shipments/create-pickup', methods=['POST'])
def create_pickup():
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')
    order_id = data.get('order_id')
    product_id = data.get('product_id')
    address = data.get('address')
    
    if not all([user_id, order_id, product_id]):
        return jsonify({"error": "user_id, order_id, and product_id are required"}), 400
    
    result = shipment_manager.create_pickup(user_id, order_id, product_id, address)
    return jsonify(result)

@app.route('/api/shipments/create-delivery', methods=['POST'])
def create_delivery():
    data = request.json
    user_id = data.get('user_id') or session.get('user_id')
    order_id = data.get('order_id')
    product_id = data.get('product_id')
    address = data.get('address')
    
    if not all([user_id, order_id, product_id]):
        return jsonify({"error": "user_id, order_id, and product_id are required"}), 400
    
    result = shipment_manager.create_delivery(user_id, order_id, product_id, address)
    return jsonify(result)


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@app.route('/api/export/chat-summaries', methods=['GET'])
def export_chat_summaries():
    filepath = excel_generator.generate_chat_summaries_report()
    return send_file(filepath, as_attachment=True)

@app.route('/api/export/shipments', methods=['GET'])
def export_shipments():
    filepath = excel_generator.generate_shipments_report()
    return send_file(filepath, as_attachment=True)


# =============================================================================
# DATA ENDPOINTS
# =============================================================================

@app.route('/api/user/<user_id>/data', methods=['GET'])
def get_user_data(user_id):
    user = db_manager.get_user_by_id(user_id)
    orders = db_manager.get_orders_by_user(user_id)
    
    product_ids = list(set([o.get('product_id') for o in orders if o.get('product_id')]))
    products = db_manager.get_products_by_ids(product_ids)
    
    policies = db_manager.get_all_policies()
    shipments = db_manager.get_shipments_by_user(user_id)
    
    return jsonify({
        "user": user,
        "orders": orders,
        "products": products,
        "policies": policies,
        "shipments": shipments
    })


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    model_info = vision_analyzer.get_model_info()
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected" if db_manager.db else "disconnected",
            "ai_agent": "ready" if support_agent.api_available else "fallback_mode",
            "vision_models": model_info["total_models"],
            "exports_path": EXPORT_PATH
        },
        "vision_models": model_info["models"]
    })


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def initialize():
    print("\n" + "="*80)
    print("  AGENTIC AI CUSTOMER SUPPORT SYSTEM")
    print("="*80 + "\n")
    
    print("🔧 Initializing services...")
    
    # Connect to database
    db_connected = db_manager.connect()
    if not db_connected:
        print("\n⚠️  Warning: Database not connected. Some features may not work.")
        print("  Make sure MongoDB is running and MONGODB_URI is correct.\n")
    
    # Check vision models
    model_info = vision_analyzer.get_model_info()
    if model_info["total_models"] > 0:
        print(f"\n✅ Vision models loaded: {model_info['total_models']}")
        for model_name in model_info["models"]:
            print(f"   • {model_name}")
    else:
        print("\n⚠️  No vision models found")
        print(f"   Place models in: {vision_analyzer.model_dir}")
        print(f"   Format: ProductName_good_bad_classifier.h5")
        print(f"   Example: AirChef Fryo_good_bad_classifier.h5")
    
    # Ensure export directory exists
    os.makedirs(EXPORT_PATH, exist_ok=True)
    print(f"\n📁 Excel exports will be saved to: {EXPORT_PATH}")
    
    print("\n" + "-"*80)
    print(f"  🚀 Server starting on http://{HOST}:{PORT}")
    print("-"*80 + "\n")


if __name__ == '__main__':
    initialize()
    app.run(host=HOST, port=PORT, debug=DEBUG)