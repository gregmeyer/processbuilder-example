#!/usr/bin/env python3
"""
Test script to verify the suggested_first_step property works correctly.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent / "src"))

from processbuilder.builder import ProcessBuilder
from processbuilder.config import Config
from processbuilder.models import ProcessStep

class TestSuggestedFirstStep(unittest.TestCase):
    """Test cases for the suggested_first_step property."""

    def setUp(self):
        """Set up the test environment."""
        # Create a test config
        self.config = Config()
        
        # Save original API key (if any)
        self.original_api_key = os.environ.get("OPENAI_API_KEY")
        
    def tearDown(self):
        """Clean up after tests."""
        # Restore original API key
        if self.original_api_key:
            os.environ["OPENAI_API_KEY"] = self.original_api_key
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

    @patch('openai.OpenAI')
    def test_suggestion_with_openai_available(self, mock_openai):
        """Test that a suggestion is returned when OpenAI is available and there are 0 steps."""
        # Set up the OpenAI mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock the chat completions response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Gather Requirements"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Set an API key to simulate OpenAI availability
        os.environ["OPENAI_API_KEY"] = "fake-api-key"
        
        # Create a ProcessBuilder
        builder = ProcessBuilder("Customer Onboarding", self.config)
        
        # Test the suggested_first_step property
        suggestion = builder.suggested_first_step
        
        # Verify that OpenAI was called
        mock_client.chat.completions.create.assert_called_once()
        
        # Verify that a suggestion was returned
        self.assertEqual(suggestion, "Gather Requirements")
        
    def test_empty_suggestion_with_existing_steps(self):
        """Test that an empty string is returned when there are existing steps."""
        # Set an API key to simulate OpenAI availability
        os.environ["OPENAI_API_KEY"] = "fake-api-key"
        
        # Create a ProcessBuilder
        builder = ProcessBuilder("Customer Onboarding", self.config)
        
        # Add a step to the process
        step = ProcessStep(
            step_id="Step1",
            description="First step in the process",
            decision="Is this step complete?",
            success_outcome="The step was successful",
            failure_outcome="The step failed",
            note_id=None,
            next_step_success="End",
            next_step_failure="End",
            validation_rules=None,
            error_codes=None
        )
        builder.steps.append(step)
        
        # Test the suggested_first_step property
        suggestion = builder.suggested_first_step
        
        # Verify that an empty string was returned
        self.assertEqual(suggestion, "")
        
    def test_empty_suggestion_without_openai(self):
        """Test that an empty string is returned when OpenAI is not available."""
        # Remove API key to simulate OpenAI unavailability
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        # Create a ProcessBuilder
        builder = ProcessBuilder("Customer Onboarding", self.config)
        
        # Force openai_client to None to ensure it's unavailable
        builder.openai_client = None
        
        # Test the suggested_first_step property
        suggestion = builder.suggested_first_step
        
        # Verify that an empty string was returned
        self.assertEqual(suggestion, "")

if __name__ == "__main__":
    unittest.main()

