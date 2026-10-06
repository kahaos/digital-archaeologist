from digital_archaeologist.config import Settings

def test_settings_default_to_safe_local_sqlite_and_dry_run():
    settings = Settings()
    assert settings.database_url.startswith("sqlite:///")
    assert settings.dry_run is True
    assert settings.allow_side_effects is False

def test_database_url_can_be_overridden(monkeypatch):
    monkeypatch.setenv("DA_DATABASE_URL", "sqlite:////tmp/custom.db")
    assert Settings().database_url == "sqlite:////tmp/custom.db"

def test_repr_does_not_expose_api_secrets(monkeypatch):
    monkeypatch.setenv("DA_GITHUB_TOKEN", "super-secret-token")
    monkeypatch.setenv("DA_AI_API_KEY", "another-secret")
    rendered = repr(Settings())
    assert "super-secret-token" not in rendered
    assert "another-secret" not in rendered

def test_research_provider_model_is_configurable(monkeypatch):
    assert Settings().ai_model == "gpt-4o-mini"
    monkeypatch.setenv("DA_AI_MODEL", "custom-model")
    assert Settings().ai_model == "custom-model"

def test_discovery_sources_can_be_configured(monkeypatch):
    monkeypatch.setenv("DA_GITHUB_QUERIES", "abandoned saas,deprecated tool")
    monkeypatch.setenv("DA_WEB_SEEDS", "https://example.com,https://example.org")
    settings = Settings()
    assert settings.github_queries == ["abandoned saas", "deprecated tool"]
    assert settings.web_seed_urls == ["https://example.com", "https://example.org"]
