"""
Data models for the Process Builder.
"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class ProcessStep:
    """Represents a single step in a process."""
    step_id: str
    description: str
    decision: str
    success_outcome: str
    failure_outcome: str
    note_id: Optional[str] = None
    next_step_success: str = "End"
    next_step_failure: str = "End"
    validation_rules: Optional[str] = None
    error_codes: Optional[str] = None
    retry_logic: Optional[str] = None
    design_feedback: Optional[str] = None
    created_at: datetime = datetime.now()

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