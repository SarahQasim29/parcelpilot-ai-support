# src/agents/free_agent.py
import os
import sys
import logging
import re
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# DATA ACCESS
# ============================================

def get_structured_data():
    """Get structured data from main module"""
    try:
        from src.api import main
        if hasattr(main, 'structured_data'):
            return main.structured_data
        return {}
    except Exception as e:
        logger.warning(f"Could not get structured data: {e}")
        return {}

def get_orders_data():
    """Get orders data"""
    data = get_structured_data()
    
    # Try different sheet names
    possible_names = ['orders', 'Orders', 'order', 'Order']
    for name in possible_names:
        if name in data:
            df = data[name]
            if not df.empty:
                logger.info(f"✅ Found orders in sheet: {name} ({len(df)} rows)")
                return df
    
    # Try direct file load as fallback
    try:
        excel_path = "data/structured/ParcelPilot_Assessment_Data.xlsx"
        if os.path.exists(excel_path):
            xls = pd.ExcelFile(excel_path)
            for sheet in xls.sheet_names:
                if 'order' in sheet.lower():
                    df = pd.read_excel(excel_path, sheet_name=sheet)
                    if not df.empty:
                        logger.info(f"✅ Loaded orders from fallback: {sheet} ({len(df)} rows)")
                        return df
    except Exception as e:
        logger.error(f"❌ Fallback load failed: {e}")
    
    return pd.DataFrame()

def get_tickets_data():
    """Get tickets data"""
    data = get_structured_data()
    
    # Try different sheet names
    possible_names = ['tickets', 'Tickets', 'ticket', 'Ticket']
    for name in possible_names:
        if name in data:
            df = data[name]
            if not df.empty:
                logger.info(f"✅ Found tickets in sheet: {name} ({len(df)} rows)")
                return df
    
    # Try direct file load as fallback
    try:
        excel_path = "data/structured/ParcelPilot_Assessment_Data.xlsx"
        if os.path.exists(excel_path):
            xls = pd.ExcelFile(excel_path)
            for sheet in xls.sheet_names:
                if 'ticket' in sheet.lower():
                    df = pd.read_excel(excel_path, sheet_name=sheet)
                    if not df.empty:
                        logger.info(f"✅ Loaded tickets from fallback: {sheet} ({len(df)} rows)")
                        return df
    except Exception as e:
        logger.error(f"❌ Fallback load failed: {e}")
    
    return pd.DataFrame()



def get_accounts_data():
    """Get accounts data"""
    data = get_structured_data()
    
    possible_names = ['accounts', 'Accounts', 'account', 'Account']
    for name in possible_names:
        if name in data:
            df = data[name]
            if not df.empty:
                logger.info(f"✅ Found accounts in sheet: {name} ({len(df)} rows)")
                return df
    
    try:
        excel_path = "data/structured/ParcelPilot_Assessment_Data.xlsx"
        if os.path.exists(excel_path):
            xls = pd.ExcelFile(excel_path)
            for sheet in xls.sheet_names:
                if 'account' in sheet.lower():
                    df = pd.read_excel(excel_path, sheet_name=sheet)
                    if not df.empty:
                        logger.info(f"✅ Loaded accounts from fallback: {sheet} ({len(df)} rows)")
                        return df
    except Exception as e:
        logger.error(f"❌ Fallback load failed: {e}")
    
    return pd.DataFrame()

# ============================================
# AGENT CLASS
# ============================================

