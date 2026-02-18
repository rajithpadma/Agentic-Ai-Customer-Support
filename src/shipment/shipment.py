"""
Shipment Module for Agentic AI Customer Support
Handles pickup and delivery creation with automated timeline progression
Similar to Amazon/Flipkart shipment tracking (48 hours total)
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import SHIPMENT_STAGES, TOTAL_DELIVERY_HOURS
from src.database.database import db_manager


class ShipmentManager:
    """
    Manages shipments including pickups (for returns) and deliveries (for replacements)
    Implements automated timeline progression over 48 hours
    """
    
    # Shipment stages for pickup (return)
    PICKUP_STAGES = [
        {"name": "Pickup Requested", "duration_hours": 2},
        {"name": "Pickup Scheduled", "duration_hours": 6},
        {"name": "Agent Assigned", "duration_hours": 8},
        {"name": "Out for Pickup", "duration_hours": 16},
        {"name": "Package Picked Up", "duration_hours": 12},
        {"name": "Returned to Warehouse", "duration_hours": 4}
    ]
    
    # Shipment stages for delivery (replacement)
    DELIVERY_STAGES = [
        {"name": "Order Confirmed", "duration_hours": 2},
        {"name": "Pickup Scheduled", "duration_hours": 4},
        {"name": "Package Picked Up", "duration_hours": 6},
        {"name": "Shipped", "duration_hours": 8},
        {"name": "In Transit", "duration_hours": 14},
        {"name": "Out for Delivery", "duration_hours": 10},
        {"name": "Delivered", "duration_hours": 4}
    ]
    
    def __init__(self):
        self.active_simulations: Dict[str, threading.Thread] = {}
        self.simulation_speed = 1.0  # 1.0 = real time, higher = faster
    
    def create_pickup(self, user_id: str, order_id: str, product_id: str, 
                      address: str = None) -> Dict:
        """
        Create a pickup shipment for returns
        
        Args:
            user_id: Customer's user ID
            order_id: Original order ID
            product_id: Product being returned
            address: Pickup address (optional, will fetch from user profile)
        
        Returns:
            Dict with shipment details
        """
        shipment_id = f"PKP-{uuid.uuid4().hex[:8].upper()}"
        
        if not address:
            user = db_manager.get_user_by_id(user_id)
            if user:
                address = user.get("address", "Address not found")
        
        timeline = self._generate_timeline(self.PICKUP_STAGES)
        
        shipment_data = {
            "shipment_id": shipment_id,
            "type": "pickup",
            "user_id": user_id,
            "order_id": order_id,
            "product_id": product_id,
            "address": address or "Address not provided",
            "status": "Pickup Requested",
            "current_stage": timeline[0],
            "timeline": timeline,
            "estimated_completion": timeline[-1]["estimated_time"],
            "created_at": datetime.utcnow()
        }
        
        db_manager.create_shipment(shipment_data)
        self._start_simulation(shipment_id, "pickup")
        
        return {
            "success": True,
            "shipment_id": shipment_id,
            "type": "pickup",
            "status": "Pickup Requested",
            "estimated_completion": timeline[-1]["estimated_time"].isoformat(),
            "message": f"Pickup scheduled. Shipment ID: {shipment_id}"
        }
    
    def create_delivery(self, user_id: str, order_id: str, product_id: str,
                        address: str = None) -> Dict:
        """
        Create a delivery shipment for replacements
        """
        shipment_id = f"DLV-{uuid.uuid4().hex[:8].upper()}"
        
        if not address:
            user = db_manager.get_user_by_id(user_id)
            if user:
                address = user.get("address", "Address not found")
        
        timeline = self._generate_timeline(self.DELIVERY_STAGES)
        
        shipment_data = {
            "shipment_id": shipment_id,
            "type": "delivery",
            "user_id": user_id,
            "order_id": order_id,
            "product_id": product_id,
            "address": address or "Address not provided",
            "status": "Order Confirmed",
            "current_stage": timeline[0],
            "timeline": timeline,
            "estimated_completion": timeline[-1]["estimated_time"],
            "created_at": datetime.utcnow()
        }
        
        db_manager.create_shipment(shipment_data)
        self._start_simulation(shipment_id, "delivery")
        
        return {
            "success": True,
            "shipment_id": shipment_id,
            "type": "delivery",
            "status": "Order Confirmed",
            "estimated_completion": timeline[-1]["estimated_time"].isoformat(),
            "message": f"Replacement delivery initiated. Shipment ID: {shipment_id}"
        }
    
    def _generate_timeline(self, stages: List[Dict]) -> List[Dict]:
        """Generate timeline with estimated times for each stage"""
        timeline = []
        current_time = datetime.utcnow()
        
        for stage in stages:
            stage_data = {
                "name": stage["name"],
                "duration_hours": stage["duration_hours"],
                "estimated_time": current_time,
                "actual_time": None,
                "completed": False
            }
            
            if not timeline:
                stage_data["actual_time"] = current_time
                stage_data["completed"] = True
            
            timeline.append(stage_data)
            current_time += timedelta(hours=stage["duration_hours"])
        
        return timeline
    
    def _start_simulation(self, shipment_id: str, shipment_type: str):
        """Start background simulation for shipment progression"""
        def simulate():
            stages = self.PICKUP_STAGES if shipment_type == "pickup" else self.DELIVERY_STAGES
            
            for i, stage in enumerate(stages[1:], 1):
                # Wait time scaled (using seconds for demo, would be hours in production)
                wait_time = stage["duration_hours"] / self.simulation_speed
                time.sleep(min(wait_time, 10))  # Cap at 10 seconds for demo
                
                stage_data = {
                    "name": stage["name"],
                    "actual_time": datetime.utcnow().isoformat(),
                    "completed": True
                }
                
                db_manager.update_shipment_status(shipment_id, stage["name"], stage_data)
            
            if shipment_id in self.active_simulations:
                del self.active_simulations[shipment_id]
        
        thread = threading.Thread(target=simulate, daemon=True)
        thread.start()
        self.active_simulations[shipment_id] = thread
    
    def get_shipment_status(self, shipment_id: str) -> Dict:
        """Get current status of a shipment"""
        shipment = db_manager.get_shipment_by_id(shipment_id)
        if not shipment:
            return {"error": "Shipment not found"}
        
        timeline_display = []
        for stage in shipment.get("timeline", []):
            timeline_display.append({
                "stage": stage["name"],
                "estimated": stage.get("estimated_time"),
                "actual": stage.get("actual_time"),
                "completed": stage.get("completed", False)
            })
        
        return {
            "shipment_id": shipment_id,
            "type": shipment.get("type"),
            "status": shipment.get("status"),
            "address": shipment.get("address"),
            "timeline": timeline_display,
            "estimated_completion": shipment.get("estimated_completion"),
            "created_at": shipment.get("created_at")
        }
    
    def get_all_active_shipments(self) -> List[Dict]:
        """Get all shipments that are not yet completed"""
        all_shipments = db_manager.get_all_shipments()
        active = []
        
        for shipment in all_shipments:
            final_status = "Returned to Warehouse" if shipment.get("type") == "pickup" else "Delivered"
            if shipment.get("status") != final_status:
                active.append({
                    "shipment_id": shipment.get("shipment_id"),
                    "type": shipment.get("type"),
                    "user_id": shipment.get("user_id"),
                    "status": shipment.get("status"),
                    "created_at": shipment.get("created_at")
                })
        
        return active


# Create singleton instance
shipment_manager = ShipmentManager()
