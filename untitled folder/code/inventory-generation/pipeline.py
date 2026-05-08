import json
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image

from schema import (
    MANUAL_STRUCTURE_SCHEMA,
    LOCALIZATION_SCHEMA,
    FUNCTION_INFERENCE_SCHEMA,
    RAW_GEOMETRY_SCHEMA,
    TACTILE_ENTRY_SCHEMA,
)
from prompts import (
    SYSTEM_PROMPT_MANUAL_STRUCTURE,
    USER_PROMPT_MANUAL_STRUCTURE,
    FEW_SHOT_MANUAL_STRUCTURE,
    SYSTEM_PROMPT_LOCALIZE,
    USER_PROMPT_LOCALIZE_TEMPLATE,
    SYSTEM_PROMPT_FUNCTION,
    USER_PROMPT_FUNCTION_TEMPLATE,
    SYSTEM_PROMPT_GEOMETRY,
    USER_PROMPT_GEOMETRY_TEMPLATE,
    SYSTEM_PROMPT_TACTILE,
    USER_PROMPT_TACTILE_TEMPLATE,
)
from image_utils import (
    image_file_to_data_url,
    image_bytes_to_data_url,
    crop_image_to_bytes,
)
from pdf_utils import pdf_page_count, render_pdf_page_to_png, page_image_union_bbox_xyxy
from openai_client import call_structured_response


MODEL_NAME = "gpt-5-nano"
REASONING_EFFORT = "low"
IMAGE_DETAIL = "original"
PDF_RENDER_DPI = 220


def _sanitize_label_for_filename(label: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in label).strip("_")
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe or "part"


def _focus_bbox_is_usable(
    *,
    page_image_path: str,
    bbox_xyxy: Optional[List[int]],
    min_area_ratio: float = 0.20
) -> bool:
    """
    Use focused PDF image-region mode only when it covers a meaningful area
    of the rendered page. Small regions (e.g., QR codes/icons) should be ignored.
    """
    if bbox_xyxy is None:
        return False

    x1, y1, x2, y2 = bbox_xyxy
    bw = max(0, x2 - x1)
    bh = max(0, y2 - y1)
    if bw == 0 or bh == 0:
        return False

    with Image.open(page_image_path) as img:
        width, height = img.size

    page_area = max(1, width * height)
    bbox_area = bw * bh
    area_ratio = bbox_area / page_area
    return area_ratio >= min_area_ratio


def prepare_pdf_page_image(
    *,
    pdf_path: str,
    page_index: int,
) -> Tuple[str, Optional[List[int]]]:
    """
    Render a specific PDF page to a temporary PNG and return:
    (png_path, preferred_localization_bbox_for_that_page).
    """
    with tempfile.NamedTemporaryFile(
        suffix=f"_page{page_index + 1}.png",
        prefix="manual_page_",
        delete=False
    ) as tmp:
        tmp_path = tmp.name

    rendered_path = render_pdf_page_to_png(
        pdf_path=pdf_path,
        page_index=page_index,
        out_png_path=tmp_path,
        dpi=PDF_RENDER_DPI,
    )
    preferred_bbox = page_image_union_bbox_xyxy(
        pdf_path=pdf_path,
        page_index=page_index,
        dpi=PDF_RENDER_DPI,
    )
    return rendered_path, preferred_bbox


