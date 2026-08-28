"""Configuration module for Hiring Panel AI.

Provides centralized management for API keys, model selections, temperature settings,
and execution parameters using environment variables and fallback defaults.
"""

import os
from typing import Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class AppConfig(BaseModel):
    """Application configuration settings."""

    llm_provider: Literal["gemini", "openai", "anthropic"] = Field(
        default="gemini",
        description="The primary LLM provider to use for agents and extraction."
    )

    # Gemini Settings
    gemini_api_key: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", ""),
        description="API key for Google Gemini calls."
    )
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite",
        description="Default Gemini model for agents and evaluation."
    )
    
    # OpenAI Settings
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="API key for OpenAI calls."
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="Default OpenAI model for agents and evaluation."
    )

    # Anthropic Settings
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""),
        description="API key for Anthropic calls."
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20240620",
        description="Default Anthropic model for agents and evaluation."
    )

    # Agent & Debate Configuration
    temperature: float = Field(
        default=0.2,
        description="Temperature setting for model inference."
    )
    max_debate_rounds: int = Field(
        default=2,
        description="Maximum rounds of cross-agent debate."
    )

    def validate_keys(self) -> None:
        """Validate that the required API key for the chosen provider is present."""
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            print("[Warning] GEMINI_API_KEY is not set in environment variables.")
        elif self.llm_provider == "openai" and not self.openai_api_key:
            print("[Warning] OPENAI_API_KEY is not set in environment variables.")
        elif self.llm_provider == "anthropic" and not self.anthropic_api_key:
            print("[Warning] ANTHROPIC_API_KEY is not set in environment variables.")


# Global default configuration instance
config = AppConfig()
