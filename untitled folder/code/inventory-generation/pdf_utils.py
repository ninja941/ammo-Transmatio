from pathlib import Path
from typing import List, Optional
import fitz  # PyMuPDF


def pdf_page_count(pdf_path: str) -> int:
    doc = fitz.open(str(pdf_path))
    try:
        return len(doc)
    finally:
        doc.close()


def render_pdf_page_to_png(
    pdf_path: str,
    page_index: int,
    out_png_path: str,
    dpi: int = 220
) -> str:
    pdf_path = str(pdf_path)
    out_png_path = str(out_png_path)

    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        doc.close()
        raise ValueError("PDF has no pages.")
    if page_index < 0 or page_index >= len(doc):
        doc.close()
        raise IndexError(f"Page index out of range: {page_index}")

    page = doc[page_index]
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    out_path = Path(out_png_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(out_png_path)

    doc.close()
    return out_png_path


def page_image_union_bbox_xyxy(
    pdf_path: str,
    page_index: int,
    dpi: int = 220,
    min_area_ratio: float = 0.01
) -> Optional[List[int]]:
    """
    Return a union bbox (xyxy, pixels at the same DPI used for rendering) for
    sizeable image blocks on a page. Helps focus localization on diagrams/photos
    instead of surrounding article text.
    """
    doc = fitz.open(str(pdf_path))
    if len(doc) == 0:
        doc.close()
        return None
    if page_index < 0 or page_index >= len(doc):
        doc.close()
        return None

    page = doc[page_index]
    page_rect = page.rect
    page_area = float(page_rect.width * page_rect.height)
    blocks = page.get_text("dict").get("blocks", [])

    candidates = []
    for block in blocks:
        if block.get("type") != 1:
            continue
        x1, y1, x2, y2 = block.get("bbox", (0, 0, 0, 0))
        area = max(0.0, (x2 - x1) * (y2 - y1))
        if page_area > 0 and (area / page_area) >= min_area_ratio:
            candidates.append((x1, y1, x2, y2))

    doc.close()

    if not candidates:
        return None

    ux1 = min(b[0] for b in candidates)
    uy1 = min(b[1] for b in candidates)
    ux2 = max(b[2] for b in candidates)
    uy2 = max(b[3] for b in candidates)

    scale = dpi / 72.0
    return [
        int(round(ux1 * scale)),
        int(round(uy1 * scale)),
        int(round(ux2 * scale)),
        int(round(uy2 * scale)),
    ]


def render_first_page_pdf_to_png(pdf_path: str, out_png_path: str, dpi: int = 220) -> str:
    return render_pdf_page_to_png(
        pdf_path=pdf_path,
        page_index=0,
        out_png_path=out_png_path,
        dpi=dpi,
    )


def first_page_image_union_bbox_xyxy(
    pdf_path: str,
    dpi: int = 220,
    min_area_ratio: float = 0.01
) -> Optional[List[int]]:
    return page_image_union_bbox_xyxy(
        pdf_path=pdf_path,
        page_index=0,
        dpi=dpi,
        min_area_ratio=min_area_ratio,
    )
