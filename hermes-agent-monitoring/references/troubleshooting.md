# Traffic Light Troubleshooting

## Symptom: 红绿灯一直绿，不亮黄

### Step 1: 检查状态文件是否在更新

```bash
cat ~/.hermes/agent_status.json | python3 -m json.tool
```

如果 `updated_at` 时间戳停滞（不随对话更新），说明心跳模块没在工作。

### Step 2: 区分"模块未加载"和"patch 未触发"

如果 Step 1 发现 `updated_at` 停滞，有两种可能：
- **A) 模块从未加载** → gateway 日志中找不到 "红绿灯心跳注入已激活"
- **B) 模块加载了、patch 也激活了，但 patched 函数从未被调用** → 日志中有 "红绿灯心跳注入已激活"，但状态文件还是不动

先确认是哪一种：

```bash
# 检查 patch 是否激活
grep '红绿灯心跳注入已激活' ~/.hermes/logs/agent.log | tail -1
```

**如果是 B 的情况：** 说明 monkey-patch 注册成功，但 gateway 实际执行路径绕过了 patched 类。最常见的原因：gateway 的 `_handle_background_command` → `_run_background_task` 在处理 CLI 消息时创建的 AIAgent 实例调用的 `run_conversation` 不是被 heartbeat 模块 patch 的那个类引用。

**诊断方法：** 在 `hermes_heartbeat.py` 的 patched 函数内加 logger 调用：

```python
# 在 _patched_run_conversation 顶部
logger.info("hermes_heartbeat: _patched_run_conversation CALLED session=%s",
            getattr(self, 'session_id', '?'))

# 在 _patched_init 中
logger.info("hermes_heartbeat: _patched_init CALLED session=%s",
            getattr(self, 'session_id', '?'))
```

清除 `.pyc` 缓存后重启 gateway，发一条消息，然后检查日志：

```bash
grep 'hermes_heartbeat.*CALLED' ~/.hermes/logs/agent.log
```

如果日志中没有任何 CALLED 行，说明 patched 函数从未被调用。进一步验证函数引用：

```python
# 在 _apply_patch 成功激活后添加
logger.info("hermes_heartbeat: AIAgent.run_conversation = %s (id=%s)",
            AIAgent.run_conversation, id(AIAgent.run_conversation))
```

然后在 gateway 代码中（`gateway/run.py::_run_background_task`）打印相同的函数 id，对比两个 id 是否一致。

### Step 3: 检查 gateway 启动时间 vs 模块创建时间

```bash
# Gateway 什么时候启动的？
ps -p $(pgrep -f 'hermes gateway') -o lstart=

# 心跳模块什么时候创建的？
ls -la ~/.hermes/hermes-agent/tools/hermes_heartbeat.py
```

如果 gateway 启动时间 < 文件创建时间，工具从未被加载 → **重启 gateway**。

### Step 4: 验证模块可导入（含 import-order 陷阱）

```bash
cd ~/.hermes/hermes-agent
venv/bin/python -c "
import sys; sys.path.insert(0, '.')
import tools.hermes_heartbeat
print('patch_applied:', tools.hermes_heartbeat._patch_applied)
"
```

⚠️ 独立测试中 `_patch_applied` 可能为 True（因为 `run_agent` 在测试中可直接导入），但在真实 gateway 中仍为 False（因为 `model_tools` 先于 `run_agent` 加载）。需要用以下方式验证真实 gateway 中的状态：

```bash
# 检查 agent.log 中是否有 '红绿灯心跳注入已激活'
grep '红绿灯心跳注入已激活' ~/.hermes/logs/agent.log | tail -1

# 如果无输出，说明 patch 从未成功。检查 import 顺序：
grep -n 'discover_builtin\|run_agent' ~/.hermes/logs/agent.log | head -5
```

**常见陷阱：`__builtins__` 导致 `AttributeError: 'dict' object has no attribute '__import__'`**

在非 `__main__` 模块中，`__builtins__` 可能是 `builtins.__dict__`（dict）而不是 `builtins` 模块。访问 `__builtins__.__import__` 会崩溃。必须用 `import builtins; builtins.__import__`。

**递归陷阱：** `_apply_patch()` 内部有 `from run_agent import AIAgent`，会再次进入 `_patched_import` 钩子。不加递归保护会导致 `RecursionError`。使用 `_patching_in_progress` 布尔标志防止重入。

### Step 5: 验证 patch 确实生效

