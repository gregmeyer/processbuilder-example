"""
Configuration management for the Process Builder.
"""
import os
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
from dotenv import load_dotenv

class Config:
    """Configuration class for Process Builder."""
    
    def __init__(self, env_path: Optional[Path] = None):
        self.env_path = env_path or Path(os.path.dirname(os.path.dirname(__file__))) / '.env'
        self._load_env()
        self._validate_config()
        self._input_handler = None
    
    def _load_env(self) -> None:
        """Load environment variables from .env file."""
        if self.env_path.exists():
            load_dotenv(dotenv_path=self.env_path)
        else:
            print(f"Warning: .env file not found at {self.env_path}")
            print("To use AI features, please create a .env file with your OpenAI API key:")
            print(f"echo 'OPENAI_API_KEY=your_api_key_here' > {self.env_path}")
            print("You can continue without AI features, but step evaluation will not work.")
    
    def _validate_config(self) -> None:
        """Validate the configuration."""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            print("Warning: OPENAI_API_KEY not found in environment variables.")
            print("To enable AI features, please set the OPENAI_API_KEY environment variable.")
    
    @property
    def has_openai(self) -> bool:
        """Check if OpenAI API key is available."""
        return bool(self.openai_api_key)
    
    @property
    def default_output_dir(self) -> Path:
        """Get the default output directory."""
        return Path("testing/output")
        
    @property
    def base_output_dir(self) -> Optional[Path]:
        """Get the base output directory."""
        return None
        
    @property
    def timestamp(self) -> str:
        """Get the current timestamp in ISO format."""
        return datetime.now().isoformat()
        
    @property
    def input_handler(self) -> Optional[Callable[[str], str]]:
        """Get the input handler function.
        
        Returns:
            A callable that takes a prompt string and returns user input,
            or None to use the default input handler.
        """
        return self._input_handler
        
    @input_handler.setter
    def input_handler(self, handler: Optional[Callable[[str], str]]) -> None:
        """Set the input handler function.
        
        Args:
            handler: A callable that takes a prompt string and returns user input,
                    or None to use the default input handler.
        """
        self._input_handler = handler 