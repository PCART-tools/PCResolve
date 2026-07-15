# MAHE_OD_DATASET -- Annotation Groups (105 groups, 139 records)

## Summary

| Evidence | Groups | Records | Needs Human |
|----------|--------|---------|-------------|
| static_obvious | 8 | 15 | 0 |
| static_context | 42 | 52 | 0 |
| manual_reasoned | 55 | 72 | 72 |
| **Total** | **105** | **139** | **72** |

## Group 1: FT -> library/torchvision (6 records)

| Evidence | static_obvious |
| Needs human | no (0/6) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import torchvision.transforms.functional</code> @ utils.py:6 |
| Owner | torchvision |
| Proposed GT | library / torchvision |

**Representative expressions:**

- <code>FT.hflip(image)</code> -- utils.py:546
- <code>FT.resize(image, dims)</code> -- utils.py:569
- <code>FT.to_tensor(new_image)</code> -- utils.py:641
- <code>FT.to_pil_image(new_image)</code> -- utils.py:653
- <code>FT.to_tensor(new_image)</code> -- utils.py:663
- ... and 1 more

**All bindings (1 unique):**
- <code>utils.py</code> L6: <code>import torchvision.transforms.functional</code>

## Group 2: bbox -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>object.find('bndbox')</code> @ utils.py:71 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>bbox.find('xmin')</code> -- utils.py:72
- <code>bbox.find('ymin')</code> -- utils.py:73
- <code>bbox.find('xmax')</code> -- utils.py:74
- <code>bbox.find('ymax')</code> -- utils.py:75

**All bindings (1 unique):**
- <code>utils.py</code> L71: <code>object.find('bndbox')</code>

## Group 3: bbox -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>object.find('bndbox')</code> @ annotation.py:44 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>bbox.find('xmin')</code> -- annotation.py:45
- <code>bbox.find('ymin')</code> -- annotation.py:46
- <code>bbox.find('xmax')</code> -- annotation.py:47
- <code>bbox.find('ymax')</code> -- annotation.py:48

**All bindings (1 unique):**
- <code>annotation.py</code> L44: <code>object.find('bndbox')</code>

## Group 4: ax -> library/matplotlib (4 records)

