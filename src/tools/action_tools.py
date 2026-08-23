# src/tools/action_tools.py
from typing import Dict, Any, Optional
from datetime import datetime
from langchain.tools import tool
from src.auth.auth_manager import User
import logging
import json
import uuid
from langchain.tools import tool

logger = logging.getLogger(__name__)

class ActionTools:
    def __init__(self):
        self.pending_action = None 
        #self.pending_actions = {}
        self.executed_actions = []
        self.current_user = None
    
    def set_user(self, user: User):
        """Set current user for access control"""
        self.current_user = user
    
    def create_pending_action(self, action_type: str, data: Dict) -> Dict:
        """Create a pending action that requires confirmation"""
        action_id = str(uuid.uuid4())
        pending_action = {
            'action_id': action_id,
            'type': action_type,
            'data': data,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'user_id': self.current_user.user_id if self.current_user else 'unknown'
        }
        
        self.pending_actions[action_id] = pending_action
        return pending_action
    
    @tool
    def create_escalation(self, ticket_id: str, reason: str, 
                          priority: str = 'high', 
                          assigned_to: str = 'support_team') -> str:
        """
        Create an escalation for a support ticket.
        This action requires explicit user confirmation before execution.
        
        Args:
            ticket_id: The ticket ID to escalate
            reason: Reason for escalation
            priority: Priority level (high, medium, low)
            assigned_to: Team or person to assign to
        """
        if not self.current_user:
            return "Authentication required. Please log in."
        
        # Check if user can perform this action
        if not self.current_user.has_permission('create_escalation'):
            return "You don't have permission to create escalations."
        
        # Create pending action
        action_data = {
            'ticket_id': ticket_id,
            'reason': reason,
            'priority': priority,
            'assigned_to': assigned_to,
            'requested_by': self.current_user.user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        pending_action = self.create_pending_action('escalation', action_data)
        
        return json.dumps({
            'status': 'pending_confirmation',
            'action_id': pending_action['action_id'],
            'message': f"Please confirm escalation of ticket {ticket_id}",
            'details': action_data
        })
    
    @tool
    def update_ticket(self, ticket_id: str, status: str = None, 
                      priority: str = None, assignee: str = None) -> str:
        """
        Update a support ticket's status, priority, or assignment.
        This action requires explicit user confirmation before execution.
        
        Args:
            ticket_id: The ticket ID to update
            status: New status (open, in_progress, resolved, closed)
            priority: New priority (high, medium, low)
            assignee: New assignee
        """
        if not self.current_user:
            return "Authentication required. Please log in."
        
        # Check if user can perform this action
        if not self.current_user.has_permission('update_ticket'):
            return "You don't have permission to update tickets."
        
        update_data = {}
        if status:
            update_data['status'] = status
        if priority:
            update_data['priority'] = priority
        if assignee:
            update_data['assignee'] = assignee
        
        if not update_data:
            return "No updates specified."
        
        # Create pending action
        action_data = {
            'ticket_id': ticket_id,
            'updates': update_data,
            'requested_by': self.current_user.user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        pending_action = self.create_pending_action('update_ticket', action_data)
        
        return json.dumps({
            'status': 'pending_confirmation',
            'action_id': pending_action['action_id'],
            'message': f"Please confirm updating ticket {ticket_id}",
            'details': action_data
        })
    
    @tool
    def create_followup_task(self, description: str, due_date: str,
                            assigned_to: str = 'support_team') -> str:
        """
        Create a follow-up task for the support team.
        This action requires explicit user confirmation before execution.
        
        Args:
            description: Task description
            due_date: Due date in YYYY-MM-DD format
            assigned_to: Team or person assigned to task
        """
        if not self.current_user:
            return "Authentication required. Please log in."
        
        # Validate due date
        try:
            datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD."
        
        # Create pending action
        action_data = {
            'description': description,
            'due_date': due_date,
            'assigned_to': assigned_to,
            'created_by': self.current_user.user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        pending_action = self.create_pending_action('create_task', action_data)
        
        return json.dumps({
            'status': 'pending_confirmation',
            'action_id': pending_action['action_id'],
            'message': "Please confirm creating follow-up task",
            'details': action_data
        })
    
    def confirm_action(self, action_id: str) -> Dict:
        """Confirm and execute a pending action"""
        if action_id not in self.pending_actions:
            return {
                'status': 'error',
                'message': 'Action not found or already processed'
            }
        
        pending_action = self.pending_actions[action_id]
        
        if pending_action['status'] != 'pending':
            return {
                'status': 'error',
                'message': f"Action already {pending_action['status']}"
            }
        
        # Execute the action
        action_type = pending_action['type']
        data = pending_action['data']
        
        try:
            if action_type == 'escalation':
                result = self._execute_escalation(data)
            elif action_type == 'update_ticket':
                result = self._execute_ticket_update(data)
            elif action_type == 'create_task':
                result = self._execute_task_creation(data)
            else:
                result = {'status': 'error', 'message': f'Unknown action type: {action_type}'}
            
            # Update pending action status
            pending_action['status'] = 'completed'
            pending_action['result'] = result
            
            self.executed_actions.append(pending_action)
            
            return {
                'status': 'success',
                'message': f"Action {action_type} executed successfully",
                'result': result
            }
            
        except Exception as e:
            pending_action['status'] = 'failed'
            pending_action['error'] = str(e)
            logger.error(f"Error executing action {action_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f"Failed to execute action: {str(e)}"
            }
    
    def cancel_action(self, action_id: str) -> Dict:
        """Cancel a pending action"""
        if action_id not in self.pending_actions:
            return {'status': 'error', 'message': 'Action not found'}
        
        pending_action = self.pending_actions[action_id]
        pending_action['status'] = 'cancelled'
        
        return {
            'status': 'cancelled',
            'message': 'Action cancelled successfully'
        }
    
    def _execute_escalation(self, data: Dict) -> Dict:
        """Execute escalation action"""
        # In production, this would create a real escalation
        return {
            'escalation_created': True,
            'ticket_id': data['ticket_id'],
            'priority': data['priority'],
            'assigned_to': data['assigned_to'],
            'escalation_id': f"ESC-{uuid.uuid4().hex[:8]}"
        }
    
    def _execute_ticket_update(self, data: Dict) -> Dict:
        """Execute ticket update action"""
        # In production, this would update the ticket in database
        return {
            'ticket_updated': True,
            'ticket_id': data['ticket_id'],
            'updates': data['updates'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _execute_task_creation(self, data: Dict) -> Dict:
        """Execute task creation action"""
        # In production, this would create a task in the system
        return {
            'task_created': True,
            'task_id': f"TASK-{uuid.uuid4().hex[:8]}",
            'description': data['description'],
            'due_date': data['due_date'],
            'assigned_to': data['assigned_to']
        }