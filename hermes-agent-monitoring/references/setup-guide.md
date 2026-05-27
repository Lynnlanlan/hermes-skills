# Hermes Agent 红绿灯 — 安装指南

自包含的安装包，可以分享给其他 Hermes 用户。

## 前提条件

- macOS 系统
- Hermes Agent 已安装
- Python 环境和 `pip`

## 快速安装

1. 安装依赖：`pip install rumps`
2. 创建目录：`mkdir -p ~/.hermes/traffic-light`
3. 将以下文件放入对应位置（参见教程正文的完整代码）：

| 文件 | 位置 |
|------|------|
| `status.py` | `~/.hermes/traffic-light/status.py` |
| `menubar.py` | `~/.hermes/traffic-light/menubar.py` |
| `start.sh` | `~/.hermes/traffic-light/start.sh` |
| `hermes_heartbeat.py` | `~/.hermes/hermes-agent/tools/hermes_heartbeat.py` |
| plist | `~/Library/LaunchAgents/com.hermes.traffic-light.plist` |

4. 加载自动启动：
   ```bash
   chmod +x ~/.hermes/traffic-light/start.sh
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hermes.traffic-light.plist
   ```

5. 清理缓存并重启 gateway：
   ```bash
   find ~/.hermes/hermes-agent/tools/__pycache__ -name '*hermes_heartbeat*' -delete
   find ~/.hermes/hermes-agent/__pycache__ -name '*model_tools*' -delete
   kill $(pgrep -f "hermes gateway run")
   # 然后通过桌面 app 重新启动 gateway
   ```

6. 验证：
   ```bash
   pgrep -fl menubar
   grep '红绿灯心跳注入已激活' ~/.hermes/logs/agent.log
   cat ~/.hermes/agent_status.json
   ```

## 完整代码

所有代码内嵌在桌面文件 `~/Desktop/Hermes红绿灯安装指南.md` 中。该文件包含完整的 status.py、menubar.py、hermes_heartbeat.py、启动脚本和 plist 配置。

## 调试清单

如果安装后不工作：

1. **一直绿灯，不见黄灯** → 检查 `grep '红绿灯心跳注入已激活' ~/.hermes/logs/agent.log`。如果没有，说明心跳模块没加载 → 检查 gateway 是否重启，pyc 是否清理
2. **menubar 不显示** → `pip install rumps`，检查 launchd：`launchctl print gui/$(id -u)/com.hermes.traffic-light`
3. **红灯常亮** → 右键菜单 → "为什么亮红灯" 查看原因，或 "清除错误状态"
4. **状态文件时间戳不变** → 心跳模块未生效，按步骤 5 重试
