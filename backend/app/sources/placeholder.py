from __future__ import annotations

from app.sources.base import SourceAdapterBase


class StaticSourceAdapter(SourceAdapterBase):
    def __init__(
        self,
        name: str,
        slug: str,
        kind: str,
        current_mode: str,
        notes: str,
        official_api_available: str = "unknown",
        automation_allowed: str = "unknown",
        terms_reviewed: bool = False,
    ) -> None:
        self.name = name
        self.slug = slug
        self.kind = kind
        self.current_mode = current_mode
        self.limitations = notes
        self.official_api_available = official_api_available
        self.automation_allowed = automation_allowed
        self.terms_reviewed = terms_reviewed
