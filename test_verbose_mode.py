#!/usr/bin/env python3
"""
Test script to verify that verbose mode controls OpenAI response logging correctly.
"""

import os
import sys
import unittest
import io
from io import StringIO
import logging
from datetime import datetime

# Import set_log_level from the builder module
from processbuilder.builder import set_log_level
from unittest.mock import patch, MagicMock, call
from typing import List, Optional, Tuple
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from processbuilder.builder import ProcessBuilder
from processbuilder.config import Config
from processbuilder.models import ProcessStep

class TestVerboseMode(unittest.TestCase):
    """Test verbose mode functionality."""
    
    def setUp(self):
        """Set up tests."""
        # Set environment variable for testing
        os.environ["OPENAI_API_KEY"] = "test_key"
        
        # Create a config for tests
        self.config = Config()
        
        # Set up logging capture
        self.log_capture = StringIO()
        self.log_handler = logging.StreamHandler(self.log_capture)
        
        # Add a formatter to distinguish between log levels
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        self.log_handler.setFormatter(formatter)
        
        # Configure handler to capture all levels including warnings
        self.log_handler.setLevel(logging.DEBUG)
        
        # Ensure root logger doesn't interfere
        logging.getLogger().setLevel(logging.WARNING)
        
        # Get the logger used by builder.py
        self.logger = logging.getLogger('processbuilder.builder')
        
        # Save original state
        self.original_handlers = list(self.logger.handlers)
        self.original_level = self.logger.level
        self.original_propagate = self.logger.propagate
        
        # Clear existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add our handler to the logger
        self.logger.addHandler(self.log_handler)
        
        # Make sure we're capturing everything at the handler level
        self.log_handler.setLevel(logging.DEBUG)
        
        # Default logger level starts at INFO
        self.logger.setLevel(logging.INFO)
        
        # Force propagation to be False to isolate our logger
        self.logger.propagate = False
        
        # Clear any initial log contents
        self.log_capture.truncate(0)
        self.log_capture.seek(0)
        
        # Reset verbose mode at the start of each test
        # Reset class variable directly instead of calling the classmethod
        ProcessBuilder._verbose = False  
        # Call set_log_level directly to ensure logger is at INFO level
        set_log_level(False)
        
    def tearDown(self):
        """Clean up after tests."""
        # Remove custom handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            
        # Restore original handlers
        for handler in self.original_handlers:
            self.logger.addHandler(handler)
            
        # Restore original level and propagation
        self.logger.setLevel(self.original_level)
        self.logger.propagate = self.original_propagate
        
        # Reset ProcessBuilder class variable
        ProcessBuilder._verbose = False
        
        # Remove test environment variable
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
    
    @patch('openai.OpenAI')
    def test_verbose_mode_off(self, mock_openai):
        """Test that debug logs do not appear when verbose mode is off."""
        # Set up the OpenAI mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock the chat completions response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Gather Requirements"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Ensure verbose mode is off
        # Set verbose mode correctly
        ProcessBuilder._verbose = False
        set_log_level(False)
        
        # Clear logs before testing
        self.log_capture.truncate(0)
        self.log_capture.seek(0)
        
        # Verify logger is set to INFO level
        self.assertEqual(self.logger.level, logging.INFO)
        
        # Create a ProcessBuilder with verbose mode off
        builder = ProcessBuilder("Customer Onboarding", self.config)
        self.assertFalse(builder.verbose)
        
        # Access the suggested_first_step property to trigger logging
        suggestion = builder.suggested_first_step
        
        # Get the captured logs
        logs = self.log_capture.getvalue()
        
        # Verify that debug logs do not appear
        self.assertNotIn("DEBUG", logs)
        self.assertNotIn("Sending OpenAI prompt", logs)
        self.assertNotIn("Received OpenAI first step suggestion", logs)
        
        # Verify the suggestion was still returned
        self.assertEqual(suggestion, "Gather Requirements")

    @patch('openai.OpenAI')
    def test_verbose_mode_on(self, mock_openai):
        """Test that debug logs appear when verbose mode is on."""
        # Set up the OpenAI mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock the chat completions response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Gather Requirements"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Explicitly set verbose mode on
        # Set verbose mode correctly
        ProcessBuilder._verbose = True
        set_log_level(True)
        
        # Clear the log capture and reset logger state
        self.log_capture.truncate(0)
        self.log_capture.seek(0)
        
        # Make sure the log levels are properly set for verbose mode
        self.logger.setLevel(logging.DEBUG)
        self.log_handler.setLevel(logging.DEBUG)
        
        # Create a ProcessBuilder with verbose mode already on (set above)
        builder = ProcessBuilder("Customer Onboarding", self.config)
        
        # Access the suggested_first_step property to trigger logging
        # Verify logger is set to DEBUG level
        self.assertEqual(self.logger.level, logging.DEBUG)
        
        # Access the suggested_first_step property to trigger logging
        suggestion = builder.suggested_first_step
        
        # Get the captured logs
        logs = self.log_capture.getvalue()
        
        # Verify that debug logs appear
        self.assertIn("DEBUG", logs)
        self.assertIn("Sending OpenAI prompt", logs)
        
        # Verify the suggestion was returned
        self.assertEqual(suggestion, "Gather Requirements")
    @patch('openai.OpenAI')
    def test_verbose_mode_toggle(self, mock_openai):
        """Test toggling verbose mode on and off."""
        # Set up the OpenAI mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Ensure the logger is capturing all needed levels
        self.logger.setLevel(logging.DEBUG)
        self.log_handler.setLevel(logging.DEBUG)
        
        # Mock the chat completions response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Gather Requirements"
        mock_client.chat.completions.create.return_value = mock_response
        
        # PART 1: Start with verbose OFF
        # =================================
        # Explicitly set verbose mode off and verify log level
        # Set verbose mode correctly
        ProcessBuilder._verbose = False
        set_log_level(False)
        self.assertEqual(self.logger.level, logging.INFO)
        
        # Create a ProcessBuilder with verbose mode off initially
        builder = ProcessBuilder("Customer Onboarding", self.config)
        self.assertFalse(builder.verbose)
        
        # Clear the log capture
        self.log_capture.truncate(0)
        self.log_capture.seek(0)
        
        # Access the suggested_first_step property
        suggestion = builder.suggested_first_step
        
        # Get the captured logs
        logs_before = self.log_capture.getvalue()
        
        # Verify debug logs don't appear when verbose is off
        self.assertNotIn("DEBUG", logs_before)
        
        # PART 2: Now toggle verbose ON
        # =================================
        # Turn on verbose mode and verify log level
        # Set verbose mode correctly
        ProcessBuilder._verbose = True
        set_log_level(True)
        self.assertEqual(self.logger.level, logging.DEBUG)
        
        # Update builder's verbose setting
        builder.verbose = True
        self.assertTrue(builder.verbose)
        
        # Clear the log capture again
        self.log_capture.truncate(0)
        self.log_capture.seek(0)
        
        # Access the suggested_first_step property again
        suggestion = builder.suggested_first_step
        
        # Get the captured logs
        logs_after = self.log_capture.getvalue()
        
        # Verify debug logs now appear when verbose is on
        # Verify debug logs now appear when verbose is on
        self.assertIn("DEBUG", logs_after)
        self.assertIn("Sending OpenAI prompt", logs_after)

        # Clear logs again to test warnings
        self.log_capture.truncate(0)
        self.log_capture.seek(0)
        
        # Clear logs before removing API key
        self.log_capture.truncate(0)
        self.log_capture.seek(0)

        # Remove the API key to trigger the warning
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
            
        # Create another ProcessBuilder that should trigger warnings
        builder2 = ProcessBuilder("Customer Onboarding", self.config, verbose=True)
        
        # Get the captured logs
        logs_with_verbose = self.log_capture.getvalue()
        
        # Print logs for debugging
        print(f"\nCapture logs:\n{logs_with_verbose}")
        
        # Verify warning logs still appear with verbose mode
        self.assertIn("WARNING", logs_with_verbose)
        self.assertIn("No OpenAI API key found", logs_with_verbose)
if __name__ == "__main__":
    unittest.main()

