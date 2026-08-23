# src/tools/langchain_tools.py
"""
LangChain-compatible tools for the AI agent
"""

from langchain.tools import tool
import pandas as pd
import re
import logging

logger = logging.getLogger(__name__)

class LangChainTools:
    def __init__(self, data_ingestion, structured_data, action_tools):
        self.data_ingestion = data_ingestion
        self.structured_data = structured_data
        self.action_tools = action_tools
        self.current_user = None
    
    def set_user(self, user):
        self.current_user = user
    
    @tool
    def search_policies(self, query: str) -> str:
        """
        Search through policies, agreements, and documentation.
        Use this tool when you need information about:
        - Cancellation policies
        - Service credits
        - Customer agreements
        - Support SLAs
        - Product operations
        
        Args:
            query: The search query string (e.g., "cancellation policy Northstar")
        """
        try:
            # Use your existing document search
            from src.tools.document_tools import DocumentTools
            doc_tools = DocumentTools(self.data_ingestion)
            return doc_tools.search_policies(query)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Error searching documents: {str(e)}"
    
    @tool
    def query_orders(self, order_id: str = None, account_id: str = None) -> str:
        """
        Query order information.
        
        Args:
            order_id: Specific order ID (e.g., "ORD-1001")
            account_id: Account ID to filter orders
        """
        if not self.current_user:
            return "Authentication required. Please log in."
        
        try:
            orders_df = self.structured_data.get('orders', pd.DataFrame())
            if orders_df.empty:
                return "No order data available."
            
            # Access control
            if account_id and not self.current_user.can_access_account(account_id):
                return "Access denied: You don't have permission for this account."
            
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
                return "No orders found matching the criteria."
            
            # Format response
            response = f"Found {len(orders_df)} orders:\n\n"
            for _, row in orders_df.iterrows():
                response += f"• Order {row.get('order_id')}: {row.get('status')} | "
                response += f"Carrier: {row.get('carrier')} | "
                response += f"Fee: ₹{row.get('shipment_fee_inr')}\n"
            
            return response
            
        except Exception as e:
            return f"Error querying orders: {str(e)}"
    
    @tool
    def query_tickets(self, ticket_id: str = None, account_id: str = None) -> str:
        """
        Query ticket information.
        
        Args:
            ticket_id: Specific ticket ID (e.g., "TKT-501")
            account_id: Account ID to filter tickets
        """
        if not self.current_user:
            return "Authentication required. Please log in."
        
        try:
            tickets_df = self.structured_data.get('tickets', pd.DataFrame())
            if tickets_df.empty:
                return "No ticket data available."
            
            # Access control
            if account_id and not self.current_user.can_access_account(account_id):
                return "Access denied: You don't have permission for this account."
            
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
                return "No tickets found matching the criteria."
            
            # Format response
            response = f"Found {len(tickets_df)} tickets:\n\n"
            for _, row in tickets_df.iterrows():
                response += f"• Ticket {row.get('ticket_id')}: {row.get('status')} | "
                response += f"Subject: {row.get('subject')} | "
                response += f"Created: {row.get('created_at')}\n"
                if row.get('historical_resolution'):
                    response += f"  ⚠️ Historical (may be incorrect): {row.get('historical_resolution')}\n"
            
            return response
            
        except Exception as e:
            return f"Error querying tickets: {str(e)}"
    
    @tool
    def check_cancellation_eligibility(self, order_id: str) -> str:
        """
        Check if an order is eligible for free cancellation.
        
        Args:
            order_id: The order ID to check (e.g., "ORD-1001")
        """
        try:
            # Get order details
            orders_df = self.structured_data.get('orders', pd.DataFrame())
            order = orders_df[orders_df['order_id'] == order_id]
            
            if order.empty:
                return f"Order {order_id} not found."
            
            row = order.iloc[0]
            status = row.get('status', '')
            booked_at = row.get('booked_at', '')
            
            # Check cancellation eligibility
            if status == 'BOOKED':
                # Check if within 24 hours
                # Note: In production, you'd calculate from datetime
                return f"✅ Order {order_id} is BOOKED and may be eligible for free cancellation (within 24 hours)."
            elif status == 'PICKED_UP':
                return f"❌ Order {order_id} has been PICKED_UP and cannot be cancelled for free."
            elif status == 'DELIVERED':
                return f"❌ Order {order_id} has been DELIVERED and cannot be cancelled."
            else:
                return f"Order {order_id} status is {status}. Please check cancellation policy."
            
        except Exception as e:
            return f"Error checking cancellation: {str(e)}"
    
    @tool
    def escalate_ticket(self, ticket_id: str, reason: str = "Needs human review") -> str:
        """
        Create an escalation for a support ticket.
        THIS TOOL REQUIRES CONFIRMATION.
        
        Args:
            ticket_id: The ticket ID to escalate
            reason: Reason for escalation
        """
        if not self.current_user:
            return "Authentication required."
        
        # Create pending action
        action_data = {
            'action': 'escalation',
            'ticket_id': ticket_id,
            'reason': reason,
            'requested_by': self.current_user.user_id
        }
        
        # Store for confirmation
        self.action_tools.pending_action = action_data
        
        return f"⚠️ I'm preparing to escalate ticket {ticket_id}. Reason: {reason}\n\nPlease confirm if you want to proceed."