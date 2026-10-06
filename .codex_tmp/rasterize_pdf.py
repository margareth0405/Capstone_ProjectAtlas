import sys
from pathlib import Path

import fitz

pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r".codex_tmp\copied_final.pdf")
out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r".codex_tmp\framework_pngs")
out_dir.mkdir(parents=True, exist_ok=True)
pdf = fitz.open(pdf_path)
matrix = fitz.Matrix(2, 2)
for index, page in enumerate(pdf, start=1):
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    pixmap.save(out_dir / f"page-{index}.png")
print(f"pages={len(pdf)}")
