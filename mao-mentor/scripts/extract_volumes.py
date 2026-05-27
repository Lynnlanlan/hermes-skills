#!/usr/bin/env python3
"""Extract all 毛泽东文集 PDFs to text files for the mao-mentor skill.

Usage:
    python3 extract_volumes.py /path/to/pdf/dir ~/.hermes/skills/life/mao-mentor/references/

The script auto-detects volumes by filename pattern (文集1, 文集2, etc.).
"""

import pymupdf
import os, re, sys, glob

def clean_text(text):
    """Remove single-char spacing in Chinese text."""
    text = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [l.strip() for l in text.split('\n')]
    return '\n'.join(lines)

def extract_pdf(pdf_path, out_path):
    """Extract text from a text-based PDF."""
    doc = pymupdf.open(pdf_path)
    with open(out_path, 'w', encoding='utf-8') as f:
        for i in range(doc.page_count):
            page = doc[i]
            text = page.get_text()
            text = clean_text(text)
            f.write(f"\n===PAGE {i+1}===\n")
            f.write(text + "\n")
    doc.close()
    return os.path.getsize(out_path)

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    pdf_dir = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    
    pdfs = sorted(glob.glob(os.path.join(pdf_dir, '*.pdf')))
    
    vol_map = {}
    for path in pdfs:
        basename = os.path.basename(path)
        m = re.search(r'文集\s*(\d+)', basename)
        if m:
            vol_map[int(m.group(1))] = path
    
    for vol in sorted(vol_map.keys()):
        path = vol_map[vol]
        out_path = os.path.join(out_dir, f'vol{vol}.txt')
        print(f"Vol {vol}: extracting {os.path.basename(path)}...", end=' ', flush=True)
        
        # Check if it's a scanned PDF (no text on first page)
        doc = pymupdf.open(path)
        first_text = doc[0].get_text().strip()
        doc.close()
        
        if len(first_text) < 20:
            print(f"SKIPPED — appears to be scanned PDF (needs OCR).")
            print(f"  Install tesseract: brew install tesseract")
            print(f"  Then OCR manually or ask Hermes to help.")
            continue
        
        size = extract_pdf(path, out_path)
        print(f"{size/1024:.0f} KB")
    
    print("\nDone! All volumes extracted.")

if __name__ == '__main__':
    main()
