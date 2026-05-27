# Implementation Files Reference

## Files Created (2026-05-27, user Lynnlanlan)

### Status helpers — `~/.hermes/traffic-light/status.py`
Constants (thresholds, error types), atomic file write via tmp+rename, heartbeat helpers, `check_heartbeat_timeout()`, `check_hermes_alive()`.

### Heartbeat injection — `~/.hermes/hermes-agent/tools/hermes_heartbeat.py`
Tool module that monkey-patches `AIAgent`:
- Wraps `builtins.__import__` with deferred patching (handles `model_tools`-before-`run_agent` import order)
- Patches `AIAgent.__init__` to inject `status_callback`
- Patches `AIAgent.run_conversation` for turn-start (`working`) / turn-end (`idle`)
- `atexit` handler: writes `error` if process exits in `working` state
- Error detection: API failures (3 consecutive), loop detection, crash signals
- Top-level `registry.register()` for AST-based tool discovery

**Key design decisions:**
- Uses `import builtins` (not `__builtins__`) because `__builtins__` is a dict in module scope
- Recursion guard `_patching_in_progress` prevents infinite recursion when `_apply_patch()` imports `run_agent`
- `_apply_patch()` is idempotent — checks `_patch_applied` first
- Called twice: once at module bottom (for cached run_agent), once via import hook (for lazy-loaded run_agent)

### Menubar app — `~/.hermes/traffic-light/menubar.py`
rumps-based macOS menu bar app (334 lines):
- 5-second poll interval
- 5-second yellow minimum hold (debounce)
- **Fast-turn detection**: tracks `_last_updated_at` across polls; if timestamp changes but status stays `idle`, simulates yellow hold (catches sub-5-second turns that complete between polls)
- Watchdog: heartbeat timeout→red at 60s, turn timeout→red at 300s
- Menu items: 状态详情, 为什么亮红灯, 清除错误状态
- Icons: 🟢 idle, 🟡 working, 🔴 error, ⚪ unknown

### Auto-start — `~/Library/LaunchAgents/com.hermes.traffic-light.plist`
Launchd plist loaded via `launchctl bootstrap gui/$UID`. Uses `RunAtLoad` + `KeepAlive`.

### Helper scripts
- `~/.hermes/traffic-light/start.sh` — launch wrapper (resolves venv python path)
- `~/.hermes/traffic-light/hermes-traffic-light.command` — double-click launcher

## PawPal Safety

User has PawPal desktop pet at `/Applications/PawPal.app` (Electron, 4 processes). Our `pgrep -f "menubar.py"` patterns never match "PawPal". No interaction risk.

## State File

`~/.hermes/agent_status.json` — single source of truth. Format:

```json
{
  "status": "idle|working|error",
  "message": "human-readable",
  "last_heartbeat": "ISO timestamp or null",
  "last_error": "message or null",
  "error_detail": {"type": "...", "detail": "...", "at": "..."} or null,
  "turn_id": "uuid or null",
  "updated_at": "ISO timestamp"
}
```

## Debugging Lessons (2026-05-27)

The heartbeat module went through 4+ debug cycles before working:

1. **Gateway runtime mismatch**: Gateway started May 23, heartbeat created May 27. `ps -p PID -o lstart=` revealed the gateway predated the module by 4 days.
2. **`__builtins__` crash**: `AttributeError: 'dict' object has no attribute '__import__'`. Fixed by using `import builtins`.
3. **Infinite recursion**: `_apply_patch()` imports `run_agent` → hook fires → `_apply_patch()` again. Fixed with `_patching_in_progress` guard.
4. **Stale `.pyc`**: After multiple file edits, old bytecode prevented the updated module from loading. Fixed with `find -name '*hermes_heartbeat*' -delete`.

Diagnosis checklist when status file is frozen:
1. `cat ~/.hermes/agent_status.json` — if `updated_at` never changes, module isn't working
2. `grep '红绿灯心跳注入已激活' ~/.hermes/logs/agent.log` — must appear for each gateway start
3. `ps -p PID -o lstart=` vs `ls -la tools/hermes_heartbeat.py` — gateway must have started AFTER file creation
4. `find tools/__pycache__ -name '*hermes_heartbeat*'` — delete any stale bytecode
