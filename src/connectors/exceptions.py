from __future__ import annotations


class ConnectorError(Exception):
    """Base exception for all connector-related errors."""


class ConnectorConfigurationError(ConnectorError):
    """Raised when a connector is misconfigured."""


class UnsupportedConnectorError(ConnectorError):
    """Raised when a requested connector type is not supported."""


class ConnectorRegistrationError(ConnectorError):
    """Raised when connector registration fails (duplicate, invalid)."""


class ConnectorInitializationError(ConnectorError):
    """Raised when a connector fails to initialize."""


class ConnectionError(ConnectorError):
    """Raised when a connector fails to connect."""


class CapabilityError(ConnectorError):
    """Raised when a connector does not support a required capability."""
