import json

with open("dual_wan_i2v.json", "r") as f:
    data = json.load(f)

nodes = data["nodes"]
links = data["links"]

def get_new_id(id_list):
    return max(id_list) + 1 if id_list else 1

existing_node_ids = [n["id"] for n in nodes]
existing_link_ids = [l[0] for l in links]

# 1. 仅为 HIGH 大模型植入 SVI PRO (高级动作极速版) LoRA
lora_node_high = {
    "id": get_new_id(existing_node_ids),
    "type": "LoraLoaderModelOnly",
    "pos": [380, 70],
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
    "widgets_values": ["wan2.2/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors", 1.0],
    "title": "SVI PRO LoRA (HIGH path)"
}
existing_node_ids.append(lora_node_high["id"])

# 2. 仅为 LOW 动作模型植入 SVI PRO LoRA (坚决剔除 Lightning)
lora_node_low = {
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
    "title": "SVI PRO LoRA (LOW path)"
}
existing_node_ids.append(lora_node_low["id"])

# 串联 HIGH 大模型路线： UNET(37) -> Lora_HIGH -> ModelSampling(54)
new_link_1 = get_new_id(existing_link_ids)
existing_link_ids.append(new_link_1)
links.append([new_link_1, 37, 0, lora_node_high["id"], 0, "MODEL"])
lora_node_high["inputs"][0]["link"] = new_link_1

for l in links:
    if l[0] == 110:
        l[1] = lora_node_high["id"] 
        l[2] = 0 
lora_node_high["outputs"][0]["links"].append(110)

# 串联 LOW 大模型路线： UNET(100) -> Lora_LOW -> ModelSampling(101)
new_link_2 = get_new_id(existing_link_ids)
existing_link_ids.append(new_link_2)
links.append([new_link_2, 100, 0, lora_node_low["id"], 0, "MODEL"])
lora_node_low["inputs"][0]["link"] = new_link_2

for l in links:
    if l[0] == 200:
        l[1] = lora_node_low["id"]
        l[2] = 0
lora_node_low["outputs"][0]["links"].append(200)

# 将新节点塞回画布总图
nodes.append(lora_node_high)
nodes.append(lora_node_low)

# 强制更新 ComfyUI 流水线末端 ID 计数器，防止解析器出错
data["last_node_id"] = lora_node_low["id"]
data["last_link_id"] = new_link_2

with open("dual_wan_i2v_SVI_PRO.json", "w") as f:
    json.dump(data, f, indent=2)

print("Saved precise dual_wan_i2v_SVI_PRO.json successfully")
