# Hermes Agent Skills Collection

自定义 [Hermes Agent](https://github.com/NousResearch/hermes-agent) skills，覆盖思考工具、人生咨询、系统监控三个维度。

## Skills

### 🧠 思考工具

| Skill | 描述 | 触发词 |
|-------|------|--------|
| [nobody](nobody/) | 魔鬼代言人 — 从反面论证你的判断，指出盲区和遗漏 | `NObody`、`反方怎么看`、`devil's advocate` |
| [grill-me](grill-me/) | 苏格拉底式深度拷问 — 10个维度逼你想透一个问题 | `grill me about X`、`拷问我` |

### 📚 知识/文化

| Skill | 描述 | 触发词 |
|-------|------|--------|
| [mao-mentor](mao-mentor/) | 以毛泽东文集为知识基座的人生咨询。教员以温和儒雅长者的身份，引用原文并用思想框架帮你分析 | `教员`、`请问教员` |

### 🔧 系统工具

| Skill | 描述 | 触发词 |
|-------|------|--------|
| [hermes-agent-monitoring](hermes-agent-monitoring/) | Hermes Agent 外部状态监控 — 红绿灯指示器、心跳检测、macOS 菜单栏应用 | `agent status`、`进程状态`、`红绿灯` |

## 安装

```bash
# 克隆
git clone https://github.com/liuyilan/hermes-skills.git

# 复制到 Hermes skills 目录
cp -r hermes-skills/nobody ~/.hermes/skills/productivity/
cp -r hermes-skills/grill-me ~/.hermes/skills/productivity/
cp -r hermes-skills/mao-mentor ~/.hermes/skills/life/
cp -r hermes-skills/hermes-agent-monitoring ~/.hermes/skills/devops/

# 重新加载
hermes skills list  # 确认已加载
```

## 许可

MIT
