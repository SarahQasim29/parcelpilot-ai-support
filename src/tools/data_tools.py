# src/tools/data_tools.py
from typing import Dict, Any, Optional
import pandas as pd
from langchain.tools import tool
from src.auth.auth_manager import User
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DataTools:
    def __init__(self, structured_data: Dict[str, pd.DataFrame]):
        self.structured_data = structured_data
        self.current_user = None
    
    def set_user(self, user: User):
        """Set current user for access control"""
        self.current_user = user
    
    # ============================================
    # TOOL 1: QUERY ORDERS
    # ============================================
    
    @tool  # ← CORRECT: Decorator on the method
    def query_orders(self, order_id: str = None, account_id: str = None) -> str:
        """
        Query order information from the system.
        
        Args:
            order_id: Specific order ID (e.g., "ORD-1001", "ORD-1002")
            account_id: Account ID to filter orders
        """
        if not self.current_user:
            return "Authentication required. Please log in."
        
        try:
            # Get orders data
            orders_df = self.structured_data.get('orders', pd.DataFrame())
            if orders_df.empty:
                orders_df = self.structured_data.get('Orders', pd.DataFrame())
            
            if orders_df.empty:
                return "No order data available."
            
            # Access control
            if account_id and not self.current_user.can_access_account(account_id):
                return "❌ Access Denied: You don't have permission for this account."
            
            # Filter by account
            if 'account_id' in orders_df.columns:
                if account_id:
                    orders_df = orders_df[orders_df['account_id'] == account_id]
                elif self.current_user.account_id:
                    orders_df = orders_df[orders_df['account_id'] == self.current_user.account_id]
            
            # Filter by order_id
            if order_id and 'order_id' in orders_df.columns:
                orders_df = orders_df[orders_df['order_id'] == order_id]
            
            if orders_df.empty:
                return "No orders found matching your criteria."
            
            # Format response
            response = ""
            for _, row in orders_df.iterrows():
                order_id_val = row.get('order_id', 'N/A')
                status = row.get('status', 'Unknown')
                carrier = row.get('carrier', 'N/A')
                fee = row.get('shipment_fee_inr', 'N/A')
                booked_at = row.get('booked_at', 'N/A')
                pickup_start = row.get('pickup_window_start', None)
                pickup_end = row.get('pickup_window_end', None)
                notes = row.get('notes', None)
                
                response += f"📦 Order {order_id_val}\n"
                response += f"   Status: {status}\n"
                response += f"   Carrier: {carrier}\n"
                response += f"   Fee: ₹{fee}\n"
                if booked_at and booked_at != 'N/A':
                    response += f"   Booked: {booked_at}\n"
                if pickup_start and pickup_end:
                    response += f"   Pickup Window: {pickup_start} - {pickup_end}\n"
                if notes and pd.notna(notes):
                    response += f"   Note: {notes}\n"
                response += "\n"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Query orders error: {e}")
            return f"Error querying orders: {str(e)}"
    
    # ============================================
    # TOOL 2: QUERY TICKETS
    # ============================================
    
    @tool  # ← CORRECT: Decorator on the method
    def query_tickets(self, ticket_id: str = None, account_id: str = None) -> str:
        """
        Query ticket information from the system.
        
        Args:
            ticket_id: Specific ticket ID (e.g., "TKT-501", "TKT-502")
            account_id: Account ID to filter tickets
        """
        if not self.current_user:
            return "Authentication required. Please log in."
        
        try:
            # Get tickets data
            tickets_df = self.structured_data.get('tickets', pd.DataFrame())
            if tickets_df.empty:
                tickets_df = self.structured_data.get('Tickets', pd.DataFrame())
            
            if tickets_df.empty:
                return "No ticket data available."
            
            # Access control
            if account_id and not self.current_user.can_access_account(account_id):
                return "❌ Access Denied: You don't have permission for this account."
            
            # Filter by account
            if 'account_id' in tickets_df.columns:
                if account_id:
                    tickets_df = tickets_df[tickets_df['account_id'] == account_id]
                elif self.current_user.account_id:
                    tickets_df = tickets_df[tickets_df['account_id'] == self.current_user.account_id]
            
            # Filter by ticket_id
            if ticket_id and 'ticket_id' in tickets_df.columns:
                tickets_df = tickets_df[tickets_df['ticket_id'] == ticket_id]
            
            if tickets_df.empty:
                return "No tickets found matching your criteria."
            
            # Format response
            response = ""
            for _, row in tickets_df.iterrows():
                ticket_id_val = row.get('ticket_id', 'N/A')
                status = row.get('status', 'Unknown')
                subject = row.get('subject', 'N/A')
                description = row.get('description', '')
                assigned_to = row.get('assigned_to', 'Unassigned')
                created_at = row.get('created_at', 'N/A')
                channel = row.get('channel', 'N/A')
                historical_resolution = row.get('historical_resolution', None)
                
                response += f"🎫 Ticket {ticket_id_val}\n"
                response += f"   Status: {status}\n"
                response += f"   Subject: {subject}\n"
                response += f"   Created: {created_at}\n"
                response += f"   Assigned To: {assigned_to}\n"
                response += f"   Channel: {channel}\n"
                if description and pd.notna(description):
                    response += f"   Description: {description[:200]}...\n"
                if historical_resolution and pd.notna(historical_resolution):
                    response += f"   ⚠️ Historical Resolution (may be incorrect): {historical_resolution}\n"
                response += "\n"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Query tickets error: {e}")
            return f"Error querying tickets: {str(e)}"
    
    # ============================================
    # TOOL 3: CALCULATE CANCELLATION FEE
    # ============================================
    
    @tool  # ← CORRECT: Decorator on the method
    def calculate_cancellation_fee(self, order_id: str, account_id: str = None) -> str:
        """
        Calculate cancellation fee for an order based on policies and agreements.
        
        Args:
            order_id: The order ID to check (e.g., "ORD-1001")
            account_id: The account ID for the order (optional)
        """
        if not self.current_user:
            return "Authentication required. Please log in."
        
        try:
            # Get orders data
            orders_df = self.structured_data.get('orders', pd.DataFrame())
            if orders_df.empty:
                orders_df = self.structured_data.get('Orders', pd.DataFrame())
            
            if orders_df.empty:
                return "No order data available."
            
            # Access control
            if account_id and not self.current_user.can_access_account(account_id):
                return "❌ Access Denied: You don't have permission for this account."
            
            # Filter by account
            if 'account_id' in orders_df.columns:
                if account_id:
                    orders_df = orders_df[orders_df['account_id'] == account_id]
                elif self.current_user.account_id:
                    orders_df = orders_df[orders_df['account_id'] == self.current_user.account_id]
            
            # Find the order
            if 'order_id' in orders_df.columns:
                order = orders_df[orders_df['order_id'] == order_id]
            else:
                return "Order ID column not found in data."
            
            if order.empty:
                return f"No order found with ID: {order_id}"
            
            row = order.iloc[0]
            status = row.get('status', '')
            booked_at = row.get('booked_at', None)
            notes = row.get('notes', '')
            
            # Determine cancellation eligibility
            response = f"📋 Cancellation Analysis for {order_id}:\n\n"
            
            # Check status
            if status == 'BOOKED':
                response += "✅ Order is BOOKED (not picked up yet)\n"
                
                if booked_at:
                    try:
                        booked_time = pd.to_datetime(booked_at)
                        time_diff = (datetime.now() - booked_time).total_seconds() / 3600
                        if time_diff <= 24:
                            response += "✅ Within 24 hours of booking - NO CANCELLATION FEE\n"
                            response += "   You can cancel this order for free."
                        else:
                            response += f"⚠️ {time_diff:.1f} hours since booking (exceeds 24 hours)\n"
                            response += "   Cancellation fee may apply. Contact support."
                    except:
                        response += "⚠️ Could not calculate booking time.\n"
                else:
                    response += "⚠️ Booking time not available.\n"
            elif status == 'PICKED_UP':
                response += "❌ Order has already been PICKED UP\n"
                response += "   Cancellation fee will apply. Contact support."
            elif status == 'DELIVERED':
                response += "❌ Order has already been DELIVERED\n"
                response += "   Cancellation is not possible."
            else:
                response += f"⚠️ Order status: {status}\n"
                response += "   Contact support for cancellation options."
            
            if notes and pd.notna(notes):
                response += f"\n📝 Notes: {notes}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in calculate_cancellation_fee: {str(e)}")
            return f"Error calculating cancellation fee: {str(e)}"