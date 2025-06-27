# Kali tools utilities

This module provides asynchronous wrappers around common security tools. Each helper simply builds the command
and runs it with `asyncio.create_subprocess_exec`. Examples include `nmap`, `hydra`, cracking tools and forensic
utilities. They return the captured standard output or an error message.

Available functions:

- `run_nmap`
- `run_hydra`
- `bruteforce_ssh`
- `run_sqlmap`
- `run_msfconsole`
- `run_burpsuite`
- `run_aircrack`
- `run_wireshark`
- `run_john`
- `run_hashcat`
- `run_crunch`
- `run_yara`
- `run_volatility`
- `run_mitmproxy`

`run_yara`, `run_volatility` and `run_mitmproxy` depend on optional utilities.
List these in a module's `required_packages` so Jarvis can fall back to safe
mode when they are unavailable.

- **YARA** – signature heuristics scanning.
  ```python
  await run_yara("rules.yar", "suspect.bin")
  ```
- **Volatility** – analyse memory dumps.
  ```python
  await run_volatility("mem.img", "pslist")
  ```
- **mitmproxy** – intercept traffic for training or manual analysis.
  ```python
  await run_mitmproxy("-p 8080")
  ```

## Updating allowed networks

Allowed target networks are read from `config/config.yaml` when the module is
imported. To apply changes without restarting Jarvis simply call:

```python
from modules import kali_tools
kali_tools.reload_allowed_networks()
```

The function reloads the CIDR list from the configuration or the
`JARVIS_ALLOWED_NETWORKS` environment variable.
