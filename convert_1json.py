import json

# File paths
files = [
    r"C:\Users\user\Desktop\VSC Folder\Company Hackathon\GoatRobotics\data\nav_graph_1.json",
    r"C:\Users\user\Desktop\VSC Folder\Company Hackathon\GoatRobotics\data\nav_graph_2.json",
    r"C:\Users\user\Desktop\VSC Folder\Company Hackathon\GoatRobotics\data\nav_graph_3.json"
]

# Initialize merged structure
merged_data = {"building_name": "new_site", "levels": {}}

# Read and merge each file
for file in files:
    with open(file, "r") as f:
        data = json.load(f)
        merged_data["levels"].update(data.get("levels", {}))

# Save merged JSON
output_file = r"C:\Users\user\Desktop\VSC Folder\Company Hackathon\GoatRobotics\data\nav_graph.json"
with open(output_file, "w") as f:
    json.dump(merged_data, f, indent=4)

print(f"Merged JSON saved to {output_file}")
