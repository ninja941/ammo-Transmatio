# import json
# from pipeline import generate_inventory

# result = generate_inventory(
#     input_file_path="/Users/monalikapadmareddy/Library/CloudStorage/OneDrive-StonyBrookUniversity/PhD-Research/Manuals/SmartGlasses/inputs/Desk-Organizer-Manual.pdf"   # or .png/.jpg
# )

# print(json.dumps(result, indent=2, ensure_ascii=False))

import json
from pathlib import Path
from pipeline import generate_inventory

input_file_path = "/Users/monalikapadmareddy/Library/CloudStorage/OneDrive-StonyBrookUniversity/PhD-Research/Manuals/SmartGlasses/Inputs/Chair.pdf"
output_folder = "/Users/monalikapadmareddy/Library/CloudStorage/OneDrive-StonyBrookUniversity/PhD-Research/Manuals/SmartGlasses/Outputs/"

result = generate_inventory(
    input_file_path=input_file_path
)

input_path = Path(input_file_path)
output_path = Path(output_folder)
output_path.mkdir(parents=True, exist_ok=True)

log_file_path = output_path / f"{input_path.stem}.log"

with open(log_file_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(json.dumps(result, indent=2, ensure_ascii=False))
print(f"\nSaved log to: {log_file_path}")