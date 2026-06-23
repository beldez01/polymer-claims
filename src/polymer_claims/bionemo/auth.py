from __future__ import annotations

import getpass
import os
import subprocess
from collections.abc import Callable, Mapping


def _default_runner(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def load_nvidia_api_key(
    *,
    service: str = "nvidia-build-api",
    account: str | None = None,
    runner: Callable[[list[str]], str] | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    """Return the NVIDIA build.nvidia.com API key.

    Order: macOS keychain (`security find-generic-password -s <service> -w`), then the
    `NVIDIA_API_KEY` env var. Never reads a dotfile. `runner`/`env` are injectable for tests.
    """
    runner = runner or _default_runner
    env = os.environ if env is None else env
    account = account or getpass.getuser()
    cmd = ["security", "find-generic-password", "-s", service, "-a", account, "-w"]
    try:
        out = runner(cmd).strip()
        if out:
            return out
    except Exception:  # noqa: BLE001 — keychain miss is expected; fall through to env
        pass
    env_key = env.get("NVIDIA_API_KEY", "").strip()
    if env_key:
        return env_key
    raise RuntimeError(
        "NVIDIA API key not found. Add it to the keychain:\n"
        f"  security add-generic-password -s {service} -a {account} -w <KEY>\n"
        "or set NVIDIA_API_KEY in the environment."
    )