| Evidence | static_context |
| Needs human | no (0/4) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>fig.add_subplot(111)</code> @ datavisualizer.py:41 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>ax.scatter(img_meta_df.Width, img_meta_df.Height, color='blue', alpha=0.5, s=img_meta_df['Aspect Rat</code> -- datavisualizer.py:42
- <code>ax.set_title('Image Resolution')</code> -- datavisualizer.py:43
- <code>ax.set_xlabel('Width', size=14)</code> -- datavisualizer.py:44
- <code>ax.set_ylabel('Height', size=14)</code> -- datavisualizer.py:45

**All bindings (1 unique):**
- <code>datavisualizer.py</code> L41: <code>fig.add_subplot(111)</code>

## Group 5: root -> library/xml (4 records)

| Evidence | static_context |
| Needs human | no (0/4) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>tree.getroot()</code> @ preprocess.py:100 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>root.find('size')</code> -- preprocess.py:102
- <code>root.find('size')</code> -- preprocess.py:103
- <code>root.find('size')</code> -- preprocess.py:104
- <code>root.findall('object')</code> -- preprocess.py:108

**All bindings (1 unique):**
- <code>preprocess.py</code> L100: <code>tree.getroot()</code>

## Group 6: object -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>for target</code> @ utils.py:63 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>object.find('difficult')</code> -- utils.py:65
- <code>object.find('name')</code> -- utils.py:67
- <code>object.find('bndbox')</code> -- utils.py:71

**All bindings (1 unique):**
- <code>utils.py</code> L63: <code>for target</code>

## Group 7: plt -> library/matplotlib (3 records)

| Evidence | static_obvious |
| Needs human | no (0/3) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import matplotlib.pyplot</code> @ preprocess.py:10 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.figure(figsize=(12, 12))</code> -- preprocess.py:150
- <code>plt.axis('off')</code> -- preprocess.py:151
- <code>plt.imshow(img)</code> -- preprocess.py:152

**All bindings (1 unique):**
- <code>preprocess.py</code> L10: <code>import matplotlib.pyplot</code>

## Group 8: root -> library/xml (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>tree.getroot()</code> @ read pascalvoc annotation.py:13 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>root.find('size')</code> -- read pascalvoc annotation.py:15
- <code>root.find('size')</code> -- read pascalvoc annotation.py:16
- <code>root.findall('object')</code> -- read pascalvoc annotation.py:21

**All bindings (1 unique):**
- <code>read pascalvoc annotation.py</code> L13: <code>tree.getroot()</code>

## Group 9: (1 - true_class_difficulties) -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | RETURN_PROPAGATION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>(1 - true_class_difficulties).sum()</code> -- utils.py:224
- <code>(1 - true_class_difficulties).sum().item()</code> -- utils.py:224


## Group 10: filename -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>for target</code> @ generatevocdata.py:37 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>filename.endswith('.jpg')</code> -- generatevocdata.py:38
- <code>filename.rstrip('.jpg')</code> -- generatevocdata.py:39

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L37: <code>for target</code>

## Group 11: image -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter image</code> @ utils.py:412 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>image.size(1)</code> -- utils.py:424
- <code>image.size(2)</code> -- utils.py:425

**All bindings (1 unique):**
- <code>utils.py</code> L412: <code>parameter image</code>

## Group 12: image -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter image</code> @ utils.py:451 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>image.size(1)</code> -- utils.py:465
- <code>image.size(2)</code> -- utils.py:466

**All bindings (1 unique):**
- <code>utils.py</code> L451: <code>parameter image</code>

## Group 13: object -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>for target</code> @ annotation.py:42 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>object.find('name')</code> -- annotation.py:43
- <code>object.find('bndbox')</code> -- annotation.py:44

**All bindings (1 unique):**
- <code>annotation.py</code> L42: <code>for target</code>

## Group 14: overlap -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>overlap.squeeze(0)</code> @ utils.py:503 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>overlap.squeeze(0)</code> -- utils.py:503
- <code>overlap.max()</code> -- utils.py:506

**All bindings (1 unique):**
- <code>utils.py</code> L503: <code>overlap.squeeze(0)</code>

## Group 15: targets -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter targets</code> @ utils.py:683 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>targets.size(0)</code> -- utils.py:692
- <code>targets.view(-1, 1)</code> -- utils.py:694

**All bindings (1 unique):**
- <code>utils.py</code> L683: <code>parameter targets</code>

## Group 16: tensor -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter tensor</code> @ utils.py:156 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>tensor.dim()</code> -- utils.py:166
- <code>tensor.dim()</code> -- utils.py:167

**All bindings (1 unique):**
- <code>utils.py</code> L156: <code>parameter tensor</code>

## Group 17: tensor -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>tensor.index_select(dim=d,\n                                         index=torch</code> @ utils.py:169 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>tensor.index_select(dim=d, index=torch.arange(start=0, end=tensor.size(d), step=m[d]).long())</code> -- utils.py:169
- <code>tensor.size(d)</code> -- utils.py:170

**All bindings (1 unique):**
- <code>utils.py</code> L169: <code>tensor.index_select(dim=d,\n                                         index=torch</code>

## Group 18: imgnames -> python/python (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ generatevocdata.py:25 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>imgnames.append(img)</code> -- generatevocdata.py:40
- <code>imgnames.copy()</code> -- generatevocdata.py:66

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L25: <code>[]</code>

## Group 19: tree -> library/xml (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ET.parse(path)</code> @ xmlfilerename.py:10 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>tree.getroot()</code> -- xmlfilerename.py:11
- <code>tree.write(path)</code> -- xmlfilerename.py:20

**All bindings (1 unique):**
- <code>xmlfilerename.py</code> L10: <code>ET.parse(path)</code>

## Group 20: annotations[labelname] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>annotations[labelname].append(img)</code> -- generatevocdata.py:59


## Group 21: areas_set_1 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>(set_1[:, 2] - set_1[:, 0]) * (set_1[:, 3] - set_1[:, 1])</code> @ utils.py:399 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>areas_set_1.unsqueeze(1)</code> -- utils.py:404

**All bindings (1 unique):**
- <code>utils.py</code> L399: <code>(set_1[:, 2] - set_1[:, 0]) * (set_1[:, 3] - set_1[:, 1])</code>

## Group 22: areas_set_2 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>(set_2[:, 2] - set_2[:, 0]) * (set_2[:, 3] - set_2[:, 1])</code> @ utils.py:400 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>areas_set_2.unsqueeze(0)</code> -- utils.py:404

**All bindings (1 unique):**
- <code>utils.py</code> L400: <code>(set_2[:, 2] - set_2[:, 0]) * (set_2[:, 3] - set_2[:, 1])</code>

## Group 23: average_precisions -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>{rev_label_map[c + 1]: v for c, v in enumerate(average_precisions.tolist())}</code> @ utils.py:305 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>average_precisions.tolist()</code> -- utils.py:305

**All bindings (1 unique):**
- <code>utils.py</code> L305: <code>{rev_label_map[c + 1]: v for c, v in enumerate(average_precisions.tolist())}</code>

## Group 24: centers_in_crop -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>(bb_centers[:, 0] &gt; left) * (bb_centers[:, 0] &lt; right) * (bb_centers[:, 1] &gt; top</code> @ utils.py:516 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>centers_in_crop.any()</code> -- utils.py:520

**All bindings (1 unique):**
- <code>utils.py</code> L516: <code>(bb_centers[:, 0] &gt; left) * (bb_centers[:, 0] &lt; right) * (bb_centers[:, 1] &gt; top</code>

## Group 25: correct -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>ind.eq(targets.view(-1, 1).expand_as(ind))</code> @ utils.py:694 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>correct.view(-1)</code> -- utils.py:695

**All bindings (1 unique):**
- <code>utils.py</code> L694: <code>ind.eq(targets.view(-1, 1).expand_as(ind))</code>

## Group 26: correct.view(-1) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>ind.eq(targets.view(-1, 1).expand_as(ind))</code> @ utils.py:694 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>correct.view(-1).float()</code> -- utils.py:695

**All bindings (1 unique):**
- <code>utils.py</code> L694: <code>ind.eq(targets.view(-1, 1).expand_as(ind))</code>

## Group 27: correct.view(-1).float() -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>ind.eq(targets.view(-1, 1).expand_as(ind))</code> @ utils.py:694 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>correct.view(-1).float().sum()</code> -- utils.py:695

**All bindings (1 unique):**
- <code>utils.py</code> L694: <code>ind.eq(targets.view(-1, 1).expand_as(ind))</code>

## Group 28: correct_total -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>correct.view(-1).float().sum()</code> @ utils.py:695 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>correct_total.item()</code> -- utils.py:696

**All bindings (1 unique):**
- <code>utils.py</code> L695: <code>correct.view(-1).float().sum()</code>

## Group 29: cumul_precision[recalls_above_t] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>cumul_precision[recalls_above_t].max()</code> -- utils.py:296


## Group 30: d -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>for target</code> @ utils.py:598 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>d(new_image, adjust_factor)</code> -- utils.py:608

**All bindings (1 unique):**
- <code>utils.py</code> L598: <code>for target</code>

## Group 31: det_class_boxes -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>det_boxes[det_labels == c]</code> @ utils.py:233 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>det_class_boxes.size(0)</code> -- utils.py:235

**All bindings (1 unique):**
- <code>utils.py</code> L233: <code>det_boxes[det_labels == c]</code>

## Group 32: det_class_boxes[d] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>det_class_boxes[d].unsqueeze(0)</code> -- utils.py:248


## Group 33: det_labels[i] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>det_labels[i].size(0)</code> -- utils.py:209


## Group 34: elem -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>comprehension target</code> @ generatevocdata.py:34 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>elem.replace(' ', '')</code> -- generatevocdata.py:34

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L34: <code>comprehension target</code>

## Group 35: file -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>for target</code> @ annotation.py:30 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>file.split('/')</code> -- annotation.py:32

**All bindings (1 unique):**
- <code>annotation.py</code> L30: <code>for target</code>

## Group 36: image -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter image</code> @ preprocess.py:145 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>image.copy()</code> -- preprocess.py:146

**All bindings (1 unique):**
- <code>preprocess.py</code> L145: <code>parameter image</code>

## Group 37: image -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter image</code> @ rescaling.py:87 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>image.copy()</code> -- rescaling.py:88

**All bindings (1 unique):**
- <code>rescaling.py</code> L87: <code>parameter image</code>

## Group 38: img_meta_df['Size'] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>img_meta_df['Size'].tolist()</code> -- datavisualizer.py:32


## Group 39: ind -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>(tuple) scores.topk(k, 1, True, True)</code> @ utils.py:693 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>ind.eq(targets.view(-1, 1).expand_as(ind))</code> -- utils.py:694

**All bindings (1 unique):**
- <code>utils.py</code> L693: <code>(tuple) scores.topk(k, 1, True, True)</code>

## Group 40: key -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ annotation.py:62 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>key.split('/')</code> -- annotation.py:63

**All bindings (1 unique):**
- <code>annotation.py</code> L62: <code>for target</code>

## Group 41: label_string -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>""</code> @ generatevocdata.py:29 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>label_string.split(',')</code> -- generatevocdata.py:33

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L29: <code>""</code>

## Group 42: max_overlap -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) torch.max(overlaps.squeeze(0), dim=0)</code> @ utils.py:261 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>max_overlap.item()</code> -- utils.py:269

**All bindings (1 unique):**
- <code>utils.py</code> L261: <code>(tuple) torch.max(overlaps.squeeze(0), dim=0)</code>

## Group 43: object.find('name').text -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>for target</code> @ utils.py:63 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>object.find('name').text.lower()</code> -- utils.py:67

**All bindings (1 unique):**
- <code>utils.py</code> L63: <code>for target</code>

## Group 44: object.find('name').text -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>for target</code> @ annotation.py:42 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>object.find('name').text.lower()</code> -- annotation.py:43

**All bindings (1 unique):**
- <code>annotation.py</code> L42: <code>for target</code>

## Group 45: object.find('name').text.lower() -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>for target</code> @ utils.py:63 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>object.find('name').text.lower().strip()</code> -- utils.py:67

**All bindings (1 unique):**
- <code>utils.py</code> L63: <code>for target</code>

## Group 46: object.find('name').text.lower() -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>for target</code> @ annotation.py:42 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>object.find('name').text.lower().strip()</code> -- annotation.py:43

**All bindings (1 unique):**
- <code>annotation.py</code> L42: <code>for target</code>

## Group 47: object_boxes -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>true_class_boxes[true_class_images == this_image]</code> @ utils.py:252 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>object_boxes.size(0)</code> -- utils.py:255

**All bindings (1 unique):**
- <code>utils.py</code> L252: <code>true_class_boxes[true_class_images == this_image]</code>

## Group 48: overlap.max() -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>overlap.squeeze(0)</code> @ utils.py:503 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>overlap.max().item()</code> -- utils.py:506

**All bindings (1 unique):**
- <code>utils.py</code> L503: <code>overlap.squeeze(0)</code>

## Group 49: overlaps -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>find_jaccard_overlap(this_detection_box, object_boxes)</code> @ utils.py:260 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>overlaps.squeeze(0)</code> -- utils.py:261

**All bindings (1 unique):**
- <code>utils.py</code> L260: <code>find_jaccard_overlap(this_detection_box, object_boxes)</code>

## Group 50: param.grad.data -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>for target</code> @ utils.py:750 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>param.grad.data.clamp_(-grad_clip, grad_clip)</code> -- utils.py:752

**All bindings (1 unique):**
- <code>utils.py</code> L750: <code>for target</code>

## Group 51: recalls_above_t -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>cumul_recall &gt;= t</code> @ utils.py:294 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>recalls_above_t.any()</code> -- utils.py:295

**All bindings (1 unique):**
- <code>utils.py</code> L294: <code>cumul_recall &gt;= t</code>

## Group 52: sampler -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>imgnames.copy()</code> @ generatevocdata.py:66 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>sampler.pop()</code> -- generatevocdata.py:73

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L66: <code>imgnames.copy()</code>

## Group 53: scores -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter scores</code> @ utils.py:683 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>scores.topk(k, 1, True, True)</code> -- utils.py:693

**All bindings (1 unique):**
- <code>utils.py</code> L683: <code>parameter scores</code>

## Group 54: self -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ utils.py:726 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.reset()</code> -- utils.py:727

**All bindings (1 unique):**
- <code>utils.py</code> L726: <code>parameter self</code>

## Group 55: set_1[:, 2:] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>set_1[:, 2:].unsqueeze(1)</code> -- utils.py:381


## Group 56: set_1[:, :2] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>set_1[:, :2].unsqueeze(1)</code> -- utils.py:380


## Group 57: set_2[:, 2:] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>set_2[:, 2:].unsqueeze(0)</code> -- utils.py:381


## Group 58: set_2[:, :2] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>set_2[:, :2].unsqueeze(0)</code> -- utils.py:380


## Group 59: targets.view(-1, 1) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter targets</code> @ utils.py:683 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>targets.view(-1, 1).expand_as(ind)</code> -- utils.py:694

**All bindings (1 unique):**
- <code>utils.py</code> L683: <code>parameter targets</code>

## Group 60: true_class_boxes -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>true_boxes[true_labels == c]</code> @ utils.py:222 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>true_class_boxes.size(0)</code> -- utils.py:265

**All bindings (1 unique):**
- <code>utils.py</code> L222: <code>true_boxes[true_labels == c]</code>

## Group 61: true_class_difficulties -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>true_difficulties[true_labels == c]</code> @ utils.py:223 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>true_class_difficulties.size(0)</code> -- utils.py:228

**All bindings (1 unique):**
- <code>utils.py</code> L223: <code>true_difficulties[true_labels == c]</code>

## Group 62: true_labels[i] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>true_labels[i].size(0)</code> -- utils.py:197


## Group 63: transform -> library/albumentations (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>A.Compose([], bbox_params=A.BboxParams(format='pascal_voc', min_visibility=min_v</code> @ preprocess.py:221 |
| Owner | albumentations |
| Proposed GT | library / albumentations |

**Representative expressions:**

- <code>transform(image=image, bboxes=bboxes, category_ids=category_ids)</code> -- preprocess.py:222

**All bindings (1 unique):**
- <code>preprocess.py</code> L221: <code>A.Compose([], bbox_params=A.BboxParams(format='pascal_voc', min_visibility=min_v</code>

## Group 64: transform -> library/albumentations (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>A.Compose([\n            A.RandomRain (slant_lower=-10, slant_upper=10, drop_len</code> @ preprocess.py:285 |
| Owner | albumentations |
| Proposed GT | library / albumentations |

**Representative expressions:**

- <code>transform(image=image, bboxes=bboxes, category_ids=category_ids)</code> -- preprocess.py:291

**All bindings (1 unique):**
- <code>preprocess.py</code> L285: <code>A.Compose([\n            A.RandomRain (slant_lower=-10, slant_upper=10, drop_len</code>

## Group 65: transform -> library/albumentations (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>A.Compose([\n             A.MotionBlur(blur_limit=blur_limit , always_apply=Fals</code> @ preprocess.py:329 |
| Owner | albumentations |
| Proposed GT | library / albumentations |

**Representative expressions:**

- <code>transform(image=image, bboxes=bboxes, category_ids=category_ids)</code> -- preprocess.py:335

**All bindings (1 unique):**
- <code>preprocess.py</code> L329: <code>A.Compose([\n             A.MotionBlur(blur_limit=blur_limit , always_apply=Fals</code>

## Group 66: transform -> library/albumentations (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>A.Compose([\n        A.RandomBrightnessContrast(p=p),\n        ], bbox_params=A.</code> @ preprocess.py:339 |
| Owner | albumentations |
| Proposed GT | library / albumentations |

**Representative expressions:**

- <code>transform(image=image, bboxes=bboxes, category_ids=category_ids)</code> -- preprocess.py:343

**All bindings (1 unique):**
- <code>preprocess.py</code> L339: <code>A.Compose([\n        A.RandomBrightnessContrast(p=p),\n        ], bbox_params=A.</code>

## Group 67: transform -> library/albumentations (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>A.Compose([\n        A.Resize(width=rwidth, height=rheight),\n        ], bbox_pa</code> @ preprocess.py:347 |
| Owner | albumentations |
| Proposed GT | library / albumentations |

**Representative expressions:**

- <code>transform(image=image, bboxes=bboxes, category_ids=category_ids)</code> -- preprocess.py:351

**All bindings (1 unique):**
- <code>preprocess.py</code> L347: <code>A.Compose([\n        A.Resize(width=rwidth, height=rheight),\n        ], bbox_pa</code>

## Group 68: transform -> library/albumentations (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>A.Compose([\n        A.HorizontalFlip(p=p),\n        ], bbox_params=A.BboxParams</code> @ preprocess.py:355 |
| Owner | albumentations |
| Proposed GT | library / albumentations |

**Representative expressions:**

- <code>transform(image=image, bboxes=bboxes, category_ids=category_ids)</code> -- preprocess.py:359

**All bindings (1 unique):**
- <code>preprocess.py</code> L355: <code>A.Compose([\n        A.HorizontalFlip(p=p),\n        ], bbox_params=A.BboxParams</code>

## Group 69: transform -> library/albumentations (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>A.Compose([\n        A.CenterCrop(rwidth, rheight)\n        ], bbox_params=A.Bbo</code> @ preprocess.py:363 |
| Owner | albumentations |
| Proposed GT | library / albumentations |

**Representative expressions:**

- <code>transform(image=image, bboxes=bboxes, category_ids=category_ids)</code> -- preprocess.py:367

**All bindings (1 unique):**
- <code>preprocess.py</code> L363: <code>A.Compose([\n        A.CenterCrop(rwidth, rheight)\n        ], bbox_params=A.Bbo</code>

## Group 70: transform -> library/albumentations (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>A.Compose([\n    #A.Resize(width=450, height=450),\n    #A.HorizontalFlip(p=1.0)</code> @ rescaling.py:101 |
| Owner | albumentations |
| Proposed GT | library / albumentations |

**Representative expressions:**

- <code>transform(image=image, bboxes=bboxes, category_ids=category_ids)</code> -- rescaling.py:115

**All bindings (1 unique):**
- <code>rescaling.py</code> L101: <code>A.Compose([\n    #A.Resize(width=450, height=450),\n    #A.HorizontalFlip(p=1.0)</code>

## Group 71: fig -> library/matplotlib (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>plt.figure(figsize=(8, 8))</code> @ datavisualizer.py:40 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>fig.add_subplot(111)</code> -- datavisualizer.py:41

**All bindings (1 unique):**
- <code>datavisualizer.py</code> L40: <code>plt.figure(figsize=(8, 8))</code>

## Group 72: img_meta_df -> library/pandas (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>pd.DataFrame.from_dict([img_meta]).T.reset_index().set_axis(['FileName', 'Size']</code> @ datavisualizer.py:31 |
| Owner | pandas |
| Proposed GT | library / pandas |

**Representative expressions:**

- <code>img_meta_df.head()</code> -- datavisualizer.py:36

**All bindings (1 unique):**
- <code>datavisualizer.py</code> L31: <code>pd.DataFrame.from_dict([img_meta]).T.reset_index().set_axis(['FileName', 'Size']</code>

## Group 73: annote_labels -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ generatevocdata.py:54 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>annote_labels.append(labelname)</code> -- generatevocdata.py:57

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L54: <code>[]</code>

## Group 74: test_list -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ generatevocdata.py:69 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>test_list.append(elem)</code> -- generatevocdata.py:76

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L69: <code>[]</code>

## Group 75: train_list -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ generatevocdata.py:67 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>train_list.append(elem)</code> -- generatevocdata.py:80

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L67: <code>[]</code>

## Group 76: val_list -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ generatevocdata.py:68 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>val_list.append(elem)</code> -- generatevocdata.py:78

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L68: <code>[]</code>

## Group 77: average_precisions -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.zeros((n_classes - 1), dtype=torch.float)</code> @ utils.py:218 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>average_precisions.mean()</code> -- utils.py:302

**All bindings (1 unique):**
- <code>utils.py</code> L218: <code>torch.zeros((n_classes - 1), dtype=torch.float)</code>

## Group 78: average_precisions.mean() -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.zeros((n_classes - 1), dtype=torch.float)</code> @ utils.py:218 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>average_precisions.mean().item()</code> -- utils.py:302

**All bindings (1 unique):**
- <code>utils.py</code> L218: <code>torch.zeros((n_classes - 1), dtype=torch.float)</code>

## Group 79: crop -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.FloatTensor([left, top, right, bottom])</code> @ utils.py:498 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>crop.unsqueeze(0)</code> -- utils.py:501

**All bindings (1 unique):**
- <code>utils.py</code> L498: <code>torch.FloatTensor([left, top, right, bottom])</code>

## Group 80: det_boxes -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.cat(det_boxes, dim=0)</code> @ utils.py:211 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>det_boxes.size(0)</code> -- utils.py:215

**All bindings (1 unique):**
- <code>utils.py</code> L211: <code>torch.cat(det_boxes, dim=0)</code>

## Group 81: det_images -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.LongTensor(det_images).to(device)</code> @ utils.py:210 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>det_images.size(0)</code> -- utils.py:215

**All bindings (1 unique):**
- <code>utils.py</code> L210: <code>torch.LongTensor(det_images).to(device)</code>

## Group 82: det_labels -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.cat(det_labels, dim=0)</code> @ utils.py:212 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>det_labels.size(0)</code> -- utils.py:215

**All bindings (1 unique):**
- <code>utils.py</code> L212: <code>torch.cat(det_labels, dim=0)</code>

## Group 83: det_scores -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.cat(det_scores, dim=0)</code> @ utils.py:213 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>det_scores.size(0)</code> -- utils.py:215

**All bindings (1 unique):**
- <code>utils.py</code> L213: <code>torch.cat(det_scores, dim=0)</code>

## Group 84: filler -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.FloatTensor(filler)</code> @ utils.py:432 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>filler.unsqueeze(1)</code> -- utils.py:433

**All bindings (1 unique):**
- <code>utils.py</code> L432: <code>torch.FloatTensor(filler)</code>

## Group 85: filler.unsqueeze(1) -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.FloatTensor(filler)</code> @ utils.py:432 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>filler.unsqueeze(1).unsqueeze(1)</code> -- utils.py:433

**All bindings (1 unique):**
- <code>utils.py</code> L432: <code>torch.FloatTensor(filler)</code>

## Group 86: precisions -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.zeros((len(recall_thresholds)), dtype=torch.float).to(device)</code> @ utils.py:292 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>precisions.mean()</code> -- utils.py:299

**All bindings (1 unique):**
- <code>utils.py</code> L292: <code>torch.zeros((len(recall_thresholds)), dtype=torch.float).to(device)</code>

## Group 87: true_boxes -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.cat(true_boxes, dim=0)</code> @ utils.py:200 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>true_boxes.size(0)</code> -- utils.py:204

**All bindings (1 unique):**
- <code>utils.py</code> L200: <code>torch.cat(true_boxes, dim=0)</code>

## Group 88: true_images -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.LongTensor(true_images).to(\n        device)</code> @ utils.py:198 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>true_images.size(0)</code> -- utils.py:204

**All bindings (1 unique):**
- <code>utils.py</code> L198: <code>torch.LongTensor(true_images).to(\n        device)</code>

## Group 89: true_labels -> library/torch (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>torch.cat(true_labels, dim=0)</code> @ utils.py:201 |
| Owner | torch |
| Proposed GT | library / torch |

**Representative expressions:**

- <code>true_labels.size(0)</code> -- utils.py:204

**All bindings (1 unique):**
- <code>utils.py</code> L201: <code>torch.cat(true_labels, dim=0)</code>

## Group 90: ET -> library/xml (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import xml.etree.ElementTree</code> @ utils.py:5 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>ET.parse(annotation_path)</code> -- utils.py:57

**All bindings (1 unique):**
- <code>utils.py</code> L5: <code>import xml.etree.ElementTree</code>

## Group 91: ET -> library/xml (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import xml.etree.ElementTree</code> @ generatevocdata.py:11 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>ET.parse(annote)</code> -- generatevocdata.py:52

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L11: <code>import xml.etree.ElementTree</code>

## Group 92: ET -> library/xml (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import xml.etree.ElementTree</code> @ xmlfilerename.py:8 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>ET.parse(path)</code> -- xmlfilerename.py:10

**All bindings (1 unique):**
- <code>xmlfilerename.py</code> L8: <code>import xml.etree.ElementTree</code>

## Group 93: ET -> library/xml (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import xml.etree.ElementTree</code> @ read pascalvoc annotation.py:8 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>ET.parse(path)</code> -- read pascalvoc annotation.py:12

**All bindings (1 unique):**
- <code>read pascalvoc annotation.py</code> L8: <code>import xml.etree.ElementTree</code>

## Group 94: ET -> library/xml (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import xml.etree.ElementTree</code> @ preprocess.py:15 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>ET.parse(path)</code> -- preprocess.py:99

**All bindings (1 unique):**
- <code>preprocess.py</code> L15: <code>import xml.etree.ElementTree</code>

## Group 95: ET -> library/xml (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import xml.etree.ElementTree</code> @ annotation.py:4 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>ET.parse(file)</code> -- annotation.py:37

**All bindings (1 unique):**
- <code>annotation.py</code> L4: <code>import xml.etree.ElementTree</code>

## Group 96: root -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>tree.getroot()</code> @ utils.py:58 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>root.iter('object')</code> -- utils.py:63

**All bindings (1 unique):**
- <code>utils.py</code> L58: <code>tree.getroot()</code>

## Group 97: root -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>tree.getroot()</code> @ generatevocdata.py:53 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>root.findall('*/name')</code> -- generatevocdata.py:55

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L53: <code>tree.getroot()</code>

## Group 98: root -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>tree.getroot()</code> @ xmlfilerename.py:11 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>root.find('filename')</code> -- xmlfilerename.py:12

**All bindings (1 unique):**
- <code>xmlfilerename.py</code> L11: <code>tree.getroot()</code>

## Group 99: root -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>tree.getroot()</code> @ annotation.py:38 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>root.iter('object')</code> -- annotation.py:42

**All bindings (1 unique):**
- <code>annotation.py</code> L38: <code>tree.getroot()</code>

## Group 100: string -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ele.text</code> @ xmlfilerename.py:13 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>string.replace('jpg', 'JPEG')</code> -- xmlfilerename.py:15

**All bindings (1 unique):**
- <code>xmlfilerename.py</code> L13: <code>ele.text</code>

## Group 101: tree -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ET.parse(annotation_path)</code> @ utils.py:57 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>tree.getroot()</code> -- utils.py:58

**All bindings (1 unique):**
- <code>utils.py</code> L57: <code>ET.parse(annotation_path)</code>

## Group 102: tree -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ET.parse(annote)</code> @ generatevocdata.py:52 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>tree.getroot()</code> -- generatevocdata.py:53

**All bindings (1 unique):**
- <code>generatevocdata.py</code> L52: <code>ET.parse(annote)</code>

## Group 103: tree -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ET.parse(path)</code> @ read pascalvoc annotation.py:12 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>tree.getroot()</code> -- read pascalvoc annotation.py:13

**All bindings (1 unique):**
- <code>read pascalvoc annotation.py</code> L12: <code>ET.parse(path)</code>

## Group 104: tree -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ET.parse(path)</code> @ preprocess.py:99 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>tree.getroot()</code> -- preprocess.py:100

**All bindings (1 unique):**
- <code>preprocess.py</code> L99: <code>ET.parse(path)</code>

## Group 105: tree -> library/xml (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ET.parse(file)</code> @ annotation.py:37 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>tree.getroot()</code> -- annotation.py:38

**All bindings (1 unique):**
- <code>annotation.py</code> L37: <code>ET.parse(file)</code>
