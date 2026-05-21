"""Audit service scaffolding."""

from services.audit.records import AuditRecord, InMemoryAuditRecorder

__all__ = ["AuditRecord", "InMemoryAuditRecorder"]
