# MAHE_OD_DATASET — Needs Annotation (139 records)

These records do not yet have `verification_level` or
`expected_*` fields confirmed by a human annotator.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| utils.py:57:11 | `ET.parse(annotation_path)` |  /  | library / xml | - | - |  |
| utils.py:58:11 | `tree.getroot()` |  /  | library / xml | - | - |  |
| utils.py:63:18 | `root.iter('object')` |  /  | library / xml | - | - |  |
| utils.py:65:24 | `object.find('difficult')` |  /  | library / xml | - | - |  |
| utils.py:67:16 | `object.find('name').text.lower()` |  /  | library / xml | - | - |  |
| utils.py:67:16 | `object.find('name').text.lower().strip()` |  /  | library / xml | - | - |  |
| utils.py:67:16 | `object.find('name')` |  /  | library / xml | - | - |  |
| utils.py:71:15 | `object.find('bndbox')` |  /  | library / xml | - | - |  |
| utils.py:72:19 | `bbox.find('xmin')` |  /  | library / xml | - | - |  |
| utils.py:73:19 | `bbox.find('ymin')` |  /  | library / xml | - | - |  |
| utils.py:74:19 | `bbox.find('xmax')` |  /  | library / xml | - | - |  |
| utils.py:75:19 | `bbox.find('ymax')` |  /  | library / xml | - | - |  |
| utils.py:166:11 | `tensor.dim()` |  /  | local / local | - | - |  |
| utils.py:167:19 | `tensor.dim()` |  /  | local / local | - | - |  |
| utils.py:169:21 | `tensor.index_select(dim=d, index=torch.arange(start=0, end=tensor.s...` |  /  | local / local | - | - |  |
| utils.py:170:73 | `tensor.size(d)` |  /  | local / local | - | - |  |
| utils.py:197:33 | `true_labels[i].size(0)` |  /  | local / local | - | - |  |
| utils.py:204:11 | `true_images.size(0)` |  /  | library / torch | - | - |  |
| utils.py:204:34 | `true_boxes.size(0)` |  /  | library / torch | - | - |  |
| utils.py:204:56 | `true_labels.size(0)` |  /  | library / torch | - | - |  |
| utils.py:209:32 | `det_labels[i].size(0)` |  /  | local / local | - | - |  |
| utils.py:215:11 | `det_images.size(0)` |  /  | library / torch | - | - |  |
| utils.py:215:33 | `det_boxes.size(0)` |  /  | library / torch | - | - |  |
| utils.py:215:54 | `det_labels.size(0)` |  /  | library / torch | - | - |  |
| utils.py:215:76 | `det_scores.size(0)` |  /  | library / torch | - | - |  |
| utils.py:224:31 | `(1 - true_class_difficulties).sum()` |  /  | library / torch | - | - |  |
| utils.py:224:31 | `(1 - true_class_difficulties).sum().item()` |  /  | library / torch | - | - |  |
| utils.py:228:49 | `true_class_difficulties.size(0)` |  /  | library / torch | - | - |  |
| utils.py:235:29 | `det_class_boxes.size(0)` |  /  | library / torch | - | - |  |
| utils.py:248:33 | `det_class_boxes[d].unsqueeze(0)` |  /  | library / torch | - | - |  |
| utils.py:255:15 | `object_boxes.size(0)` |  /  | library / torch | - | - |  |
| utils.py:261:41 | `overlaps.squeeze(0)` |  /  | local / local | - | - |  |
| utils.py:265:50 | `true_class_boxes.size(0)` |  /  | library / torch | - | - |  |
| utils.py:269:15 | `max_overlap.item()` |  /  | library / torch | - | - |  |
| utils.py:295:15 | `recalls_above_t.any()` |  /  | local / local | - | - |  |
| utils.py:296:32 | `cumul_precision[recalls_above_t].max()` |  /  | local / local | - | - |  |
| utils.py:299:36 | `precisions.mean()` |  /  | library / torch | - | - |  |
| utils.py:302:29 | `average_precisions.mean()` |  /  | library / torch | - | - |  |
| utils.py:302:29 | `average_precisions.mean().item()` |  /  | library / torch | - | - |  |
| utils.py:305:72 | `average_precisions.tolist()` |  /  | library / torch | - | - |  |
| utils.py:380:29 | `set_1[:, :2].unsqueeze(1)` |  /  | local / local | - | - |  |
| utils.py:380:56 | `set_2[:, :2].unsqueeze(0)` |  /  | local / local | - | - |  |
| utils.py:381:29 | `set_1[:, 2:].unsqueeze(1)` |  /  | local / local | - | - |  |
| utils.py:381:56 | `set_2[:, 2:].unsqueeze(0)` |  /  | local / local | - | - |  |
| utils.py:404:12 | `areas_set_1.unsqueeze(1)` |  /  | local / local | - | - |  |
| utils.py:404:39 | `areas_set_2.unsqueeze(0)` |  /  | local / local | - | - |  |
| utils.py:424:17 | `image.size(1)` |  /  | library / torchvision | - | - |  |
| utils.py:425:17 | `image.size(2)` |  /  | library / torchvision | - | - |  |
| utils.py:433:67 | `filler.unsqueeze(1)` |  /  | library / torch | - | - |  |
| utils.py:433:67 | `filler.unsqueeze(1).unsqueeze(1)` |  /  | library / torch | - | - |  |
| utils.py:465:17 | `image.size(1)` |  /  | library / torchvision | - | - |  |
| utils.py:466:17 | `image.size(2)` |  /  | library / torchvision | - | - |  |
| utils.py:501:43 | `crop.unsqueeze(0)` |  /  | library / torch | - | - |  |
| utils.py:503:22 | `overlap.squeeze(0)` |  /  | local / local | - | - |  |
| utils.py:506:15 | `overlap.max()` |  /  | local / local | - | - |  |
| utils.py:506:15 | `overlap.max().item()` |  /  | local / local | - | - |  |
| utils.py:520:19 | `centers_in_crop.any()` |  /  | local / local | - | - |  |
| utils.py:546:16 | `FT.hflip(image)` |  /  | library / torchvision | - | - |  |
| utils.py:569:16 | `FT.resize(image, dims)` |  /  | library / torchvision | - | - |  |
| utils.py:608:24 | `d(new_image, adjust_factor)` |  /  | library / torchvision | - | - |  |
| utils.py:641:20 | `FT.to_tensor(new_image)` |  /  | library / torchvision | - | - |  |
| utils.py:653:20 | `FT.to_pil_image(new_image)` |  /  | library / torchvision | - | - |  |
| utils.py:663:16 | `FT.to_tensor(new_image)` |  /  | library / torchvision | - | - |  |
| utils.py:666:16 | `FT.normalize(new_image, mean=mean, std=std)` |  /  | library / torchvision | - | - |  |
| utils.py:692:17 | `targets.size(0)` |  /  | local / local | - | - |  |
| utils.py:693:13 | `scores.topk(k, 1, True, True)` |  /  | local / local | - | - |  |
| utils.py:694:14 | `ind.eq(targets.view(-1, 1).expand_as(ind))` |  /  | unknown / unknown | - | - |  |
| utils.py:694:21 | `targets.view(-1, 1)` |  /  | local / local | - | - |  |
| utils.py:694:21 | `targets.view(-1, 1).expand_as(ind)` |  /  | local / local | - | - |  |
| utils.py:695:20 | `correct.view(-1)` |  /  | unknown / unknown | - | - |  |
| utils.py:695:20 | `correct.view(-1).float()` |  /  | unknown / unknown | - | - |  |
| utils.py:695:20 | `correct.view(-1).float().sum()` |  /  | unknown / unknown | - | - |  |
| utils.py:696:11 | `correct_total.item()` |  /  | unknown / unknown | - | - |  |
| utils.py:727:8 | `self.reset()` |  /  | local / local | - | - |  |
| utils.py:752:16 | `param.grad.data.clamp_(-grad_clip, grad_clip)` |  /  | unknown / unknown | - | - |  |
| datavisualizer.py:32:48 | `img_meta_df['Size'].tolist()` |  /  | library / pandas | - | - |  |
| datavisualizer.py:36:0 | `img_meta_df.head()` |  /  | library / pandas | - | - |  |
| datavisualizer.py:41:5 | `fig.add_subplot(111)` |  /  | library / matplotlib | - | - |  |
| datavisualizer.py:42:9 | `ax.scatter(img_meta_df.Width, img_meta_df.Height, color='blue', alp...` |  /  | library / matplotlib | - | - |  |
| datavisualizer.py:43:0 | `ax.set_title('Image Resolution')` |  /  | library / matplotlib | - | - |  |
| datavisualizer.py:44:0 | `ax.set_xlabel('Width', size=14)` |  /  | library / matplotlib | - | - |  |
| datavisualizer.py:45:0 | `ax.set_ylabel('Height', size=14)` |  /  | library / matplotlib | - | - |  |
| generatevocdata.py:33:13 | `label_string.split(',')` |  /  | local / local | - | - |  |
| generatevocdata.py:34:15 | `elem.replace(' ', '')` |  /  | local / local | - | - |  |
| generatevocdata.py:38:11 | `filename.endswith('.jpg')` |  /  | library / os | - | - |  |
| generatevocdata.py:39:18 | `filename.rstrip('.jpg')` |  /  | library / os | - | - |  |
| generatevocdata.py:40:12 | `imgnames.append(img)` |  /  | local / local | - | - |  |
| generatevocdata.py:52:19 | `ET.parse(annote)` |  /  | library / xml | - | - |  |
| generatevocdata.py:53:19 | `tree.getroot()` |  /  | library / xml | - | - |  |
| generatevocdata.py:55:29 | `root.findall('*/name')` |  /  | library / xml | - | - |  |
| generatevocdata.py:57:16 | `annote_labels.append(labelname)` |  /  | local / local | - | - |  |
| generatevocdata.py:59:20 | `annotations[labelname].append(img)` |  /  | local / local | - | - |  |
| generatevocdata.py:66:14 | `imgnames.copy()` |  /  | local / local | - | - |  |
| generatevocdata.py:73:15 | `sampler.pop()` |  /  | local / local | - | - |  |
| generatevocdata.py:76:12 | `test_list.append(elem)` |  /  | local / local | - | - |  |
| generatevocdata.py:78:12 | `val_list.append(elem)` |  /  | local / local | - | - |  |
| generatevocdata.py:80:12 | `train_list.append(elem)` |  /  | local / local | - | - |  |
| xmlfilerename.py:10:7 | `ET.parse(path)` |  /  | library / xml | - | - |  |
| xmlfilerename.py:11:7 | `tree.getroot()` |  /  | library / xml | - | - |  |
| xmlfilerename.py:12:5 | `root.find('filename')` |  /  | library / xml | - | - |  |
| xmlfilerename.py:15:4 | `string.replace('jpg', 'JPEG')` |  /  | library / xml | - | - |  |
| xmlfilerename.py:20:0 | `tree.write(path)` |  /  | library / xml | - | - |  |
| read pascalvoc annotation.py:12:7 | `ET.parse(path)` |  /  | library / xml | - | - |  |
| read pascalvoc annotation.py:13:7 | `tree.getroot()` |  /  | library / xml | - | - |  |
| read pascalvoc annotation.py:15:13 | `root.find('size')` |  /  | library / xml | - | - |  |
| read pascalvoc annotation.py:16:12 | `root.find('size')` |  /  | library / xml | - | - |  |
| read pascalvoc annotation.py:21:14 | `root.findall('object')` |  /  | library / xml | - | - |  |
| preprocess.py:99:11 | `ET.parse(path)` |  /  | library / xml | - | - |  |
| preprocess.py:100:11 | `tree.getroot()` |  /  | library / xml | - | - |  |
| preprocess.py:102:17 | `root.find('size')` |  /  | library / xml | - | - |  |
| preprocess.py:103:16 | `root.find('size')` |  /  | library / xml | - | - |  |
| preprocess.py:104:19 | `root.find('size')` |  /  | library / xml | - | - |  |
| preprocess.py:108:18 | `root.findall('object')` |  /  | library / xml | - | - |  |
| preprocess.py:146:10 | `image.copy()` |  /  | local / local | - | - |  |
| preprocess.py:150:4 | `plt.figure(figsize=(12, 12))` |  /  | library / matplotlib | - | - |  |
| preprocess.py:151:4 | `plt.axis('off')` |  /  | library / matplotlib | - | - |  |
| preprocess.py:152:4 | `plt.imshow(img)` |  /  | library / matplotlib | - | - |  |
| preprocess.py:222:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` |  /  | library / albumentations | - | - |  |
| preprocess.py:291:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` |  /  | library / albumentations | - | - |  |
| preprocess.py:335:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` |  /  | library / albumentations | - | - |  |
| preprocess.py:343:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` |  /  | library / albumentations | - | - |  |
| preprocess.py:351:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` |  /  | library / albumentations | - | - |  |
| preprocess.py:359:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` |  /  | library / albumentations | - | - |  |
| preprocess.py:367:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` |  /  | library / albumentations | - | - |  |
| rescaling.py:88:10 | `image.copy()` |  /  | local / local | - | - |  |
| rescaling.py:115:14 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` |  /  | library / albumentations | - | - |  |
| annotation.py:32:9 | `file.split('/')` |  /  | library / glob | - | - |  |
| annotation.py:37:9 | `ET.parse(file)` |  /  | library / xml | - | - |  |
| annotation.py:38:9 | `tree.getroot()` |  /  | library / xml | - | - |  |
| annotation.py:42:16 | `root.iter('object')` |  /  | library / xml | - | - |  |
| annotation.py:43:12 | `object.find('name').text.lower()` |  /  | library / xml | - | - |  |
| annotation.py:43:12 | `object.find('name').text.lower().strip()` |  /  | library / xml | - | - |  |
| annotation.py:43:12 | `object.find('name')` |  /  | library / xml | - | - |  |
| annotation.py:44:11 | `object.find('bndbox')` |  /  | library / xml | - | - |  |
| annotation.py:45:15 | `bbox.find('xmin')` |  /  | library / xml | - | - |  |
| annotation.py:46:15 | `bbox.find('ymin')` |  /  | library / xml | - | - |  |
| annotation.py:47:15 | `bbox.find('xmax')` |  /  | library / xml | - | - |  |
| annotation.py:48:15 | `bbox.find('ymax')` |  /  | library / xml | - | - |  |
| annotation.py:63:8 | `key.split('/')` |  /  | local / local | - | - |  |
