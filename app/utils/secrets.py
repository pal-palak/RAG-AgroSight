"""
AgroSight – Secrets Management Utility
========================================
Provides secure handling of sensitive configuration values.
Supports multiple backends:
  • Environment variables (default)
  • AWS Secrets Manager
  • HashiCorp Vault
  • Azure Key Vault
  • Local encrypted .env files

Usage:
  from app.utils.secrets import SecretManager
  secrets = SecretManager()
  api_key = secrets.get("MISTRAL_API_KEY")
"""

from __future__ import annotations

import os
from typing import Optional
from app.utils.logger import logger


class SecretManager:
    """
    Centralized secrets management with multiple backend support.
    Falls back to environment variables by default.
    """
    
    BACKEND = os.getenv("SECRETS_BACKEND", "env").lower()
    
    # Critical secrets that must be validated on startup
    REQUIRED_SECRETS = [
        "MISTRAL_API_KEY",
        "QDRANT_URL",
        "QDRANT_API_KEY",
    ]
    
    # Optional secrets that should be warned if missing
    OPTIONAL_SECRETS = [
        "OPENWEATHER_API_KEY",
        "DATA_GOV_API_KEY_1",
        "AGMARKNET_API_KEY",
        "USDA_NASS_API_KEY",
        "KAGGLE_KEY",
    ]
    
    def __init__(self):
        """Initialize secrets manager with configured backend."""
        self._validate_backend()
        logger.info(f"Using secrets backend: {self.BACKEND}")
    
    def _validate_backend(self) -> None:
        """Validate that configured backend is available."""
        if self.BACKEND == "env":
            pass  # Always available
        elif self.BACKEND == "aws":
            try:
                import boto3  # noqa: F401
            except ImportError:
                logger.warning("AWS backend selected but boto3 not installed. Falling back to env.")
                self.BACKEND = "env"
        elif self.BACKEND == "vault":
            try:
                import hvac  # noqa: F401
            except ImportError:
                logger.warning("Vault backend selected but hvac not installed. Falling back to env.")
                self.BACKEND = "env"
        elif self.BACKEND == "azure":
            try:
                from azure.identity import DefaultAzureCredential  # noqa: F401
                from azure.keyvault.secrets import SecretClient  # noqa: F401
            except ImportError:
                logger.warning("Azure backend selected but azure-identity/azure-keyvault-secrets not installed. Falling back to env.")
                self.BACKEND = "env"
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret value from configured backend.
        
        Args:
            key: Secret key name
            default: Default value if secret not found
        
        Returns:
            Secret value or default
        
        Raises:
            ValueError: If backend returns error
        """
        if self.BACKEND == "env":
            return self._get_from_env(key, default)
        elif self.BACKEND == "aws":
            return self._get_from_aws(key, default)
        elif self.BACKEND == "vault":
            return self._get_from_vault(key, default)
        elif self.BACKEND == "azure":
            return self._get_from_azure(key, default)
        else:
            logger.warning(f"Unknown backend {self.BACKEND}, using env")
            return self._get_from_env(key, default)
    
    def _get_from_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from environment variables."""
        value = os.getenv(key, default)
        if value is None and key in self.REQUIRED_SECRETS:
            logger.warning(f"Required secret '{key}' not found in environment")
        return value
    
    def _get_from_aws(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            client = boto3.client("secretsmanager")
            try:
                response = client.get_secret_value(SecretId=key)
                return response.get("SecretString") or response.get("SecretBinary")
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    logger.warning(f"Secret '{key}' not found in AWS Secrets Manager")
                    return default
                raise
        except ImportError:
            logger.error("boto3 not installed. Cannot use AWS backend.")
            return default
        except Exception as e:
            logger.error(f"Failed to get secret from AWS: {e}")
            raise ValueError(f"AWS Secrets Manager error: {e}")
    
    def _get_from_vault(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from HashiCorp Vault."""
        try:
            import hvac
            
            vault_addr = os.getenv("VAULT_ADDR", "http://localhost:8200")
            vault_token = os.getenv("VAULT_TOKEN")
            vault_path = os.getenv("VAULT_PATH", "secret/agrosight")
            
            if not vault_token:
                logger.warning("VAULT_TOKEN not set. Cannot use Vault backend.")
                return default
            
            client = hvac.Client(url=vault_addr, token=vault_token)
            try:
                secret = client.secrets.kv.read_secret_version(path=vault_path)
                return secret["data"]["data"].get(key, default)
            except Exception as e:
                logger.warning(f"Secret '{key}' not found in Vault: {e}")
                return default
        except ImportError:
            logger.error("hvac not installed. Cannot use Vault backend.")
            return default
    
    def _get_from_azure(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from Azure Key Vault."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            from azure.core.exceptions import ResourceNotFoundError
            
            vault_url = os.getenv("AZURE_KEYVAULT_URL")
            if not vault_url:
                logger.warning("AZURE_KEYVAULT_URL not set. Cannot use Azure backend.")
                return default
            
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)
            try:
                secret = client.get_secret(key)
                return secret.value
            except ResourceNotFoundError:
                logger.warning(f"Secret '{key}' not found in Azure Key Vault")
                return default
        except ImportError:
            logger.error("azure-identity or azure-keyvault-secrets not installed. Cannot use Azure backend.")
            return default
    
    def validate_required(self) -> bool:
        """
        Validate that all required secrets are present.
        
        Returns:
            True if all required secrets are present
        
        Raises:
            ValueError: If any required secret is missing
        """
        missing = []
        for key in self.REQUIRED_SECRETS:
            if not self.get(key):
                missing.append(key)
        
        if missing:
            msg = f"Missing required secrets: {', '.join(missing)}. " \
                  f"Please set them in your environment or via {self.BACKEND} backend."
            logger.error(msg)
            raise ValueError(msg)
        
        logger.success(f"All {len(self.REQUIRED_SECRETS)} required secrets validated")
        return True
    
    def validate_optional(self) -> list[str]:
        """
        Check for optional secrets and warn if missing.
        
        Returns:
            List of missing optional secrets
        """
        missing = []
        for key in self.OPTIONAL_SECRETS:
            if not self.get(key):
                missing.append(key)
        
        if missing:
            logger.warning(f"Optional secrets not configured: {', '.join(missing)}. "
                          f"Some features may not work. Set them in your environment or {self.BACKEND} backend.")
        
        return missing


# Singleton instance
_secret_manager: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """Get or create the secret manager singleton."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager
