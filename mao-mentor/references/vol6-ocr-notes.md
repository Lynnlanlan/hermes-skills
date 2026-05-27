# 文集6 OCR 记录

文集6（中共中央文献研究室编，人民出版社，1993）是扫描版 PDF，
77MB，530页，每页均为图片，pymupdf 无法直接提取文字。

## OCR 方法

使用 tesseract + chi_sim 语言包：

```bash
brew install tesseract
# 中文语言包
curl -L -o $(brew --prefix)/share/tessdata/chi_sim.traineddata \
  https://github.com/tesseract-ocr/tessdata_fast/raw/main/chi_sim.traineddata
```

## 关键参数

- `--psm 3`（自动检测页面布局）—— 书籍扫描有页眉页脚页码，`--psm 6`（均匀文字块）无法正确处理
- DPI: 300（过高导致 OCR 速度变慢且不提升精度）

## 沙箱注意事项

Hermes 的 terminal 工具存在进程间文件隔离：
- Python 子进程写入 `/tmp/` 的文件，tesseract 在后续 shell 命令中无法读取
- **必须使用 `~/.hermes/` 作为临时目录**

## 完整批处理脚本

```python
import pymupdf, subprocess, os

pdf = '毛泽东文集第六卷.pdf'
out_path = 'vol6.txt'
tmp_base = os.path.expanduser('~/.hermes/ocr_tmp')

doc = pymupdf.open(pdf)
total = doc.page_count

with open(out_path, 'w', encoding='utf-8') as out:
    for i in range(total):
        pix = doc[i].get_pixmap(dpi=300)
        img = f'{tmp_base}_{i}.png'
        pix.save(img)
        
        out_base = f'{tmp_base}_{i}'
        subprocess.run(['tesseract', img, out_base, '-l', 'chi_sim', '--psm', '3'],
                       capture_output=True, timeout=20)
        
        txt_path = out_base + '.txt'
        text = ''
        if os.path.exists(txt_path):
            with open(txt_path) as f:
                text = f.read().strip()
            os.unlink(txt_path)
        
        out.write(f'\n===PAGE {i+1}===\n')
        out.write(text + '\n')
        os.unlink(img)

doc.close()

# 清理临时文件
for f in os.listdir(os.path.expanduser('~/.hermes/')):
    if f.startswith('ocr_tmp_'):
        os.unlink(os.path.expanduser(f'~/.hermes/{f}'))
```

## 结果

- 530页 → 725KB 纯文本
- 耗时约 8 分钟（~0.9s/页，M5 MacBook Pro）
- OCR 质量：中文识别良好，少量数字/标点识别偏差，可搜索
