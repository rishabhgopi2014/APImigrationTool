"""
Audit Logger

Provides immutable audit logging for all migration actions with:
- Correlation IDs for tracing
- Structured logging
- Compliance-ready format
- Integration with database audit table
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import structlog


class ResourceType(str, Enum):
    """Resource types for audit logging"""
    API = "API"
    MIGRATION = "MIGRATION"
    APPROVAL = "APPROVAL"
    PLAN = "PLAN"
    CONFIG = "CONFIG"
    LOCK = "LOCK"


class Action(str, Enum):
    """Actions for audit logging"""
    # Discovery actions
    DISCOVER = "DISCOVER"
    REGISTER = "REGISTER"
    
    # Planning actions
    PLAN = "PLAN"
    VALIDATE = "VALIDATE"
    
    # Deployment actions
    DEPLOY = "DEPLOY"
    DEPLOY_MIRROR = "DEPLOY_MIRROR"
    
    # Traffic management actions
    SHIFT_TRAFFIC = "SHIFT_TRAFFIC"
    ADVANCE_CANARY = "ADVANCE_CANARY"
    ROLLBACK = "ROLLBACK"
    
    # Approval actions
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    
    # Portal actions
    PUBLISH = "PUBLISH"
    NOTIFY = "NOTIFY"
    
    # Decommission actions
    DECOMMISSION = "DECOMMISSION"
    ARCHIVE = "ARCHIVE"
    
    # Lock actions
    ACQUIRE_LOCK = "ACQUIRE_LOCK"
    RELEASE_LOCK = "RELEASE_LOCK"
    
    # State actions
    UPDATE_STATE = "UPDATE_STATE"
    FAIL = "FAIL"


class AuditLogger:
    """
    Audit logger for compliance and troubleshooting.
    
    Logs all migration actions with correlation IDs for tracing.
    """
    
    def __init__(self, actor: str, actor_team: str, db_connection=None):
        """
        Initialize audit logger.
        
        Args:
            actor: User/developer performing actions
            actor_team: Team the actor belongs to
            db_connection: Database connection for persistent audit log
        """
        self.actor = actor
        self.actor_team = actor_team
        self.db = db_connection
        
        # Configure structlog for structured logging
        self.logger = structlog.get_logger()
    
    def log(
        self,
        action: Action,
        resource_type: ResourceType,
        success: bool,
        resource_id: Optional[str] = None,
        api_name: Optional[str] = None,
        platform: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Log an audit event.
        
        Args:
            action: Action being performed
            resource_type: Type of resource
            success: Whether action succeeded
            resource_id: Resource ID (UUID)
            api_name: API name
            platform: Platform name
            details: Additional action-specific details
            error_message: Error message if action failed
            correlation_id: Correlation ID for tracing (auto-generated if not provided)
            
        Returns:
            correlation_id for this audit event
        """
        # Generate correlation ID if not provided
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        audit_entry = {
            "correlation_id": correlation_id,
            "actor": self.actor,
            "actor_team": self.actor_team,
            "action": action.value,
            "resource_type": resource_type.value,
            "resource_id": resource_id,
            "api_name": api_name,
            "platform": platform,
            "success": success,
            "error_message": error_message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Structured log
        if success:
            self.logger.info(
                f"{action.value} {resource_type.value}",
                **audit_entry
            )
        else:
            self.logger.error(
                f"{action.value} {resource_type.value} FAILED",
                **audit_entry
            )
        
        # Persist to database audit table
        self._persist_audit_log(audit_entry)
        
        return correlation_id
    
    def _persist_audit_log(self, audit_entry: Dict[str, Any]):
        """
        Persist audit log to database (immutable).
        
        Args:
            audit_entry: Audit entry dictionary
        """
        # TODO: Insert into audit_log table
        # SQL: INSERT INTO audit_log (correlation_id, actor, action, ...)
        #      VALUES (...)
        pass
    
    def log_discovery(
        self,
        platform: str,
        apis_discovered: int,
        success: bool,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log API discovery action"""
        return self.log(
            action=Action.DISCOVER,
            resource_type=ResourceType.API,
            success=success,
            platform=platform,
            details={"apis_discovered": apis_discovered},
            error_message=error_message,
            correlation_id=correlation_id
        )
    
    def log_plan_generation(
        self,
        api_name: str,
        platform: str,
        api_id: str,
        success: bool,
        plan_details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log migration plan generation"""
        return self.log(
            action=Action.PLAN,
            resource_type=ResourceType.PLAN,
            success=success,
            resource_id=api_id,
            api_name=api_name,
            platform=platform,
            details=plan_details,
            error_message=error_message,
            correlation_id=correlation_id
        )
    
    def log_deployment(
        self,
        api_name: str,
        platform: str,
        api_id: str,
        namespace: str,
        mirror_mode: bool,
        success: bool,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log Gloo Gateway deployment"""
        action = Action.DEPLOY_MIRROR if mirror_mode else Action.DEPLOY
        
        return self.log(
            action=action,
            resource_type=ResourceType.MIGRATION,
            success=success,
            resource_id=api_id,
            api_name=api_name,
            platform=platform,
            details={
                "namespace": namespace,
                "mirror_mode": mirror_mode
            },
            error_message=error_message,
            correlation_id=correlation_id
        )
    
    def log_traffic_shift(
        self,
        api_name: str,
        platform: str,
        api_id: str,
        from_percentage: int,
        to_percentage: int,
        success: bool,
        metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log traffic shifting action"""
        return self.log(
            action=Action.SHIFT_TRAFFIC,
            resource_type=ResourceType.MIGRATION,
            success=success,
            resource_id=api_id,
            api_name=api_name,
            platform=platform,
            details={
                "from_percentage": from_percentage,
                "to_percentage": to_percentage,
                "metrics": metrics or {}
            },
            error_message=error_message,
            correlation_id=correlation_id
        )
    
    def log_rollback(
        self,
        api_name: str,
        platform: str,
        api_id: str,
        reason: str,
        success: bool,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log rollback action"""
        return self.log(
            action=Action.ROLLBACK,
            resource_type=ResourceType.MIGRATION,
            success=success,
            resource_id=api_id,
            api_name=api_name,
            platform=platform,
            details={"reason": reason},
            error_message=error_message,
            correlation_id=correlation_id
        )
    
    def log_approval_request(
        self,
        api_name: str,
        platform: str,
        api_id: str,
        request_type: str,
        success: bool,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log approval request"""
        return self.log(
            action=Action.REQUEST_APPROVAL,
            resource_type=ResourceType.APPROVAL,
            success=success,
            resource_id=api_id,
            api_name=api_name,
            platform=platform,
            details={"request_type": request_type},
            error_message=error_message,
            correlation_id=correlation_id
        )
    
    def log_approval_decision(
        self,
        api_name: str,
        platform: str,
        api_id: str,
        approved: bool,
        approver: str,
        reason: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log approval decision"""
        action = Action.APPROVE if approved else Action.REJECT
        
        return self.log(
            action=action,
            resource_type=ResourceType.APPROVAL,
            success=True,
            resource_id=api_id,
            api_name=api_name,
            platform=platform,
            details={
                "approver": approver,
                "reason": reason
            },
            correlation_id=correlation_id
        )
    
    def log_lock_acquisition(
        self,
        api_name: str,
        platform: str,
        success: bool,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log lock acquisition"""
        return self.log(
            action=Action.ACQUIRE_LOCK,
            resource_type=ResourceType.LOCK,
            success=success,
            api_name=api_name,
            platform=platform,
            error_message=error_message,
            correlation_id=correlation_id
        )
    
    def create_correlation_id(self) -> str:
        """Generate a new correlation ID for tracing"""
        return str(uuid.uuid4())
