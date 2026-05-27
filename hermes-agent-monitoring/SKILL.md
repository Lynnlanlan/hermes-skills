---
name: hermes-agent-monitoring
description: Add external monitoring, status indicators, and observability hooks to Hermes Agent without modifying source code. Covers monkey-patch injection via tool modules, status file conventions, menu bar indicators, and watchdog patterns.
---

# Hermes Agent Monitoring

Monitor Hermes Agent state from outside the process — status indicators, heartbeat detection, crash notification. All hooks injected via monkey-patch in a tool module; zero modifications to Hermes source code.

## When to Use

- User wants a visual status indicator (menu bar light, LED, dashboard widget)
- User needs to know if Hermes is idle, working, or crashed without watching the terminal
- User wants crash/heartbeat-timeout detection with notification
- User asks for "agent status", "进程状态", "红绿灯", "heartbeat", "watchdog"

## How It Works

```
┌─────────────┐  write(working/heartbeat)  ┌──────────────────┐
│  Hermes     │ ───────────────────────────→│ agent_status.json│
│  (patched)  │                             │                  │
└─────────────┘                             └────────┬─────────┘
                                                     │ read (poll)
                                            ┌────────▼─────────┐
                                            │  Menubar / Widget │
                                            │  🟢🟡🔴           │
                                            └──────────────────┘
```

## Architecture

Three components, one status file:

| Component | Path | Role |
|-----------|------|------|
| `status.py` | `~/.hermes/traffic-light/status.py` | Constants, atomic file I/O |
| `hermes_heartbeat.py` | `~/.hermes/hermes-agent/tools/hermes_heartbeat.py` | Monkey-patches AIAgent to write status during turns |
| `menubar.py` | `~/.hermes/traffic-light/menubar.py` | rumps-based macOS menu bar app, polls status file |

All three read/write `~/.hermes/agent_status.json`.

See `references/implementation-files.md` for full file listing and the setup guide at `references/setup-guide.md` for a self-contained installation walkthrough.

## Injection Pattern

Create `~/.hermes/hermes-agent/tools/hermes_heartbeat.py`. The module gets auto-discovered by `tools/registry.py::discover_builtin_tools()`.

### AST Discovery Requirement

`discover_builtin_tools()` uses AST inspection to find top-level `registry.register()` calls. The call MUST be at module top level — NOT inside a function, NOT inside try/except.

```python
# CORRECT — bare call at module top level:
from tools.registry import registry
registry.register(
    name="hermes_heartbeat",
    toolset="utility",
    schema={...},
    handler=lambda args, **kw: '{"status": "ok"}',
    check_fn=lambda: True,
)
```

### Deferred Patching via `__import__` Hook (REQUIRED)

The naive approach — calling `_apply_patch()` at module import time — fails because `model_tools` (which triggers `discover_builtin_tools()`) is lazy-imported on the first user message. At that point, `run_agent` may or may not be available. When it's NOT available, `from run_agent import AIAgent` raises `ImportError`, which `_apply_patch()` silently catches and returns — the patch is never retried.

**Solution:** Wrap `builtins.__import__` with a hook that fires when `run_agent` is later imported. This handles both cases: if run_agent is already cached, the initial `_apply_patch()` call at module bottom succeeds through the hook; if not yet loaded, the hook catches it later.

```python
import builtins
_original_import = builtins.__import__
_patching_in_progress = False  # recursion guard

def _patched_import(name, *args, **kwargs):
    module = _original_import(name, *args, **kwargs)
    global _patching_in_progress
    if name == "run_agent" and not _patch_applied and not _patching_in_progress:
        _patching_in_progress = True
        try:
            _apply_patch()
        finally:
            _patching_in_progress = False
    return module

builtins.__import__ = _patched_import
_apply_patch()  # try immediately (run_agent might be cached)
```

**Critical: use `import builtins`, NOT `__builtins__`.** In non-`__main__` modules, `__builtins__` can be `builtins.__dict__` (a plain dict) rather than the `builtins` module. `__builtins__.__import__` raises `AttributeError: 'dict' object has no attribute '__import__'`.

**Critical: recursion guard is mandatory.** `_apply_patch()` itself does `from run_agent import AIAgent`, which re-enters the `__import__` hook → calls `_apply_patch()` again → `RecursionError`. The `_patching_in_progress` flag skips the hook during re-entrant calls.

### Entry Point: run_conversation

The real conversation loop lives in `agent/conversation_loop.py`, but `AIAgent.run_conversation` (in `run_agent.py`) is a thin forwarder that the gateway calls. Patch this forwarder:

```python
_original_run = AIAgent.run_conversation

def _patched_run_conversation(self, user_message, *args, **kwargs):
    write_status("working", f"处理中: {user_message[:80]}")
    try:
        result = _original_run(self, user_message, *args, **kwargs)
        write_status("idle", "就绪")
        return result
    except Exception as e:
        write_status("error", str(e), error_type="crash")
        raise

AIAgent.run_conversation = _patched_run_conversation
```

### Intermediate Heartbeats & Crash Detection

Patch `AIAgent.__init__` to inject a `status_callback` for per-tool-call heartbeats, and register `atexit` to detect crashes:

```python
def _patched_init(self, *args, **kwargs):
    _original_init(self, *args, **kwargs)
    self.status_callback = _status_callback
    write_status("idle", "Hermes 已就绪")

atexit.register(_on_atexit)  # writes "error" if process died in "working" state
```

