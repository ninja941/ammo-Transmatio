MANUAL_STRUCTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "page_summary": {"type": "string"},
        "instruction_steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step_number": {"type": "integer"},
                    "text": {"type": "string"},
                    "parts_mentioned": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["step_number", "text", "parts_mentioned"],
                "additionalProperties": False
            }
        },
        "parts_involved": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["page_summary", "instruction_steps", "parts_involved"],
    "additionalProperties": False
}

LOCALIZATION_SCHEMA = {
    "type": "object",
    "properties": {
        "part_label": {"type": "string"},
        "bbox_xyxy": {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 4,
            "maxItems": 4
        },
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"]
        },
        "rationale_short": {"type": "string"}
    },
    "required": ["part_label", "bbox_xyxy", "confidence", "rationale_short"],
    "additionalProperties": False
}

FUNCTION_INFERENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "part_label": {"type": "string"},
        "used_in_steps": {
            "type": "array",
            "items": {"type": "integer"}
        },
        "inferred_function": {"type": "string"},
        "function_rationale": {"type": "string"},
        "similar_parts": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": [
        "part_label",
        "used_in_steps",
        "inferred_function",
        "function_rationale",
        "similar_parts"
    ],
    "additionalProperties": False
}

RAW_GEOMETRY_SCHEMA = {
    "type": "object",
    "properties": {
        "part_label": {"type": "string"},
        "observed_geometry": {
            "type": "object",
            "properties": {
                "overall_shape": {"type": "string"},
                "relative_size": {"type": "string"},
                "apparent_thickness": {"type": "string"},
                "edge_structure": {"type": "string"},
                "surface_regions": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "holes_slots_grooves": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "protrusions_pegs_tabs": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "symmetry_and_asymmetry": {"type": "string"},
                "orientation_markers": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "comparison_observations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": [
                "overall_shape",
                "relative_size",
                "apparent_thickness",
                "edge_structure",
                "surface_regions",
                "holes_slots_grooves",
                "protrusions_pegs_tabs",
                "symmetry_and_asymmetry",
                "orientation_markers",
                "comparison_observations"
            ],
            "additionalProperties": False
        },
        "uncertainties": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["part_label", "observed_geometry", "uncertainties"],
    "additionalProperties": False
}

TACTILE_ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "part_label": {"type": "string"},
        "used_in_steps": {
            "type": "array",
            "items": {"type": "integer"}
        },
        "inferred_function": {"type": "string"},
        "function_rationale": {"type": "string"},
        "one_sentence_summary": {"type": "string"},
        "shape": {"type": "string"},
        "size_relative": {"type": "string"},
        "thickness_or_depth": {"type": "string"},
        "edge_profile": {"type": "string"},
        "surface_texture": {"type": "string"},
        "protrusions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "grooves_slots_holes": {
            "type": "array",
            "items": {"type": "string"}
        },
        "symmetry": {"type": "string"},
        "orientation_cues": {
            "type": "array",
            "items": {"type": "string"}
        },
        "distinctive_landmarks": {
            "type": "array",
            "items": {"type": "string"}
        },
        "distinguish_from_similar_parts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "other_part": {"type": "string"},
                    "differences": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["other_part", "differences"],
                "additionalProperties": False
            }
        },
        "action_relevant_notes": {
            "type": "array",
            "items": {"type": "string"}
        },
        "uncertainties": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": [
        "part_label",
        "used_in_steps",
        "inferred_function",
        "function_rationale",
        "one_sentence_summary",
        "shape",
        "size_relative",
        "thickness_or_depth",
        "edge_profile",
        "surface_texture",
        "protrusions",
        "grooves_slots_holes",
        "symmetry",
        "orientation_cues",
        "distinctive_landmarks",
        "distinguish_from_similar_parts",
        "action_relevant_notes",
        "uncertainties"
    ],
    "additionalProperties": False
}