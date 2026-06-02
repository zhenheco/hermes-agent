import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig


def _discord_enabled_without_token_config() -> GatewayConfig:
    config = GatewayConfig()
    config.platforms[Platform.DISCORD] = PlatformConfig(enabled=True, token="")
    return config


def test_missing_required_platform_tokens_reports_discord_token():
    import gateway.run as gateway_run

    missing = gateway_run._missing_required_platform_tokens(
        _discord_enabled_without_token_config()
    )

    assert missing == ["discord: DISCORD_BOT_TOKEN"]


@pytest.mark.asyncio
async def test_start_gateway_fails_before_runner_when_required_token_missing(monkeypatch):
    import gateway.run as gateway_run

    state_updates = []

    monkeypatch.setenv("HERMES_GATEWAY_REQUIRE_CONFIGURED_PLATFORM_TOKENS", "1")
    monkeypatch.setattr("gateway.status.get_running_pid", lambda: None)
    monkeypatch.setattr("tools.skills_sync.sync_skills", lambda quiet=True: None)
    monkeypatch.setattr("hermes_logging.setup_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        "gateway.status.write_runtime_status",
        lambda **kwargs: state_updates.append(kwargs),
    )
    monkeypatch.setattr(
        gateway_run,
        "load_gateway_config",
        lambda: _discord_enabled_without_token_config(),
    )
    monkeypatch.setattr(
        gateway_run,
        "GatewayRunner",
        lambda config=None: (_ for _ in ()).throw(
            AssertionError("GatewayRunner must not start without required tokens")
        ),
    )

    assert await gateway_run.start_gateway() is False
    assert state_updates[-1]["gateway_state"] == "startup_failed"
    assert "DISCORD_BOT_TOKEN" in state_updates[-1]["exit_reason"]
