import base64
import io
import mimetypes
from pathlib import Path
from typing import List, Tuple

from PIL import Image


def image_file_to_data_url(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type is None:
        mime_type = "image/png"

    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{b64}"


def image_bytes_to_data_url(image_bytes: bytes, mime_type: str = "image/png") -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def clamp_bbox_xyxy(bbox: List[int], width: int, height: int) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(1, min(x2, width))
    y2 = max(1, min(y2, height))

    if x2 <= x1:
        x2 = min(width, x1 + 1)
    if y2 <= y1:
        y2 = min(height, y1 + 1)

    return x1, y1, x2, y2


def expand_bbox_xyxy(
    bbox: List[int],
    width: int,
    height: int,
    margin_ratio: float = 0.08
) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    bw = x2 - x1
    bh = y2 - y1
    mx = int(bw * margin_ratio)
    my = int(bh * margin_ratio)

    return (
        max(0, x1 - mx),
        max(0, y1 - my),
        min(width, x2 + mx),
        min(height, y2 + my),
    )


def crop_image_to_bytes(
    image_path: str,
    bbox_xyxy: List[int],
    margin_ratio: float = 0.08,
    output_format: str = "PNG"
) -> bytes:
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        width, height = img.size
        bbox = clamp_bbox_xyxy(bbox_xyxy, width, height)
        bbox = expand_bbox_xyxy(list(bbox), width, height, margin_ratio=margin_ratio)
        crop = img.crop(bbox)

        buffer = io.BytesIO()
        crop.save(buffer, format=output_format)
        return buffer.getvalue()