def extract_manual_structure(
    page_image_path: str,
    focus_bbox_xyxy: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Read the manual page and extract:
    - page summary
    - instruction steps
    - parts involved on this page
    """
    page_url = image_file_to_data_url(page_image_path)
    image_for_structure = page_url

    if focus_bbox_xyxy is not None:
        focus_crop_bytes = crop_image_to_bytes(
            image_path=page_image_path,
            bbox_xyxy=focus_bbox_xyxy,
            margin_ratio=0.0,
        )
        image_for_structure = image_bytes_to_data_url(focus_crop_bytes)

    user_content = [
        {
            "type": "input_text",
            "text": FEW_SHOT_MANUAL_STRUCTURE
        },
        {
            "type": "input_text",
            "text": USER_PROMPT_MANUAL_STRUCTURE
        },
        {
            "type": "input_image",
            "image_url": image_for_structure,
            "detail": IMAGE_DETAIL
        },
    ]

    return call_structured_response(
        model=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
        system_prompt=SYSTEM_PROMPT_MANUAL_STRUCTURE,
        user_content=user_content,
        schema_name="manual_structure",
        schema=MANUAL_STRUCTURE_SCHEMA,
    )


def build_instruction_context(instruction_steps: List[Dict[str, Any]], part_label: str) -> str:
    """
    Build a small text context using only the steps that mention the target part.
    """
    relevant = []

    for step in instruction_steps:
        if part_label in step.get("parts_mentioned", []):
            relevant.append(f"Step {step['step_number']}: {step['text']}")

    return "\n".join(relevant) if relevant else "No direct step mentions found."


def derive_parts_from_instruction_steps(instruction_steps: List[Dict[str, Any]]) -> List[str]:
    """
    Build a stable, ordered unique part list from instruction step mentions.
    """
    ordered_parts: List[str] = []
    seen = set()

    for step in instruction_steps:
        for part in step.get("parts_mentioned", []):
            if isinstance(part, str):
                normalized = part.strip()
            else:
                normalized = ""

            if normalized and normalized not in seen:
                seen.add(normalized)
                ordered_parts.append(normalized)

    return ordered_parts


def localize_part(
    page_image_path: str,
    part_label: str,
    instruction_steps: List[Dict[str, Any]],
    search_bbox_xyxy: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Find the bounding box for a specific part on the full manual page.
    """
    page_url = image_file_to_data_url(page_image_path)
    instruction_context = build_instruction_context(instruction_steps, part_label)

    image_for_localize = page_url
    offset_x = 0
    offset_y = 0

    if search_bbox_xyxy is not None:
        search_crop_bytes = crop_image_to_bytes(
            image_path=page_image_path,
            bbox_xyxy=search_bbox_xyxy,
            margin_ratio=0.0,
        )
        image_for_localize = image_bytes_to_data_url(search_crop_bytes)
        offset_x = int(search_bbox_xyxy[0])
        offset_y = int(search_bbox_xyxy[1])

    user_content = [
        {
            "type": "input_text",
            "text": USER_PROMPT_LOCALIZE_TEMPLATE.format(
                part_label=part_label,
                instruction_context=instruction_context
            )
        },
        {
            "type": "input_image",
            "image_url": image_for_localize,
            "detail": IMAGE_DETAIL
        }
    ]
    localization = call_structured_response(
        model=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
        system_prompt=SYSTEM_PROMPT_LOCALIZE,
        user_content=user_content,
        schema_name="part_localization",
        schema=LOCALIZATION_SCHEMA,
    )

    if search_bbox_xyxy is not None:
        x1, y1, x2, y2 = localization["bbox_xyxy"]
        localization["bbox_xyxy"] = [
            int(x1 + offset_x),
            int(y1 + offset_y),
            int(x2 + offset_x),
            int(y2 + offset_y),
        ]

    return localization


def infer_part_function(
    part_label: str,
    instruction_steps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Infer:
    - which steps use the part
    - its likely procedural role
    - any similar/confusable parts
    """
    user_content = [
        {
            "type": "input_text",
            "text": USER_PROMPT_FUNCTION_TEMPLATE.format(
                part_label=part_label,
                instruction_steps_json=json.dumps(
                    instruction_steps,
                    ensure_ascii=False,
                    indent=2
                )
            )
        }
    ]

    return call_structured_response(
        model=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
        system_prompt=SYSTEM_PROMPT_FUNCTION,
        user_content=user_content,
        schema_name="function_inference",
        schema=FUNCTION_INFERENCE_SCHEMA,
    )


def extract_raw_geometry(
    *,
    page_image_path: str,
    part_label: str,
    crop_data_url: str,
    similar_parts: List[str],
    comparison_crop_data_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract only grounded geometric observations from:
    - full manual page
    - target crop
    - optional similar-part comparison crop
    """
    page_url = image_file_to_data_url(page_image_path)

    user_content = [
        {
            "type": "input_text",
            "text": USER_PROMPT_GEOMETRY_TEMPLATE.format(
                part_label=part_label,
                similar_parts=similar_parts
            )
        },
        {
            "type": "input_text",
            "text": "Full manual page:"
        },
        {
            "type": "input_image",
            "image_url": page_url,
            "detail": IMAGE_DETAIL
        },
        {
            "type": "input_text",
            "text": f"Target crop for part {part_label}:"
        },
        {
            "type": "input_image",
            "image_url": crop_data_url,
            "detail": IMAGE_DETAIL
        }
    ]

    if comparison_crop_data_url is not None:
        user_content.extend([
            {
                "type": "input_text",
                "text": "Comparison crop for a similar part:"
            },
            {
                "type": "input_image",
                "image_url": comparison_crop_data_url,
                "detail": IMAGE_DETAIL
            },
        ])

    return call_structured_response(
        model=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
        system_prompt=SYSTEM_PROMPT_GEOMETRY,
        user_content=user_content,
        schema_name="raw_geometry",
        schema=RAW_GEOMETRY_SCHEMA,
    )


def rewrite_to_tactile_entry(
    *,
    function_json: Dict[str, Any],
    geometry_json: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert:
    - function inference
    - grounded raw geometry

    into the final tactile inventory entry.
    """
    user_content = [
        {
            "type": "input_text",
            "text": USER_PROMPT_TACTILE_TEMPLATE.format(
                function_json=json.dumps(function_json, ensure_ascii=False, indent=2),
                geometry_json=json.dumps(geometry_json, ensure_ascii=False, indent=2),
            )
        }
    ]

    return call_structured_response(
        model=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
        system_prompt=SYSTEM_PROMPT_TACTILE,
        user_content=user_content,
        schema_name="tactile_entry",
        schema=TACTILE_ENTRY_SCHEMA,
    )


def generate_inventory(
    *,
    input_file_path: str,
    uploads_dir: str = "data/uploads",
) -> Dict[str, Any]:
    """
    Main end-to-end pipeline.

    Input:
    - manual image (single page) or manual PDF (all pages)

    Output:
    - merged page summaries
    - merged instruction steps (globally renumbered)
    - merged parts involved
    - tactile inventory entry for each part occurrence
    """
    Path(uploads_dir).mkdir(parents=True, exist_ok=True)
    input_path = Path(input_file_path)
    is_pdf = input_path.suffix.lower() == ".pdf"

    page_inputs: List[Dict[str, Any]] = []
    temp_files_to_cleanup: List[str] = []

    if is_pdf:
        total_pages = pdf_page_count(str(input_path))
        for page_index in range(total_pages):
            page_image_path, preferred_localization_bbox = prepare_pdf_page_image(
                pdf_path=str(input_path),
                page_index=page_index,
            )
            page_inputs.append({
                "page_number": page_index + 1,
                "page_image_path": page_image_path,
                "preferred_localization_bbox": preferred_localization_bbox,
            })
            temp_files_to_cleanup.append(page_image_path)
    else:
        page_inputs.append({
            "page_number": 1,
            "page_image_path": str(input_path),
            "preferred_localization_bbox": None,
        })

    all_page_summaries: List[Dict[str, Any]] = []
    all_instruction_steps: List[Dict[str, Any]] = []
    all_parts_involved: List[str] = []
    seen_parts = set()
    inventory: List[Dict[str, Any]] = []
    next_global_step_number = 1
    part_crops_dir: Optional[Path] = None
    next_crop_index = 1

    try:
        for page_input in page_inputs:
            page_number = page_input["page_number"]
            page_image_path = page_input["page_image_path"]
            preferred_localization_bbox = page_input["preferred_localization_bbox"]

            effective_focus_bbox = (
                preferred_localization_bbox
                if _focus_bbox_is_usable(
                    page_image_path=page_image_path,
                    bbox_xyxy=preferred_localization_bbox
                )
                else None
            )

            manual_structure = extract_manual_structure(
                page_image_path=page_image_path,
                focus_bbox_xyxy=effective_focus_bbox,
            )

            all_page_summaries.append({
                "page_number": page_number,
                "summary": manual_structure["page_summary"],
            })

            instruction_steps_local = manual_structure["instruction_steps"]
            step_number_map: Dict[int, int] = {}
            instruction_steps_global_for_page: List[Dict[str, Any]] = []

            for step in instruction_steps_local:
                old_step_number = int(step["step_number"])
                new_step_number = next_global_step_number
                next_global_step_number += 1

                step_number_map[old_step_number] = new_step_number
                instruction_steps_global_for_page.append({
                    "step_number": new_step_number,
                    "text": step["text"],
                    "parts_mentioned": step["parts_mentioned"],
                })

            all_instruction_steps.extend(instruction_steps_global_for_page)

            parts_from_steps = derive_parts_from_instruction_steps(instruction_steps_local)
            parts_involved_local = (
                parts_from_steps if parts_from_steps else manual_structure["parts_involved"]
            )

            for part_label in parts_involved_local:
                if part_label not in seen_parts:
                    seen_parts.add(part_label)
                    all_parts_involved.append(part_label)

            localizations: Dict[str, Dict[str, Any]] = {}
            functions: Dict[str, Dict[str, Any]] = {}

            for part_label in parts_involved_local:
                localizations[part_label] = localize_part(
                    page_image_path=page_image_path,
                    part_label=part_label,
                    instruction_steps=instruction_steps_local,
                    search_bbox_xyxy=effective_focus_bbox,
                )

                function_json = infer_part_function(
                    part_label=part_label,
                    instruction_steps=instruction_steps_local,
                )

                used_steps_global = []
                for used_step_local in function_json.get("used_in_steps", []):
                    if used_step_local in step_number_map:
                        used_steps_global.append(step_number_map[used_step_local])
                function_json["used_in_steps"] = sorted(set(used_steps_global))
                functions[part_label] = function_json

            crop_data_urls: Dict[str, str] = {}
            crop_file_paths: Dict[str, str] = {}

            for part_label in parts_involved_local:
                crop_bytes = crop_image_to_bytes(
                    image_path=page_image_path,
                    bbox_xyxy=localizations[part_label]["bbox_xyxy"],
                    margin_ratio=0.08,
                )
                crop_data_urls[part_label] = image_bytes_to_data_url(crop_bytes)

                if part_crops_dir is None:
                    part_crops_dir = Path(uploads_dir) / f"part_crops_{uuid.uuid4().hex[:8]}"
                    part_crops_dir.mkdir(parents=True, exist_ok=True)

                safe_label = _sanitize_label_for_filename(part_label)
                crop_file_name = (
                    f"p{page_number:02d}_{next_crop_index:03d}_{safe_label}.png"
                )
                next_crop_index += 1
                crop_file_path = part_crops_dir / crop_file_name
                crop_file_path.write_bytes(crop_bytes)
                crop_file_paths[part_label] = str(crop_file_path.resolve())

            for part_label in parts_involved_local:
                function_json = functions[part_label]
                similar_parts = function_json.get("similar_parts", [])

                comparison_crop_data_url = None
                if similar_parts:
                    for other in similar_parts:
                        if other in crop_data_urls and other != part_label:
                            comparison_crop_data_url = crop_data_urls[other]
                            break

                geometry_json = extract_raw_geometry(
                    page_image_path=page_image_path,
                    part_label=part_label,
                    crop_data_url=crop_data_urls[part_label],
                    similar_parts=similar_parts,
                    comparison_crop_data_url=comparison_crop_data_url,
                )

                tactile_entry = rewrite_to_tactile_entry(
                    function_json=function_json,
                    geometry_json=geometry_json,
                )

                tactile_entry["bbox_xyxy"] = localizations[part_label]["bbox_xyxy"]
                tactile_entry["localization_confidence"] = localizations[part_label]["confidence"]
                tactile_entry["image"] = crop_data_urls[part_label]
                tactile_entry["image_path"] = crop_file_paths[part_label]
                tactile_entry["source_page"] = page_number

                inventory.append(tactile_entry)

        combined_page_summary = " ".join(
            f"Page {item['page_number']}: {item['summary']}"
            for item in all_page_summaries
            if item.get("summary")
        ).strip()

        return {
            "document_type": "manual",
            "page_count_processed": len(page_inputs),
            "page_summary": combined_page_summary,
            "instruction_steps": all_instruction_steps,
            "parts_involved": all_parts_involved,
            "inventory": inventory,
            "page_summaries": all_page_summaries,
        }
    finally:
        for tmp_path in temp_files_to_cleanup:
            try:
                Path(tmp_path).unlink()
            except FileNotFoundError:
                pass
