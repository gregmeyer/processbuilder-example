"""
Test file to verify single step processes work correctly
"""
import unittest
from datetime import datetime
from .models import ProcessStep
from .utils import validate_process_flow

class SingleStepTest(unittest.TestCase):
    """Tests for single step processes"""
    
    def test_single_step_default_end(self):
        """Test that a single step with default 'end' values validates successfully"""
        step = ProcessStep(
            step_id="step1",
            description="Test Step",
            decision="Is this working?",
            success_outcome="Yes, it works",
            failure_outcome="No, it doesn't work"
            # Using default next_step_success="end" and next_step_failure="end"
        )
        
        issues = validate_process_flow([step])
        self.assertEqual(len(issues), 0, f"Expected no issues but got: {issues}")
    
    def test_single_step_mixed_case_end(self):
        """Test that a single step with mixed case 'End' values validates successfully"""
        step = ProcessStep(
            step_id="step1",
            description="Test Step",
            decision="Is this working?",
            success_outcome="Yes, it works",
            failure_outcome="No, it doesn't work",
            next_step_success="End",  # Upper case E
            next_step_failure="END"   # All upper case
        )
        
        issues = validate_process_flow([step])
        self.assertEqual(len(issues), 0, f"Expected no issues but got: {issues}")
    
    def test_single_step_no_end(self):
        """Test that a single step with neither success nor failure pointing to 'end' fails validation"""
        step = ProcessStep(
            step_id="step1",
            description="Test Step",
            decision="Is this working?",
            success_outcome="Yes, it works",
            failure_outcome="No, it doesn't work",
            next_step_success="non_existent_step",  # Not pointing to end
            next_step_failure="another_non_existent_step"  # Not pointing to end
        )
        
        issues = validate_process_flow([step])
        self.assertGreater(len(issues), 0, "Expected validation issues but got none")
        self.assertTrue(any("must have at least one path that leads to 'End'" in issue for issue in issues),
                       f"Expected 'path to End' issue but got: {issues}")

if __name__ == "__main__":
    unittest.main()

