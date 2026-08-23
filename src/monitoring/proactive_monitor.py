# src/monitoring/proactive_monitor.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class Alert:
    type: str
    severity: str
    description: str
    affected_accounts: List[str]
    tickets: List[str]
    timestamp: datetime
    recommendation: str
    metadata: Dict = None

class ProactiveMonitor:
    def __init__(self, structured_data: Dict[str, pd.DataFrame]):
        self.data = structured_data
        self.alerts = []
        self.last_analysis = None
    
    def analyze_support_patterns(self) -> List[Dict]:
        """Analyze support data for patterns and issues"""
        alerts = []
        
        tickets = self.data.get('Tickets', pd.DataFrame())
        orders = self.data.get('Orders', pd.DataFrame())
        
        if tickets.empty:
            logger.warning("No ticket data available for analysis")
            return []
        
        # 1. Detect complaint surges
        complaint_alerts = self._detect_complaint_surges(tickets)
        alerts.extend(complaint_alerts)
        
        # 2. Detect SLA violations
        sla_alerts = self._detect_sla_violations(tickets)
        alerts.extend(sla_alerts)
        
        # 3. Find recurring issues
        recurring_alerts = self._find_recurring_issues(tickets)
        alerts.extend(recurring_alerts)
        
        # 4. High-impact customer issues
        impact_alerts = self._detect_high_impact_issues(tickets, orders)
        alerts.extend(impact_alerts)
        
        self.alerts = alerts
        self.last_analysis = datetime.now()
        
        return [asdict(alert) for alert in alerts]
    
    def _detect_complaint_surges(self, tickets: pd.DataFrame, 
                                 window_hours: int = 24, 
                                 threshold: int = 3) -> List[Alert]:
        """Detect sudden increase in complaints"""
        alerts = []
        
        try:
            tickets['created_at'] = pd.to_datetime(tickets['created_at'])
            now = datetime.now()
            cutoff = now - timedelta(hours=window_hours)
            
            recent = tickets[tickets['created_at'] > cutoff]
            
            if recent.empty:
                return alerts
            
            complaint_counts = recent.groupby('category').size()
            
            for category, count in complaint_counts.items():
                if count >= threshold:
                    affected = recent[recent['category'] == category]
                    
                    alerts.append(Alert(
                        type="complaint_surge",
                        severity="high",
                        description=f"Surge in '{category}' complaints: {count} in last {window_hours} hours",
                        affected_accounts=affected['account_id'].unique().tolist(),
                        tickets=affected['ticket_id'].tolist(),
                        timestamp=datetime.now(),
                        recommendation=f"Investigate '{category}' issues and consider proactive outreach",
                        metadata={
                            'category': category,
                            'count': count,
                            'window_hours': window_hours
                        }
                    ))
            
        except Exception as e:
            logger.error(f"Error detecting complaint surges: {str(e)}")
        
        return alerts
    
    def _detect_sla_violations(self, tickets: pd.DataFrame) -> List[Alert]:
        """Detect tickets approaching or exceeding SLA"""
        alerts = []
        
        try:
            tickets['created_at'] = pd.to_datetime(tickets['created_at'])
            now = datetime.now()
            
            sla_hours = {
                'high': 4,
                'medium': 24,
                'low': 48
            }
            
            for _, ticket in tickets.iterrows():
                created = ticket['created_at']
                priority = ticket.get('priority', 'medium').lower()
                
                sla = sla_hours.get(priority, 24)
                elapsed = (now - created).total_seconds() / 3600
                
                if elapsed > sla:
                    alerts.append(Alert(
                        type="sla_breach",
                        severity="critical",
                        description=f"SLA breached for ticket {ticket.get('ticket_id', 'Unknown')}",
                        affected_accounts=[ticket.get('account_id', 'Unknown')],
                        tickets=[ticket.get('ticket_id', 'Unknown')],
                        timestamp=now,
                        recommendation=f"Urgent escalation required for ticket {ticket.get('ticket_id', 'Unknown')}",
                        metadata={
                            'priority': priority,
                            'sla_hours': sla,
                            'elapsed_hours': elapsed
                        }
                    ))
                elif elapsed > sla * 0.8:
                    alerts.append(Alert(
                        type="sla_warning",
                        severity="medium",
                        description=f"SLA approaching for ticket {ticket.get('ticket_id', 'Unknown')}",
                        affected_accounts=[ticket.get('account_id', 'Unknown')],
                        tickets=[ticket.get('ticket_id', 'Unknown')],
                        timestamp=now,
                        recommendation=f"Prioritize ticket {ticket.get('ticket_id', 'Unknown')}",
                        metadata={
                            'priority': priority,
                            'sla_hours': sla,
                            'elapsed_hours': elapsed
                        }
                    ))
            
        except Exception as e:
            logger.error(f"Error detecting SLA violations: {str(e)}")
        
        return alerts
    
    def _find_recurring_issues(self, tickets: pd.DataFrame, 
                               threshold: int = 3) -> List[Alert]:
        """Find issues affecting multiple customers"""
        alerts = []
        
        try:
            issue_groups = tickets.groupby('category')['ticket_id'].count()
            
            for category, count in issue_groups.items():
                if count >= threshold:
                    affected = tickets[tickets['category'] == category]
                    affected_accounts = affected['account_id'].unique().tolist()
                    
                    alerts.append(Alert(
                        type="recurring_issue",
                        severity="medium",
                        description=f"'{category}' affecting {len(affected_accounts)} customers ({count} tickets)",
                        affected_accounts=affected_accounts,
                        tickets=affected['ticket_id'].tolist(),
                        timestamp=datetime.now(),
                        recommendation=f"Investigate '{category}' for potential systemic issue",
                        metadata={
                            'category': category,
                            'ticket_count': count,
                            'customer_count': len(affected_accounts)
                        }
                    ))
            
        except Exception as e:
            logger.error(f"Error finding recurring issues: {str(e)}")
        
        return alerts
    
    def _detect_high_impact_issues(self, tickets: pd.DataFrame, 
                                   orders: pd.DataFrame) -> List[Alert]:
        """Detect issues affecting high-value or high-volume customers"""
        alerts = []
        
        try:
            if orders.empty:
                return alerts
            
            # Calculate order volume per account
            order_volume = orders.groupby('account_id').size().reset_index()
            order_volume.columns = ['account_id', 'order_count']
            
            # Merge with ticket data
            ticket_volume = tickets.groupby('account_id').size().reset_index()
            ticket_volume.columns = ['account_id', 'ticket_count']
            
            merged = pd.merge(order_volume, ticket_volume, on='account_id', how='inner')
            
            # Identify high-volume customers (top 20%)
            threshold = merged['order_count'].quantile(0.8)
            high_volume = merged[merged['order_count'] > threshold]
            
            for _, customer in high_volume.iterrows():
                account_id = customer['account_id']
                ticket_count = customer['ticket_count']
                
                if ticket_count > 2:  # More than 2 tickets for high-volume customer
                    customer_tickets = tickets[tickets['account_id'] == account_id]
                    
                    alerts.append(Alert(
                        type="high_impact_issue",
                        severity="high",
                        description=f"High-volume customer {account_id} has {ticket_count} open tickets",
                        affected_accounts=[account_id],
                        tickets=customer_tickets['ticket_id'].tolist(),
                        timestamp=datetime.now(),
                        recommendation=f"Proactively reach out to {account_id}",
                        metadata={
                            'account_id': account_id,
                            'ticket_count': ticket_count,
                            'order_count': customer['order_count']
                        }
                    ))
            
        except Exception as e:
            logger.error(f"Error detecting high-impact issues: {str(e)}")
        
        return alerts
    
    def generate_summary(self) -> Dict:
        """Generate summary of current alerts"""
        if not self.alerts:
            return {
                'total_alerts': 0,
                'summary': 'No issues detected',
                'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None
            }
        
        alert_counts = {}
        for alert in self.alerts:
            alert_counts[alert.type] = alert_counts.get(alert.type, 0) + 1
        
        return {
            'total_alerts': len(self.alerts),
            'alert_counts': alert_counts,
            'critical_alerts': len([a for a in self.alerts if a.severity == 'critical']),
            'high_severity': len([a for a in self.alerts if a.severity == 'high']),
            'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None,
            'alerts': [asdict(alert) for alert in self.alerts]
        }