```bash
cd ~/.hermes/hermes-agent
venv/bin/python -c "
import sys; sys.path.insert(0, '.')
import tools.hermes_heartbeat
from run_agent import AIAgent
import inspect
src = inspect.getsource(AIAgent.run_conversation)
print('PATCHED' if 'STATUS_WORKING' in src else 'NOT PATCHED')
"
```

### Step 6: 终极诊断 — stderr 标记

如果以上步骤都通过但 gateway 中 patch 还是不生效，在 `hermes_heartbeat.py` 模块顶层加 stderr 打印来确认模块是否被加载：

```python
# 模块加载标记
print("[HERMES_HEARTBEAT] Module loaded, sys.modules has run_agent:",
      "run_agent" in sys.modules, file=sys.stderr, flush=True)
```

然后在 agent.log 中搜索 `HERMES_HEARTBEAT`。如果没有输出，说明模块根本没被 `discover_builtin_tools()` 导入——检查 AST 发现是否通过：

```bash
cd ~/.hermes/hermes-agent
venv/bin/python -c "
from tools.registry import _module_registers_tools
from pathlib import Path
print(_module_registers_tools(Path('tools/hermes_heartbeat.py')))
"
```

## Symptom: 所有修复都做了但心跳仍不工作（模块未被加载）

这是最棘手的情况——AST 扫描通过、独立测试通过、import hook 代码正确，但运行中的 gateway 就是不加载模块。

### 终极诊断：marker 文件法

由于 stderr 可能被 gateway 的日志系统截获或重定向到不同文件，更可靠的方法是在模块顶层写一个 marker 文件：

```python
# 在 hermes_heartbeat.py 模块顶层
from pathlib import Path
_marker = Path.home() / ".hermes" / "heartbeat_loaded.marker"
try:
    _marker.write_text(f"loaded\n")
except Exception:
    pass
```

测试流程：
```bash
# 1. 删除旧 marker
rm -f ~/.hermes/heartbeat_loaded.marker

# 2. 重启 gateway
kill $(pgrep -f "hermes gateway run")
hermes gateway run --replace &

# 3. 发一条消息触发 lazy import

# 4. 检查 marker
cat ~/.hermes/heartbeat_loaded.marker
```

如果 marker 不存在，说明 `discover_builtin_tools()` 没有导入该模块。可能原因：
- 工具文件不在正确的 `tools/` 目录
- AST 发现失败（检查 `_module_registers_tools()` 返回值）
- 文件权限问题
- gateway 进程使用的 Python 环境不同
- **`.pyc` 缓存污染**（最常见但最难排查）：之前的导入尝试编译了 broken `.pyc`，后续导入直接用缓存而不重新编译源码。清除方法：

```bash
find ~/.hermes/hermes-agent/tools/__pycache__ -name '*hermes_heartbeat*' -delete
find ~/.hermes/hermes-agent/__pycache__ -name '*model_tools*' -delete
```

清除 `.pyc` 后必须重启 gateway 才能触发重新编译导入。

如果 turn 在 5 秒内完成，且两次 polling 之间正好跳过了 `working` 状态：

```
t=0  轮询: idle → 绿灯
t=1  发消息，心跳写 working
t=2  回复完毕，心跳写 idle
t=5  轮询: idle → 还是绿灯（从未见过 working）
```

**修复：** menubar 通过追踪 `updated_at` 时间戳变化来检测快闪 turn。如果两次轮询间 `updated_at` 变了但状态始终 idle，说明有 turn 在间隙中完成，主动亮黄灯 5 秒。

见 `menubar.py` 中 `_last_updated_at` 和 `_poll()` 的快闪检测逻辑。

## Symptom: menubar 进程不在了

### 原因 1：gateway 重启导致 menubar 被连带杀死

Gateway 通过 `tools/process_registry` 追踪后台进程，shutdown 时会清理子进程。每次 gateway 重启后都需要检查 menubar：

```bash
pgrep -fl menubar || echo "menubar 未运行"
```

### 原因 2：launchd 未自动重启

```bash
# 检查 launchd 状态
launchctl list | grep com.hermes.traffic-light

# 手动启动
cd ~/.hermes/traffic-light
~/.hermes/hermes-agent/venv/bin/python menubar.py &

# 或重新 bootstrap
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hermes.traffic-light.plist
```

**最佳实践：** 每次 gateway 重启后，用以下一行命令确保 menubar 运行：

```bash
pgrep -fl menubar >/dev/null || (cd ~/.hermes/traffic-light && ~/.hermes/hermes-agent/venv/bin/python menubar.py &)
```
