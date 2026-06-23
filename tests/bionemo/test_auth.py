import pytest
from polymer_claims.bionemo.auth import load_nvidia_api_key


def test_loads_key_from_keychain_runner():
    def fake_runner(cmd):
        assert cmd[0] == "security"
        assert "find-generic-password" in cmd
        return "kc-secret-123\n"
    key = load_nvidia_api_key(runner=fake_runner, env={})
    assert key == "kc-secret-123"


def test_falls_back_to_env_when_keychain_misses():
    def fake_runner(cmd):
        raise FileNotFoundError("security miss")
    key = load_nvidia_api_key(runner=fake_runner, env={"NVIDIA_API_KEY": "env-secret"})
    assert key == "env-secret"


def test_raises_when_neither_source_has_key():
    def fake_runner(cmd):
        raise FileNotFoundError("security miss")
    with pytest.raises(RuntimeError, match="NVIDIA API key"):
        load_nvidia_api_key(runner=fake_runner, env={})
