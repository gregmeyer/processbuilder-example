"""
Data models for the Process Builder.
"""
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
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessStep':
        """Create a step from a dictionary (loaded from JSON)."""
        # Handle created_at conversion from ISO format string to datetime
        if "created_at" in data and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

    def validate(self) -> List[str]:
        """Validate the step and return a list of issues."""
        issues = []
        if not self.step_id.strip():
            issues.append("Step ID cannot be empty")
        if not self.description.strip():
            issues.append("Description cannot be empty")
        if not self.decision.strip():
            issues.append("Decision cannot be empty")
        if not self.success_outcome.strip():
            issues.append("Success outcome cannot be empty")
        if not self.failure_outcome.strip():
            issues.append("Failure outcome cannot be empty")
        return issues

@dataclass
class ProcessNote:
    """Represents a note associated with a process step."""
    note_id: str
    content: str
    related_step_id: str
    created_at: datetime = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the note to a dictionary for JSON serialization."""
        return {
            "note_id": self.note_id,
            "content": self.content,
            "related_step_id": self.related_step_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessNote':
        """Create a note from a dictionary (loaded from JSON)."""
        # Handle created_at conversion from ISO format string to datetime
        if "created_at" in data and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

    def validate(self) -> List[str]:
        """Validate the note and return a list of issues."""
        issues = []
        if not self.note_id.strip():
            issues.append("Note ID cannot be empty")
        if not self.content.strip():
            issues.append("Content cannot be empty")
        if not self.related_step_id.strip():
            issues.append("Related step ID cannot be empty")
        return issues 