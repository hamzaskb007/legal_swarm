from __future__ import annotations


class ValidationError(Exception):
    """Base exception for all validation-layer errors."""


class ValidationConfigurationError(ValidationError):
    """Raised when the validation engine or a validator is misconfigured."""


class ValidationModelError(ValidationError):
    """Raised when a validation model receives invalid or corrupt data."""


class ValidationExecutionError(ValidationError):
    """Raised when a validation run fails unexpectedly at runtime."""


class ValidationContextError(ValidationError):
    """Raised when the validation context is invalid or incomplete."""


class ValidationResultError(ValidationError):
    """Raised when building or processing a validation result fails."""
