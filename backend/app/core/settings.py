from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Gigged Glasgow"
    environment: str = "local"
    database_url: str = "sqlite:///./gigged_glasgow.db"
    backend_cors_origins: str = "http://localhost:3000"
    admin_api_key: str = "change-me-in-production"
    ticketmaster_api_key: str | None = None
    eventbrite_api_key: str | None = None
    songkick_api_key: str | None = None
    bandsintown_app_id: str | None = None
    skiddle_source_settings: str | None = None
    gigs_in_scotland_source_settings: str | None = None
    whats_on_glasgow_source_settings: str | None = None
    manual_events_csv_path: str | None = "seeds/manual_events.csv"
    instagram_handle: str | None = None
    meta_app_id: str | None = None
    meta_app_secret: str | None = None
    facebook_page_id: str | None = None
    meta_access_token: str | None = None
    instagram_business_account_id: str | None = None
    meta_graph_api_version: str = "v20.0"
    meta_publishing_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
