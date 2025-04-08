"""Base models for the Process Builder."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, ClassVar
from datetime import datetime
import json

@dataclass
class ProcessStep:
    """Represents a single step in a process."""
    step_id: str
    description: str
    decision: str
    success_outcome: str
    failure_outcome: str
    note_id: Optional[str] = None
    next_step_success: str = "end"
    next_step_failure: str = "end"
    validation_rules: Optional[str] = None
    error_codes: Optional[str] = None
    retry_logic: Optional[str] = None
    design_feedback: Optional[str] = None
    created_at: datetime = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the step to a dictionary for JSON serialization."""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "decision": self.decision,
            "success_outcome": self.success_outcome,
            "failure_outcome": self.failure_outcome,
            "note_id": self.note_id,
            "next_step_success": self.next_step_success,
            "next_step_failure": self.next_step_failure,
            "validation_rules": self.validation_rules,
            "error_codes": self.error_codes,
            "retry_logic": self.retry_logic,
            "design_feedback": self.design_feedback,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessStep':
        """Create a ProcessStep from a dictionary."""
        data = data.copy()
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

@dataclass
class ProcessNote:
    """Represents a note attached to a process step."""
    note_id: str
    content: str
    step_id: str
    created_at: datetime = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the note to a dictionary for JSON serialization."""
        return {
            "note_id": self.note_id,
            "content": self.content,
            "step_id": self.step_id,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessNote':
        """Create a ProcessNote from a dictionary."""
        data = data.copy()
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data) 