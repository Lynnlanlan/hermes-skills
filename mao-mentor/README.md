# 教员 Skill — 安装指南

## 这是什么

一个基于《毛泽东文集》（1-8卷）的人生咨询 Hermes Skill。
当你遇到困惑、决策、矛盾时，以教员的思维方式帮你分析问题。

触发词：`教员` / `请问教员` / `如果是教员`

## 安装方法

### 1. 复制 skill 文件

```bash
mkdir -p ~/.hermes/skills/life/mao-mentor/references
cp SKILL.md ~/.hermes/skills/life/mao-mentor/
cp references/topic_index.json ~/.hermes/skills/life/mao-mentor/references/
cp references/all_titles.txt ~/.hermes/skills/life/mao-mentor/references/
```

### 2. 准备知识基座（二选一）

**方案A：从 PDF 自动提取（推荐）**

将《毛泽东文集》1-8 卷 PDF 放到一个目录，然后运行：

```bash
pip install pymupdf
python3 scripts/extract_volumes.py /path/to/pdf/dir ~/.hermes/skills/life/mao-mentor/references/
```

**方案B：手动复制**

如果你已经有提取好的 vol1.txt ~ vol8.txt，直接复制：

```bash
cp vol*.txt ~/.hermes/skills/life/mao-mentor/references/
```

### 3. 验证

在 Hermes 中说：`教员，你好`

应该收到以教员 persona 的回复。

## 文件结构

```
~/.hermes/skills/life/mao-mentor/
├── SKILL.md                    # 主文件
├── references/
│   ├── vol1.txt ~ vol8.txt     # 文集全文（提取后）
│   ├── topic_index.json        # 11个主题索引
│   └── all_titles.txt          # 文章标题列表
└── scripts/
    └── extract_volumes.py      # PDF提取脚本
```

## 注意事项

- 文集6 是扫描版，需要 tesseract OCR（`brew install tesseract` + 中文语言包）
- 其他 7 卷是文字型 PDF，pymupdf 直接提取
- 文集 ≠ 选集：《矛盾论》《实践论》等经典在选集中，文集中只有间接引用