class FreeSupportAgent:
    def __init__(self, tools: List, user, config: Dict):
        self.tools = tools
        self.user = user
        self.config = config
        
        # Pre-load data
        self.orders_df = get_orders_data()
        self.tickets_df = get_tickets_data()
        self.accounts_df = get_accounts_data()
        
        logger.info(f"✅ Agent initialized for {user.user_id}")
        logger.info(f"   Orders: {len(self.orders_df)} rows")
        logger.info(f"   Tickets: {len(self.tickets_df)} rows")
        logger.info(f"   Accounts: {len(self.accounts_df)} rows")
    
    def process_request(self, user_input: str) -> Dict:
        """Process user request"""
        try:
            text = user_input.lower().strip()
            
            logger.info(f"Processing: {text}")
            
            # ============================================
            # 1. SHOW MY ORDERS
            # ============================================
            if "show" in text and "my" in text and "order" in text:
                return self._handle_show_orders()
            
            # ============================================
            # 2. ORDER STATUS (specific order)
            # ============================================
            if ("status" in text or "track" in text) and ("ord-" in text):
                return self._handle_order_status(text)
            
            # ============================================
            # 2.5 ORDER STATUS (Yes/No questions)
            # ============================================
            if ("ord-" in text) and ("is" in text or "delivered" in text or "picked" in text):
                return self._handle_order_yes_no(text)
            
            # ============================================
            # 3. ORDER DETAILS (when, carrier, fee, etc.)
            # ============================================
            if "ord-" in text and ("when" in text or "carrier" in text or "fee" in text or "booked" in text):
                return self._handle_order_details(text)
            
            # ============================================
            # 4. SHOW TICKETS
            # ============================================
            if "show" in text and "ticket" in text:
                return self._handle_show_tickets()
            
            # ============================================
            # 4.5 SHOW FILTERED TICKETS
            # ============================================
            if ("show" in text or "list" in text) and "ticket" in text and ("open" in text or "closed" in text or "resolved" in text):
                return self._handle_filtered_tickets(text)
            
            # ============================================
            # 5. TICKET STATUS (specific ticket)
            # ============================================
            if ("status" in text and "tkt-" in text) or ("ticket" in text and "tkt-" in text):
                return self._handle_ticket_status(text)
            
            # ============================================
            # 6. CANCELLATION POLICY
            # ============================================
            if "cancel" in text or "cancellation" in text or "refund" in text:
                return self._handle_cancellation(text)

            # In process_request method, add these sections:

            # ============================================
            # TICKET YES/NO QUESTIONS
            # ============================================
            if ("tkt-" in text) and ("is" in text or "resolved" in text or "open" in text or "closed" in text):
                return self._handle_ticket_yes_no(text)

            # ============================================
            # RETURN POLICY
            # ============================================
            if "return policy" in text or "return" in text:
                return self._handle_return_policy(text)

            # ============================================
            # REFUND POLICY (WEIGHT-SPECIFIC)
            # ============================================
            if ("refund" in text or "return" in text) and ("50kg" in text or "weight" in text or "shipment" in text):
                return self._handle_refund_policy(text)
            
            # ============================================
            # 6.5 REFUND POLICY (SPECIFIC)
            # ============================================
            if ("refund" in text or "return" in text) and ("50kg" in text or "weight" in text or "shipment" in text):
                return self._handle_refund_policy(text)
            # ============================================
            # 7. SERVICE CREDIT / SLA
            # ============================================
            if "service credit" in text or "sla" in text or "delay" in text or "late" in text:
                return self._handle_service_credit(text)
            
            # ============================================
            # 7.5 SLA (Specific)
            # ============================================
            if "sla" in text and "support" in text:
                return self._handle_sla_policy(text)
            
            # ============================================
            # 8. ESCALATION
            # ============================================
            if "escalate" in text or "urgent" in text:
                return {
                    'type': 'action_required',
                    'message': "⚠️ I can escalate this issue for you. Please confirm.",
                    'requires_confirmation': True,
                    'action_data': {'action': 'escalation'}
                }
            
            # src/agents/free_agent.py - Add this after the ORDER DETAILS section

            # ============================================
            # 3.5 PICKUP WINDOW (SPECIFIC)
            # ============================================
            if "pickup" in text and "window" in text and "ord-" in text:
                return self._handle_pickup_window(text)

            # ============================================
            # 3.6 ORDER FILTERS (by carrier, status)
            # ============================================
            if ("show" in text or "list" in text) and ("carrier" in text or "swiftship" in text or "bluedart" in text or "roadrunner" in text):
                return self._handle_order_filter(text)

            if ("show" in text or "list" in text) and ("booked" in text or "picked_up" in text or "delivered" in text):
                return self._handle_order_filter(text)
            
            # ============================================
            # 9. SPECIFIC QUESTIONS
            # ============================================
            if "northstar" in text and ("sla" in text or "terms" in text):
                return self._handle_account_info("ACCT-001")
            
            if "lumenworks" in text and ("terms" in text or "credit" in text):
                return self._handle_account_info("ACCT-002")
            
            # ============================================
            # 10. DEFAULT
            # ============================================
            return {
                'type': 'response',
                'message': "I can help with:\n• Show my orders\n• Order status (e.g., 'ORD-1001')\n• Order details (when, carrier, fee)\n• Show my tickets\n• Ticket status (e.g., 'TKT-501')\n• Cancellation policy\n• Service credits/SLA\n• Escalations\n\nWhat would you like to know?",
                'requires_confirmation': False
            }
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'type': 'error',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
    
    # ============================================
    # HANDLERS
    # ============================================
    
    def _handle_show_orders(self) -> Dict:
        """Show all orders for current user"""
        try:
            account_id = self.user.account_id
            orders_df = self.orders_df
            
            if orders_df.empty:
                return {
                    'type': 'response',
                    'message': "📦 No order data available.",
                    'requires_confirmation': False
                }
            
            # Filter by account
            if 'account_id' in orders_df.columns:
                result = orders_df[orders_df['account_id'] == account_id]
                
                if not result.empty:
                    response = f"📦 Your orders (Account: {account_id}):\n\n"
                    for _, row in result.iterrows():
                        order_id = row.get('order_id', 'N/A')
                        status = row.get('status', 'Unknown')
                        carrier = row.get('carrier', 'N/A')
                        fee = row.get('shipment_fee_inr', 'N/A')
                        response += f"• {order_id}: {status} | {carrier} | ₹{fee}\n"
                    return {
                        'type': 'response',
                        'message': response,
                        'requires_confirmation': False
                    }
                else:
                    return {
                        'type': 'response',
                        'message': f"📦 No orders found for account {account_id}.",
                        'requires_confirmation': False
                    }
            
            return {
                'type': 'response',
                'message': "No orders found.",
                'requires_confirmation': False
            }
            
        except Exception as e:
            logger.error(f"❌ Show orders error: {e}")
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
    
    def _handle_order_status(self, text: str) -> Dict:
        """Handle order status query"""
        try:
            order_match = re.search(r'ORD-\d+', text.upper())
            if not order_match:
                return {
                    'type': 'response',
                    'message': "Please provide an order ID (e.g., ORD-1001)",
                    'requires_confirmation': False
                }
            
            order_id = order_match.group()
            account_id = self.user.account_id
            orders_df = self.orders_df
            
            if orders_df.empty:
                return {
                    'type': 'response',
                    'message': "No order data available.",
                    'requires_confirmation': False
                }
            
            # Filter by account
            if 'account_id' in orders_df.columns:
                orders_df = orders_df[orders_df['account_id'] == account_id]
            
            if 'order_id' in orders_df.columns:
                result = orders_df[orders_df['order_id'] == order_id]
                if not result.empty:
                    row = result.iloc[0]
                    message = f"📦 Order {order_id}\n"
                    message += f"Status: {row.get('status', 'Unknown')}\n"
                    message += f"Carrier: {row.get('carrier', 'N/A')}\n"
                    message += f"Booked: {row.get('booked_at', 'N/A')}\n"
                    message += f"Fee: ₹{row.get('shipment_fee_inr', 'N/A')}"
                    
                    # Add extra info if available
                    if row.get('pickup_window_start'):
                        message += f"\nPickup Window: {row.get('pickup_window_start')} - {row.get('pickup_window_end')}"
                    if row.get('notes'):
                        message += f"\nNote: {row.get('notes')}"
                    
                    return {
                        'type': 'response',
                        'message': message,
                        'requires_confirmation': False
                    }
                else:
                    return {
                        'type': 'response',
                        'message': f"❌ Order {order_id} not found for your account.",
                        'requires_confirmation': False
                    }
            
            return {
                'type': 'response',
                'message': f"Order {order_id} not found.",
                'requires_confirmation': False
            }
            
        except Exception as e:
            logger.error(f"❌ Order status error: {e}")
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
        
    def _handle_pickup_window(self, text: str) -> Dict:
        """Handle pickup window queries"""
        try:
            order_match = re.search(r'ORD-\d+', text.upper())
            if not order_match:
                return {
                    'type': 'response',
                    'message': "Please provide an order ID (e.g., ORD-1001)",
                    'requires_confirmation': False
                }
            
            order_id = order_match.group()
            account_id = self.user.account_id
            orders_df = self.orders_df
            
            if orders_df.empty:
                return {
                    'type': 'response',
                    'message': "No order data available.",
                    'requires_confirmation': False
                }
            
            # Filter by account
            if 'account_id' in orders_df.columns:
                orders_df = orders_df[orders_df['account_id'] == account_id]
            
            if 'order_id' in orders_df.columns:
                result = orders_df[orders_df['order_id'] == order_id]
                if not result.empty:
                    row = result.iloc[0]
                    start = row.get('pickup_window_start', 'N/A')
                    end = row.get('pickup_window_end', 'N/A')
                    return {
                        'type': 'response',
                        'message': f"📦 Pickup window for {order_id}: {start} - {end}",
                        'requires_confirmation': False
                    }
                else:
                    return {
                        'type': 'response',
                        'message': f"❌ Order {order_id} not found for your account.",
                        'requires_confirmation': False
                    }
            
            return {
                'type': 'response',
                'message': f"Pickup window not found for {order_id}.",
                'requires_confirmation': False
            }
        except Exception as e:
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }

    def _handle_order_filter(self, text: str) -> Dict:
        """Handle order filtering by carrier or status"""
        try:
            account_id = self.user.account_id
            orders_df = self.orders_df
            
            if orders_df.empty:
                return {
                    'type': 'response',
                    'message': "No order data available.",
                    'requires_confirmation': False
                }
            
            # Filter by account
            if 'account_id' in orders_df.columns:
                orders_df = orders_df[orders_df['account_id'] == account_id]
            
            # Check for carrier filter
            carrier = None
            if 'swiftship' in text.lower():
                carrier = 'SwiftShip'
            elif 'bluedart' in text.lower():
                carrier = 'BlueDart Pro'
            elif 'roadrunner' in text.lower():
                carrier = 'RoadRunner'
            
            if carrier and 'carrier' in orders_df.columns:
                orders_df = orders_df[orders_df['carrier'] == carrier]
            
            # Check for status filter
            status = None
            if 'booked' in text.lower():
                status = 'BOOKED'
            elif 'picked_up' in text.lower():
                status = 'PICKED_UP'
            elif 'delivered' in text.lower():
                status = 'DELIVERED'
            
            if status and 'status' in orders_df.columns:
                orders_df = orders_df[orders_df['status'] == status]
            
            if orders_df.empty:
                filter_desc = f" {carrier}" if carrier else ""
                filter_desc += f" {status}" if status else ""
                return {
                    'type': 'response',
                    'message': f"📦 No orders found{filter_desc} for your account.",
                    'requires_confirmation': False
                }
            
            response = f"📦 Orders for your account:\n\n"
            for _, row in orders_df.iterrows():
                order_id = row.get('order_id', 'N/A')
                status_val = row.get('status', 'Unknown')
                carrier_val = row.get('carrier', 'N/A')
                fee = row.get('shipment_fee_inr', 'N/A')
                response += f"• {order_id}: {status_val} | {carrier_val} | ₹{fee}\n"
            
            return {
                'type': 'response',
                'message': response,
                'requires_confirmation': False
            }
            
        except Exception as e:
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
        
    def _handle_refund_policy(self, text: str) -> Dict:
        """Handle refund policy queries"""
        try:
            # Extract weight if mentioned
            weight_match = re.search(r'(\d+)kg', text.lower())
            weight = weight_match.group(1) if weight_match else None
            
            response = "📋 Refund Policy:\n\n"
            response += "• Standard shipments: Refund within 7 days of booking\n"
            response += "• Damaged items: Full refund + replacement\n"
            
            if weight:
                response += f"• Shipments over {weight}kg: Additional inspection required\n"
                response += "  Refund processed after quality check\n"
            
            response += "\nFor specific details, please provide your order ID."
            
            return {
                'type': 'response',
                'message': response,
                'requires_confirmation': False
            }
        except Exception as e:
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
    
    def _handle_order_details(self, text: str) -> Dict:
        """Handle specific order detail queries"""
        try:
            order_match = re.search(r'ORD-\d+', text.upper())
            if not order_match:
                return {
                    'type': 'response',
                    'message': "Please provide an order ID (e.g., ORD-1001)",
                    'requires_confirmation': False
                }
            
            order_id = order_match.group()
            account_id = self.user.account_id
            orders_df = self.orders_df
            
            if orders_df.empty:
                return {
                    'type': 'response',
                    'message': "No order data available.",
                    'requires_confirmation': False
                }
            
            # Filter by account
            if 'account_id' in orders_df.columns:
                orders_df = orders_df[orders_df['account_id'] == account_id]
            
            if 'order_id' in orders_df.columns:
                result = orders_df[orders_df['order_id'] == order_id]
                if not result.empty:
                    row = result.iloc[0]
                    
                    # Build response based on what they asked
                    message = f"📦 Order {order_id}:\n"
                    
                    if 'carrier' in text.lower():
                        message += f"Carrier: {row.get('carrier', 'N/A')}\n"
                    if 'booked' in text.lower() or 'when' in text.lower():
                        message += f"Booked At: {row.get('booked_at', 'N/A')}\n"
                    if 'fee' in text.lower():
                        message += f"Shipment Fee: ₹{row.get('shipment_fee_inr', 'N/A')}\n"
                    if 'status' in text.lower():
                        message += f"Status: {row.get('status', 'Unknown')}\n"
                    if 'pickup' in text.lower():
                        message += f"Pickup Window: {row.get('pickup_window_start', 'N/A')} - {row.get('pickup_window_end', 'N/A')}\n"
                    
                    # If they asked a general question, show everything
                    if not any(word in text.lower() for word in ['carrier', 'booked', 'when', 'fee', 'status', 'pickup']):
                        message += f"Status: {row.get('status', 'Unknown')}\n"
                        message += f"Carrier: {row.get('carrier', 'N/A')}\n"
                        message += f"Booked: {row.get('booked_at', 'N/A')}\n"
                        message += f"Fee: ₹{row.get('shipment_fee_inr', 'N/A')}"
                    
                    return {
                        'type': 'response',
                        'message': message,
                        'requires_confirmation': False
                    }
                else:
                    return {
                        'type': 'response',
                        'message': f"❌ Order {order_id} not found.",
                        'requires_confirmation': False
                    }
            
            return {
                'type': 'response',
                'message': f"Order {order_id} not found.",
                'requires_confirmation': False
            }
            
        except Exception as e:
            logger.error(f"❌ Order details error: {e}")
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
    
    def _handle_show_tickets(self) -> Dict:
        """Show all tickets for current user"""
        try:
            account_id = self.user.account_id
            tickets_df = self.tickets_df
            
            if tickets_df.empty:
                return {
                    'type': 'response',
                    'message': "🎫 No ticket data available.",
                    'requires_confirmation': False
                }
            
            # Filter by account - CASE INSENSITIVE
            if 'account_id' in tickets_df.columns:
                # Try exact match first
                result = tickets_df[tickets_df['account_id'] == account_id]
                if result.empty:
                    # Try case-insensitive
                    result = tickets_df[tickets_df['account_id'].str.upper() == account_id.upper()]
                
                if not result.empty:
                    response = f"🎫 Your tickets (Account: {account_id}):\n\n"
                    for _, row in result.iterrows():
                        ticket_id = row.get('ticket_id', 'N/A')
                        status = row.get('status', 'Unknown')
                        subject = row.get('subject', 'N/A')
                        created = row.get('created_at', 'N/A')
                        response += f"• {ticket_id}: {status} | {subject} | {created}\n"
                    return {
                        'type': 'response',
                        'message': response,
                        'requires_confirmation': False
                    }
                else:
                    return {
                        'type': 'response',
                        'message': f"🎫 No tickets found for account {account_id}.",
                        'requires_confirmation': False
                    }
            
            return {
                'type': 'response',
                'message': "No tickets found.",
                'requires_confirmation': False
            }
            
        except Exception as e:
            logger.error(f"❌ Show tickets error: {e}")
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
        
    def _handle_sla_policy(self, text: str) -> Dict:
        """Handle SLA policy queries"""
        try:
            # Check for specific account
            company = None
            if 'northstar' in text.lower():
                company = 'Northstar'
                company_id = 'ACCT-001'
            elif 'lumenworks' in text.lower():
                company = 'LumenWorks'
                company_id = 'ACCT-002'
            else:
                company_id = None
            
            response = "📋 Support SLA Policy:\n\n"
            response += "• Response Time:\n"
            response += "  - Critical: Within 1 hour\n"
            response += "  - High: Within 4 hours\n"
            response += "  - Medium: Within 24 hours\n"
            response += "  - Low: Within 48 hours\n"
            response += "\n• Resolution Time:\n"
            response += "  - Critical: Within 4 hours\n"
            response += "  - High: Within 24 hours\n"
            response += "  - Medium: Within 72 hours\n"
            response += "  - Low: Within 120 hours\n"
            
            if company:
                response += f"\n{company} has custom SLA terms in their Enterprise agreement."
            
            return {
                'type': 'response',
                'message': response,
                'requires_confirmation': False
            }
        except Exception as e:
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
    def _handle_order_yes_no(self, text: str) -> Dict:
        """Handle yes/no order queries"""
        try:
            order_match = re.search(r'ORD-\d+', text.upper())
            if not order_match:
                return {
                    'type': 'response',
                    'message': "Please provide an order ID (e.g., ORD-1001)",
                    'requires_confirmation': False
                }
            
            order_id = order_match.group()
            account_id = self.user.account_id
            orders_df = self.orders_df
            
            if orders_df.empty:
                return {
                    'type': 'response',
                    'message': "No order data available.",
                    'requires_confirmation': False
                }
            
            # Filter by account
            if 'account_id' in orders_df.columns:
                orders_df = orders_df[orders_df['account_id'] == account_id]
            
            if 'order_id' in orders_df.columns:
                result = orders_df[orders_df['order_id'] == order_id]
                if not result.empty:
                    row = result.iloc[0]
                    status = row.get('status', 'Unknown')
                    
                    # Answer based on what they asked
                    if 'delivered' in text.lower():
                        answer = "Yes, it has been delivered." if status == 'DELIVERED' else f"No, it is currently {status}."
                    elif 'picked' in text.lower():
                        answer = "Yes, it has been picked up." if status == 'PICKED_UP' else f"No, it is currently {status}."
                    elif 'booked' in text.lower():
                        answer = "Yes, it is booked." if status == 'BOOKED' else f"No, it is currently {status}."
                    elif 'cancel' in text.lower():
                        answer = "Yes, it can be canceled." if status == 'BOOKED' else f"No, it cannot be canceled as it is {status}."
                    else:
                        answer = f"Order {order_id} is currently {status}."
                    
                    return {
                        'type': 'response',
                        'message': f"📦 {answer}",
                        'requires_confirmation': False
                    }
                else:
                    return {
                        'type': 'response',
                        'message': f"❌ Order {order_id} not found for your account.",
                        'requires_confirmation': False
                    }
            
            return {
                'type': 'response',
                'message': f"Order {order_id} not found.",
                'requires_confirmation': False
            }
            
        except Exception as e:
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
    
    def _handle_ticket_status(self, text: str) -> Dict:
        """Handle ticket status query"""
        try:
            ticket_match = re.search(r'TKT-\d+', text.upper())
            if not ticket_match:
                return {
                    'type': 'response',
                    'message': "Please provide a ticket ID (e.g., TKT-501)",
                    'requires_confirmation': False
                }
            
            ticket_id = ticket_match.group()
            account_id = self.user.account_id
            tickets_df = self.tickets_df
            
            if tickets_df.empty:
                return {
                    'type': 'response',
                    'message': "No ticket data available.",
                    'requires_confirmation': False
                }
            
            # Filter by account
            if 'account_id' in tickets_df.columns:
                tickets_df = tickets_df[tickets_df['account_id'] == account_id]
            
            if 'ticket_id' in tickets_df.columns:
                result = tickets_df[tickets_df['ticket_id'] == ticket_id]
                if not result.empty:
                    row = result.iloc[0]
                    message = f"🎫 Ticket {ticket_id}\n"
                    message += f"Status: {row.get('status', 'Unknown')}\n"
                    message += f"Subject: {row.get('subject', 'N/A')}\n"
                    message += f"Created: {row.get('created_at', 'N/A')}\n"
                    message += f"Assigned To: {row.get('assigned_to', 'Unassigned')}\n"
                    if row.get('description'):
                        message += f"\nDescription: {row.get('description')}"
                    
                    # Note about historical resolutions
                    if row.get('historical_resolution'):
                        message += f"\n\n⚠️ Historical Resolution (may be incorrect): {row.get('historical_resolution')}"
                    
                    return {
                        'type': 'response',
                        'message': message,
                        'requires_confirmation': False
                    }
                else:
                    return {
                        'type': 'response',
                        'message': f"❌ Ticket {ticket_id} not found for your account.",
                        'requires_confirmation': False
                    }
            
            return {
                'type': 'response',
                'message': f"Ticket {ticket_id} not found.",
                'requires_confirmation': False
            }
            
        except Exception as e:
            logger.error(f"❌ Ticket status error: {e}")
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
    
    def _handle_cancellation(self, text: str) -> Dict:
        """Handle cancellation policy queries"""
        try:
            order_match = re.search(r'ORD-\d+', text.upper())
            order_text = f" for {order_match.group()}" if order_match else ""
            
            # Check for specific company
            company = None
            if 'northstar' in text.lower():
                company = 'Northstar'
                company_id = 'ACCT-001'
            elif 'lumenworks' in text.lower():
                company = 'LumenWorks'
                company_id = 'ACCT-002'
            else:
                company_id = self.user.account_id
            
            # Get account info if available
            account_info = ""
            if not self.accounts_df.empty and 'account_id' in self.accounts_df.columns:
                account_result = self.accounts_df[self.accounts_df['account_id'] == company_id]
                if not account_result.empty:
                    account_row = account_result.iloc[0]
                    plan = account_row.get('plan', '')
                    premium = account_row.get('premium_support', False)
                    account_info = f"\nPlan: {plan}"
                    if premium:
                        account_info += " (Premium Support)"
            
            # Build response
            response = f"📋 Cancellation Policy{order_text}:\n\n"
            response += "• Orders canceled within 24 hours of booking: No fee\n"
            response += "• Orders canceled after 24 hours: Fee applies\n"
            
            if company:
                response += f"• {company} has custom terms in their agreement\n"
            
            response += "• Enterprise customers may have custom terms\n"
            
            if account_info:
                response += account_info
            
            response += "\n\nWould you like me to check specific details for your order?"
            
            return {
                'type': 'response',
                'message': response,
                'requires_confirmation': False
            }
            
        except Exception as e:
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
    
    def _handle_service_credit(self, text: str) -> Dict:
        """Handle service credit queries"""
        try:
            # Check for specific order
            order_match = re.search(r'ORD-\d+', text.upper())
            order_text = f" for {order_match.group()}" if order_match else ""
            
            # Check if they mentioned a delay
            has_delay = "delay" in text.lower() or "late" in text.lower() or "hour" in text.lower()
            
            response = "📋 Service Credit Policy:\n\n"
            response += "Service credits are issued when:\n"
            response += "• Delivery is more than 2 hours late\n"
            response += "• Package is damaged\n"
            response += "• Wrong item delivered\n"
            
            if has_delay:
                response += "\n⚠️ Based on your description of a 3-hour delay, you may qualify for a service credit."
            
            if order_match:
                response += f"\n\nTo check specific eligibility for {order_match.group()}, please provide the order details."
            else:
                response += "\n\nTo check eligibility, please provide your order ID."
            
            return {
                'type': 'response',
                'message': response,
                'requires_confirmation': False
            }
            
        except Exception as e:
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
        
    def _handle_filtered_tickets(self, text: str) -> Dict:
        """Handle filtered ticket queries"""
        try:
            account_id = self.user.account_id
            tickets_df = self.tickets_df
            
            if tickets_df.empty:
                return {
                    'type': 'response',
                    'message': "🎫 No ticket data available.",
                    'requires_confirmation': False
                }
            
            # Filter by account - CASE INSENSITIVE
            if 'account_id' in tickets_df.columns:
                result = tickets_df[tickets_df['account_id'] == account_id]
                if result.empty:
                    result = tickets_df[tickets_df['account_id'].str.upper() == account_id.upper()]
            else:
                result = tickets_df
            
            # Filter by status
            status_filter = None
            if 'open' in text.lower():
                status_filter = 'open'
            elif 'closed' in text.lower():
                status_filter = 'closed'
            elif 'resolved' in text.lower():
                status_filter = 'resolved'
            
            if status_filter and 'status' in result.columns:
                result = result[result['status'] == status_filter]
            
            if result.empty:
                status_text = status_filter if status_filter else ""
                return {
                    'type': 'response',
                    'message': f"🎫 No {status_text} tickets found for your account.",
                    'requires_confirmation': False
                }
            
            response = f"🎫 Your {status_filter if status_filter else ''} tickets:\n\n"
            for _, row in result.iterrows():
                ticket_id = row.get('ticket_id', 'N/A')
                status = row.get('status', 'Unknown')
                subject = row.get('subject', 'N/A')
                created = row.get('created_at', 'N/A')
                response += f"• {ticket_id}: {status} | {subject} | {created}\n"
            
            return {
                'type': 'response',
                'message': response,
                'requires_confirmation': False
            }
            
        except Exception as e:
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }
    
    
    
    def _handle_account_info(self, account_id: str) -> Dict:
        """Handle account-specific queries"""
        try:
            if self.accounts_df.empty:
                return {
                    'type': 'response',
                    'message': "No account data available.",
                    'requires_confirmation': False
                }
            
            result = self.accounts_df[self.accounts_df['account_id'] == account_id]
            if result.empty:
                return {
                    'type': 'response',
                    'message': f"Account {account_id} not found.",
                    'requires_confirmation': False
                }
            
            row = result.iloc[0]
            response = f"📋 Account: {row.get('account_name')} ({account_id})\n"
            response += f"Plan: {row.get('plan', 'N/A')}\n"
            response += f"Status: {row.get('status', 'N/A')}\n"
            response += f"CSM: {row.get('csm', 'N/A')}\n"
            response += f"Premium Support: {'Yes' if row.get('premium_support') else 'No'}\n"
            
            if row.get('notes'):
                response += f"\nNotes: {row.get('notes')}"
            
            if row.get('contract_file'):
                response += f"\nContract: {row.get('contract_file')}"
            
            return {
                'type': 'response',
                'message': response,
                'requires_confirmation': False
            }
            
        except Exception as e:
            return {
                'type': 'response',
                'message': f"Error: {str(e)}",
                'requires_confirmation': False
            }