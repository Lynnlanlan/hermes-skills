# 教员 Skill — 知识基座构建记录

## PDF 来源

毛泽东文集 1-8 卷，中共中央文献研究室编，人民出版社。

| 卷 | 文件名 | 类型 | 页数 | 提取方式 |
|----|--------|------|------|----------|
| 1 | 毛泽东文集1.pdf | 文字型 | 528 | pymupdf |
| 2 | 毛泽东文集2.pdf | 文字型 | 483 | pymupdf |
| 3 | 毛泽东文集3.pdf | 文字型 | 469 | pymupdf |
| 4 | 毛泽东文集4.pdf | 文字型 | 356 | pymupdf |
| 5 | 毛泽东文集5.pdf | 文字型 | 365 | pymupdf |
| 6 | 06、毛泽东文集（第六卷）...pdf | 扫描版 | 530 | tesseract OCR |
| 7 | 毛泽东文集7.pdf | 文字型 | 476 | pymupdf |
| 8 | 毛泽东文集8.pdf | 文字型 | 459 | pymupdf |

## 提取步骤

### 文字型 PDF（卷1-5, 7-8）

```python
import pymupdf, re

def clean_text(text):
    text = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return '\n'.join(l.strip() for l in text.split('\n'))

doc = pymupdf.open('毛泽东文集1.pdf')
with open('vol1.txt', 'w') as f:
    for i in range(doc.page_count):
        text = clean_text(doc[i].get_text())
        f.write(f'\n===PAGE {i+1}===\n{text}\n')
doc.close()
```

### 扫描版 PDF（卷6）

卷6 是 Pdg2Pic 生成的扫描版，每页是 1580×2500 的图片，无嵌入文字。
OCR 配置：tesseract + chi_sim + --psm 3（自动版面分析）

```python
import pymupdf, subprocess, os

tmp_base = os.path.expanduser('~/.hermes/ocr_tmp')
doc = pymupdf.open('vol6.pdf')

with open('vol6.txt', 'w') as out:
    for i in range(doc.page_count):
        pix = doc[i].get_pixmap(dpi=300)
        img = f'{tmp_base}_{i}.png'
        pix.save(img)
        subprocess.run(['tesseract', img, f'{tmp_base}_{i}',
                       '-l', 'chi_sim', '--psm', '3'],
                       capture_output=True, timeout=20)
        txt_path = f'{tmp_base}_{i}.txt'
        text = ''
        if os.path.exists(txt_path):
            with open(txt_path) as f:
                text = f.read().strip()
            os.unlink(txt_path)
        out.write(f'\n===PAGE {i+1}===\n{text}\n')
        os.unlink(img)
doc.close()
```

## 文本特征与搜索策略

### 空格问题

文字型 PDF 提取后汉字间有空格残留（如"矛 盾 论"），导致多字短语的精确 grep 失败。

**对策**：
- grep 用宽松正则：`grep '主要.*矛盾'` 而非 `grep '主要矛盾'`
- 优先搜单字核心词：`grep '矛盾'` 命中率远高于 `grep '主要矛盾'`
- 关键引用务必用 read_file 验证原文，grep snippet 可能只含单个汉字

### 文集 vs 选集

毛泽东文集 ≠ 毛泽东选集。文集收录选集**以外**的文稿（讲话、谈话、信件、电报等）。
《矛盾论》《实践论》《论持久战》等经典理论著作在选集中，文集中只有间接讨论或后期回顾。

## 主题索引

11 个主题类别，见 `topic_index.json`。每个类别有 trigger 词（匹配用户问题）和 keywords（搜索原文用）。
