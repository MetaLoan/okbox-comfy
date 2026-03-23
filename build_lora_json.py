import json

with open("dual_wan_i2v.json", "r") as f:
    data = json.load(f)

nodes = data["nodes"]
links = data["links"]

def get_new_id(id_list):
    return max(id_list) + 1 if id_list else 1

existing_node_ids = [n["id"] for n in nodes]
existing_link_ids = [l[0] for l in links]

# Create Lora for HIGH path
lora_node_high = {
    "id": get_new_id(existing_node_ids),
    "type": "LoraLoaderModelOnly",
    "pos": [380, 70],
    "size": [315, 82],
    "flags": {},
    "order": 5,
    "mode": 0,
    "inputs": [
        {"name": "model", "type": "MODEL", "link": None} # will set later
    ],
    "outputs": [
        {"name": "MODEL", "type": "MODEL", "links": [], "slot_index": 0}
    ],
    "properties": {"Node name for S&R": "LoraLoaderModelOnly"},
    "widgets_values": ["wan2.2/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors", 1.0],
    "title": "LoRA (HIGH path)"
}
existing_node_ids.append(lora_node_high["id"])

# Create Lora 1 for LOW path
lora_node_low_1 = {
    "id": get_new_id(existing_node_ids),
    "type": "LoraLoaderModelOnly",
    "pos": [380, 220],
    "size": [315, 82],
    "flags": {},
    "order": 5,
    "mode": 0,
    "inputs": [
        {"name": "model", "type": "MODEL", "link": None}
    ],
    "outputs": [
        {"name": "MODEL", "type": "MODEL", "links": [], "slot_index": 0}
    ],
    "properties": {"Node name for S&R": "LoraLoaderModelOnly"},
    "widgets_values": ["wan2.2/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors", 1.0],
    "title": "LoRA 1 (LOW path)"
}
existing_node_ids.append(lora_node_low_1["id"])

# Create Lora 2 for LOW path
lora_node_low_2 = {
    "id": get_new_id(existing_node_ids),
    "type": "LoraLoaderModelOnly",
    "pos": [380, 320],
    "size": [315, 82],
    "flags": {},
    "order": 6,
    "mode": 0,
    "inputs": [
        {"name": "model", "type": "MODEL", "link": None}
    ],
    "outputs": [
        {"name": "MODEL", "type": "MODEL", "links": [], "slot_index": 0}
    ],
    "properties": {"Node name for S&R": "LoraLoaderModelOnly"},
    "widgets_values": ["wan2.2/Wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors", 1.0],
    "title": "LoRA 2 (LOW path)"
}
existing_node_ids.append(lora_node_low_2["id"])

# Now rewire the links.
# Link 110 connects Node 37 (UNET HIGH) to Node 54 (Sampling)
# We change Link 110 to start from Lora_HIGH
# And create New Link connecting Node 37 to Lora_HIGH
new_link_1 = get_new_id(existing_link_ids)
existing_link_ids.append(new_link_1)
links.append([new_link_1, 37, 0, lora_node_high["id"], 0, "MODEL"])
lora_node_high["inputs"][0]["link"] = new_link_1

for l in links:
    if l[0] == 110:
        l[1] = lora_node_high["id"] # change origin node
        l[2] = 0 # origin port
lora_node_high["outputs"][0]["links"].append(110)


# Link 200 connects Node 100 (UNET LOW) to Node 101 (Sampling)
# We redirect it to go: Node 100 -> Lora_LOW_1 -> Lora_LOW_2 -> Node 101

new_link_2 = get_new_id(existing_link_ids)
existing_link_ids.append(new_link_2)
links.append([new_link_2, 100, 0, lora_node_low_1["id"], 0, "MODEL"])
lora_node_low_1["inputs"][0]["link"] = new_link_2

new_link_3 = get_new_id(existing_link_ids)
existing_link_ids.append(new_link_3)
links.append([new_link_3, lora_node_low_1["id"], 0, lora_node_low_2["id"], 0, "MODEL"])
lora_node_low_1["outputs"][0]["links"].append(new_link_3)
lora_node_low_2["inputs"][0]["link"] = new_link_3

for l in links:
    if l[0] == 200:
        l[1] = lora_node_low_2["id"]
        l[2] = 0
lora_node_low_2["outputs"][0]["links"].append(200)

nodes.append(lora_node_high)
nodes.append(lora_node_low_1)
nodes.append(lora_node_low_2)

data["last_node_id"] = lora_node_low_2["id"]
data["last_link_id"] = new_link_3

with open("dual_wan_i2v_LORA.json", "w") as f:
    json.dump(data, f, indent=2)

print("Saved dual_wan_i2v_LORA.json")