## Status File Format

`~/.hermes/agent_status.json`:

```json
{
  "status": "idle",
  "message": "就绪",
  "last_heartbeat": "2026-05-27T14:30:00",
  "last_error": null,
  "error_detail": null,
  "turn_id": null,
  "updated_at": "2026-05-27T14:30:05"
}
```

Status values: `idle`, `working`, `error`.
Error types: `heartbeat_timeout`, `turn_timeout`, `api_failure`, `loop_detect`, `crash`.

### Timing Thresholds

| Threshold | Value | Triggers |
|-----------|-------|----------|
| Heartbeat timeout | 60s | Process crash or unresponsive |
| Turn timeout | 300s | Dead loop or stuck task |
| API failures | 3 consecutive | Network/API issues |
| Loop detection | 10 same-tool calls | Infinite loop |

## macOS Menu Bar App

Use `rumps` for a lightweight menu bar indicator.

### Polling & Debouncing

- Poll interval: **5 seconds**
- Yellow minimum hold: **5 seconds** — prevents flash on quick turns
- Red transitions: **instant**
- Green from idle: **instant**

### Fast-Turn Detection

If a turn completes in <5 seconds, the status file writes `working` then `idle` between two polling intervals. The menubar never sees `working` and stays green.

**Fix:** Track `updated_at` from the status file across polls. If the timestamp changed but status is always `idle`, a turn happened in the gap — manually trigger the yellow hold with 5-second minimum:

```python
self._last_updated_at = None  # track file timestamp across polls

def _poll(self, _):
    file_updated = data.get("updated_at")
    if (raw_status == "idle"
            and self.current_status not in ("working",)
            and not self._pending_green
            and self._last_updated_at is not None
            and file_updated != self._last_updated_at):
        self._yellow_since = now
        self._pending_green = True  # triggers 5s yellow hold
    if file_updated:
        self._last_updated_at = file_updated
```

### Menu Items

- **状态详情** — current status, last heartbeat, error info
- **为什么亮红灯** — diagnostic panel with error type, timestamp, suggested cause
- **清除错误状态** — manual reset to idle

### Auto-Start on Login

Use `launchctl bootstrap` for GUI apps (not `launchctl load`):

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hermes.traffic-light.plist
```

Plist must include `RunAtLoad` and `KeepAlive`.

## Pitfalls

1. **Gateway must be restarted after creating `hermes_heartbeat.py`.** Tools are discovered at startup only. A gateway running since before the file was created will never load it. Confirm by comparing gateway start time with file modification time:
   ```bash
   ps -p $(pgrep -f 'hermes gateway') -o lstart=
   ls -la ~/.hermes/hermes-agent/tools/hermes_heartbeat.py
   ```

2. **Silent failure: status file frozen at old timestamp.** If `updated_at` never changes across multiple turns, the heartbeat module isn't loaded. Check the log: `grep '红绿灯心跳注入已激活' ~/.hermes/logs/agent.log`. If absent, the module wasn't imported or the patch failed.

3. **Patch activated but `run_conversation` never fires (gateway background-task path).** The log says "红绿灯心跳注入已激活" but the status file stays frozen at idle through multiple turns. This means the patched `AIAgent.run_conversation` is not being called, despite the patch registering successfully. The gateway processes CLI messages via `_handle_background_command` → `_run_background_task`, which creates `AIAgent` and calls `run_conversation` in a thread executor. If this code path uses a different `AIAgent` reference than the one patched by the heartbeat module, the proxy is silently bypassed. **Diagnosis:** add `logger.info()` calls at the top of `_patched_run_conversation` and `_patched_init`, restart gateway, and check if those log lines appear during a turn. If they don't appear, the patch target and execution path are disconnected. See `references/troubleshooting.md` for detailed diagnostic steps.

3. **Use `import builtins`, not `__builtins__`.** In non-main module scope, `__builtins__` is a dict, causing `AttributeError` on `__builtins__.__import__`.

4. **Import hook needs recursion guard.** Without `_patching_in_progress`, `_apply_patch()` → `from run_agent` → hook → `_apply_patch()` → infinite recursion.

5. **Delete stale `.pyc` files after editing the heartbeat module.** Before restarting gateway: `find ~/.hermes/hermes-agent/__pycache__ -name '*hermes_heartbeat*' -delete`.

6. **Menubar dies when gateway gets SIGTERM.** The gateway tracks child processes and terminates them on shutdown. After gateway restart, re-check menubar: `pgrep -fl menubar || restart_it`. The launchd plist's `KeepAlive` handles crashes but NOT intentional shutdown.

7. **AST discovery: `registry.register()` must be bare at module top level.** No try/except, no function body wrapping.

8. **Multiple menubar instances conflict.** Kill old processes (`pgrep -f menubar.py`) before starting new ones.

9. **`launchctl load` doesn't work for GUI menubar apps on macOS 26+.** Use `launchctl bootstrap gui/$UID`.

## Related Skills

- `macos-power-management` — keeping the Mac awake so monitoring stays alive
- `macos-gateway-uptime` — similar pattern of keeping a background service running

## References

- `references/implementation-files.md` — complete file listing and format specs
- `references/setup-guide.md` — self-contained installation walkthrough for sharing with others
