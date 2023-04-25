import json

with open('labels.json', 'r', encoding='utf-8') as f:
    labels_dict = json.load(f)

# print(labels_dict)

class_labels = [item['label'] for item in labels_dict.values()]
class_labels_cn = [item['label_cn'] for item in labels_dict.values()]
class_labels_id = [int(label_id) for label_id in labels_dict.keys()]
class_colors_hex = [item['color'] for item in labels_dict.values()]
class_colors_rgb = [tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (1, 3, 5)) for hex_color in class_colors_hex]

labels_dict_pack = {
    'label_id': class_labels_id,
    'label': class_labels,
    'label_cn': class_labels_cn,
    'color_hex': class_colors_hex,
    'color_rgb': class_colors_rgb,
}

# print(class_labels)
# print(class_labels_cn)
# print(class_labels_id)
# print(class_colors)

ui_groups = {
    'indoor': [],
    'outdoor': [],
    'others': [],
}


colors_hex = [
'#000000',
'#ff0000',
'#6496f5',
'#64e6f5',
'#1e3c96',
'#0000ff',
'#6450fa',
'#501eb4',
'#0000ff',
'#ff1e1e',
'#ff28c8',
'#963c5a',
'#ff00ff',
'#ff96ff',
'#4b004b',
'#af004b',
'#ffc800',
'#ff7832',
'#ff9600',
'#96ffaa',
'#00af00',
'#873c00',
'#96f050',
'#fff096',
'#ff0000',
'#32ffff',
'#808000',
'#ee82ee',
'#ffa500',
'#a52a2a'
]