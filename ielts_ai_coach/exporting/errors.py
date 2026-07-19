"""Safe exporter exceptions that never carry source content."""


class ExporterError(Exception):
    """Base class for safe exporter failures."""


class ExportConfigurationError(ExporterError):
    """Raised when paths or command options are unsafe."""


class ExportDatabaseError(ExporterError):
    """Raised when a read-only source operation cannot complete."""


class ExportPrivacyError(ExporterError, ValueError):
    """Raised when a forbidden field reaches an export boundary."""


class ExportStateError(ExporterError):
    """Raised when the local state manifest cannot be trusted."""


class ExportWriteError(ExporterError):
    """Raised when an allowed output cannot be written atomically."""


class UnsupportedAdapterError(ExporterError):
    """Raised for adapters that are intentionally unavailable."""
