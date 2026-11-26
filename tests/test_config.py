import pytest

from assistant_app.config import DEFAULT_MODEL, ConfigError, Settings, load_settings


def test_empty_environment_gives_safe_defaults():
    settings = load_settings({})
    assert settings.openai_api_key is None
    assert settings.openai_model == DEFAULT_MODEL
    assert settings.timeout_seconds == 20.0
    assert settings.max_retries == 2


def test_values_are_read_and_parsed():
    settings = load_settings(
        {
            "OPENAI_API_KEY": " sk-test ",
            "OPENAI_MODEL": "my-model",
            "OPENAI_TIMEOUT_SECONDS": "5.5",
            "OPENAI_MAX_RETRIES": "1",
        }
    )
    assert settings.openai_api_key == "sk-test"
    assert settings.openai_model == "my-model"
    assert settings.timeout_seconds == 5.5
    assert settings.max_retries == 1


def test_blank_key_means_no_key():
    assert load_settings({"OPENAI_API_KEY": "   "}).openai_api_key is None


def test_non_numeric_timeout_is_rejected():
    with pytest.raises(ConfigError, match="OPENAI_TIMEOUT_SECONDS"):
        load_settings({"OPENAI_TIMEOUT_SECONDS": "soon"})


def test_out_of_range_retries_is_rejected():
    with pytest.raises(ConfigError, match="OPENAI_MAX_RETRIES"):
        load_settings({"OPENAI_MAX_RETRIES": "50"})


def test_key_is_hidden_from_repr():
    assert "sk-secret" not in repr(Settings(openai_api_key="sk-secret"))
