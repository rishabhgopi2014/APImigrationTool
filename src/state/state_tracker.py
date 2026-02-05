"""
Migration State Tracker

Manages migration state machine with persistence and recovery.
Tracks API migration progress through different phases.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import uuid


class MigrationStatus(str, Enum):
    """Migration status enum matching database schema"""
    DISCOVERED = "DISCOVERED"
    PLANNED = "PLANNED"
    VALIDATED = "VALIDATED"
    DEPLOYED_MIRROR = "DEPLOYED_MIRROR"
    CANARY_5 = "CANARY_5"
    CANARY_25 = "CANARY_25"
    CANARY_50 = "CANARY_50"
    CANARY_75 = "CANARY_75"
    COMPLETED = "COMPLETED"
    ROLLED_BACK = "ROLLED_BACK"
    DECOMMISSIONED = "DECOMMISSIONED"
    FAILED = "FAILED"


# Valid state transitions
VALID_TRANSITIONS = {
    MigrationStatus.DISCOVERED: [MigrationStatus.PLANNED, MigrationStatus.FAILED],
    MigrationStatus.PLANNED: [MigrationStatus.VALIDATED, MigrationStatus.DISCOVERED, MigrationStatus.FAILED],
    MigrationStatus.VALIDATED: [MigrationStatus.DEPLOYED_MIRROR, MigrationStatus.PLANNED, MigrationStatus.FAILED],
    MigrationStatus.DEPLOYED_MIRROR: [
        MigrationStatus.CANARY_5,
        MigrationStatus.ROLLED_BACK,
        MigrationStatus.VALIDATED,
        MigrationStatus.FAILED
    ],
    MigrationStatus.CANARY_5: [
        MigrationStatus.CANARY_25,
        MigrationStatus.ROLLED_BACK,
        MigrationStatus.DEPLOYED_MIRROR,
        MigrationStatus.FAILED
    ],
    MigrationStatus.CANARY_25: [
        MigrationStatus.CANARY_50,
        MigrationStatus.ROLLED_BACK,
        MigrationStatus.CANARY_5,
        MigrationStatus.FAILED
    ],
    MigrationStatus.CANARY_50: [
        MigrationStatus.CANARY_75,
        MigrationStatus.ROLLED_BACK,
        MigrationStatus.CANARY_25,
        MigrationStatus.FAILED
    ],
    MigrationStatus.CANARY_75: [
        MigrationStatus.COMPLETED,
        MigrationStatus.ROLLED_BACK,
        MigrationStatus.CANARY_50,
        MigrationStatus.FAILED
    ],
    MigrationStatus.COMPLETED: [MigrationStatus.DECOMMISSIONED, MigrationStatus.ROLLED_BACK],
    MigrationStatus.ROLLED_BACK: [MigrationStatus.DEPLOYED_MIRROR, MigrationStatus.FAILED],
    MigrationStatus.DECOMMISSIONED: [],  # Terminal state
    MigrationStatus.FAILED: [MigrationStatus.DISCOVERED]  # Can restart from discovery
}


@dataclass
class MigrationState:
    """Migration state for an API"""
    api_id: str
    api_name: str
    platform: str
    status: MigrationStatus
    previous_status: Optional[MigrationStatus] = None
    
    # Gloo Gateway details
    gloo_namespace: Optional[str] = None
    gloo_virtual_service_name: Optional[str] = None
    gloo_configs: Optional[Dict[str, Any]] = None
    
    # Traffic shifting
    current_traffic_percentage: int = 0
    target_traffic_percentage: Optional[int] = None
    
    # Metrics
    legacy_error_rate: Optional[float] = None
    gloo_error_rate: Optional[float] = None
    legacy_p95_latency_ms: Optional[int] = None
    gloo_p95_latency_ms: Optional[int] = None
    
    # State metadata
    last_transition_at: Optional[datetime] = None
    transition_reason: Optional[str] = None
    
    # Lock info
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert enums to strings
        data['status'] = self.status.value
        if self.previous_status:
            data['previous_status'] = self.previous_status.value
        # Convert datetime to ISO format
        if self.last_transition_at:
            data['last_transition_at'] = self.last_transition_at.isoformat()
        if self.locked_at:
            data['locked_at'] = self.locked_at.isoformat()
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data


class StateTransitionError(Exception):
    """Raised when invalid state transition is attempted"""
    pass


class StateTracker:
    """
    Migration state machine with persistence.
    
    In production, this would integrate with PostgreSQL database.
    For now, implements in-memory storage with database interface.
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize state tracker.
        
        Args:
            db_connection: Database connection (optional for now)
        """
        self.db = db_connection
        self._states: Dict[str, MigrationState] = {}
    
    def create_state(
        self,
        api_id: str,
        api_name: str,
        platform: str,
        initial_status: MigrationStatus = MigrationStatus.DISCOVERED
    ) -> MigrationState:
        """
        Create initial migration state for an API.
        
        Args:
            api_id: API unique ID
            api_name: API name
            platform: Platform name
            initial_status: Initial migration status
            
        Returns:
            Created MigrationState
        """
        state = MigrationState(
            api_id=api_id,
            api_name=api_name,
            platform=platform,
            status=initial_status,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_transition_at=datetime.now()
        )
        
        self._states[api_id] = state
        
        # TODO: Persist to database
        # self._persist_state(state)
        
        return state
    
    def get_state(self, api_id: str) -> Optional[MigrationState]:
        """
        Get current migration state for an API.
        
        Args:
            api_id: API unique ID
            
        Returns:
            MigrationState or None if not found
        """
        # TODO: Load from database
        return self._states.get(api_id)
    
    def can_transition(
        self,
        current_status: MigrationStatus,
        target_status: MigrationStatus
    ) -> bool:
        """
        Check if state transition is valid.
        
        Args:
            current_status: Current migration status
            target_status: Target migration status
            
        Returns:
            True if transition is allowed
        """
        allowed_transitions = VALID_TRANSITIONS.get(current_status, [])
        return target_status in allowed_transitions
    
    def transition(
        self,
        api_id: str,
        target_status: MigrationStatus,
        reason: Optional[str] = None,
        **kwargs
    ) -> MigrationState:
        """
        Transition API to new migration status.
        
        Args:
            api_id: API unique ID
            target_status: Target migration status
            reason: Reason for transition
            **kwargs: Additional state updates (traffic percentage, metrics, etc.)
            
        Returns:
            Updated MigrationState
            
        Raises:
            StateTransitionError: If transition is invalid
            ValueError: If API state not found
        """
        state = self.get_state(api_id)
        
        if not state:
            raise ValueError(f"No migration state found for API ID: {api_id}")
        
        # Validate transition
        if not self.can_transition(state.status, target_status):
            raise StateTransitionError(
                f"Invalid transition from {state.status.value} to {target_status.value}"
            )
        
        # Update state
        state.previous_status = state.status
        state.status = target_status
        state.last_transition_at = datetime.now()
        state.transition_reason = reason
        state.updated_at = datetime.now()
        
        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        # Persist changes
        # TODO: self._persist_state(state)
        
        return state
    
    def get_traffic_percentage_for_status(self, status: MigrationStatus) -> int:
        """Get traffic percentage associated with a canary status"""
        traffic_map = {
            MigrationStatus.DISCOVERED: 0,
            MigrationStatus.PLANNED: 0,
            MigrationStatus.VALIDATED: 0,
            MigrationStatus.DEPLOYED_MIRROR: 0,
            MigrationStatus.CANARY_5: 5,
            MigrationStatus.CANARY_25: 25,
            MigrationStatus.CANARY_50: 50,
            MigrationStatus.CANARY_75: 75,
            MigrationStatus.COMPLETED: 100,
            MigrationStatus.ROLLED_BACK: 0,
        }
        return traffic_map.get(status, 0)
    
    def advance_canary(
        self,
        api_id: str,
        reason: Optional[str] = None
    ) -> MigrationState:
        """
        Advance to next canary phase.
        
        Args:
            api_id: API unique ID
            reason: Reason for advancement
            
        Returns:
            Updated MigrationState
        """
        state = self.get_state(api_id)
        
        if not state:
            raise ValueError(f"No migration state found for API ID: {api_id}")
        
        # Determine next canary phase
        canary_progression = [
            MigrationStatus.DEPLOYED_MIRROR,
            MigrationStatus.CANARY_5,
            MigrationStatus.CANARY_25,
            MigrationStatus.CANARY_50,
            MigrationStatus.CANARY_75,
            MigrationStatus.COMPLETED
        ]
        
        try:
            current_index = canary_progression.index(state.status)
            next_status = canary_progression[current_index + 1]
        except (ValueError, IndexError):
            raise StateTransitionError(
                f"Cannot advance canary from status {state.status.value}"
            )
        
        # Transition to next phase
        next_traffic = self.get_traffic_percentage_for_status(next_status)
        
        return self.transition(
            api_id,
            next_status,
            reason=reason or f"Advancing to {next_traffic}% traffic",
            current_traffic_percentage=next_traffic,
            target_traffic_percentage=next_traffic
        )
    
    def rollback(
        self,
        api_id: str,
        reason: str
    ) -> MigrationState:
        """
        Rollback migration to legacy gateway.
        
        Args:
            api_id: API unique ID
            reason: Reason for rollback
            
        Returns:
            Updated MigrationState
        """
        return self.transition(
            api_id,
            MigrationStatus.ROLLED_BACK,
            reason=reason,
            current_traffic_percentage=0
        )
    
    def fail(
        self,
        api_id: str,
        reason: str
    ) -> MigrationState:
        """
        Mark migration as failed.
        
        Args:
            api_id: API unique ID
            reason: Failure reason
            
        Returns:
            Updated MigrationState
        """
        return self.transition(
            api_id,
            MigrationStatus.FAILED,
            reason=reason
        )
    
    def list_states_by_status(
        self,
        status: MigrationStatus
    ) -> list[MigrationState]:
        """
        List all APIs in a specific migration status.
        
        Args:
            status: Migration status to filter by
            
        Returns:
            List of MigrationState objects
        """
        # TODO: Query database
        return [state for state in self._states.values() if state.status == status]
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get migration statistics across all APIs.
        
        Returns:
            Dict of status counts
        """
        stats = {status.value: 0 for status in MigrationStatus}
        
        for state in self._states.values():
            stats[state.status.value] += 1
        
        return stats
