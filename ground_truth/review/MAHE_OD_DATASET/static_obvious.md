# MAHE_OD_DATASET — static_obvious (341 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| utils.py:8:9 | `torch.device('cuda' if torch.cuda.is_available() else 'cpu')` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:8:32 | `torch.cuda.is_available()` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:29:34 | `enumerate(voc_labels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:31:34 | `label_map.items()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:53:53 | `enumerate(label_map.keys())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:53:63 | `label_map.keys()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:60:12 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:61:13 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:62:19 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:65:20 | `int(object.find('difficult').text == '1')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:72:15 | `int(bbox.find('xmin').text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:73:15 | `int(bbox.find('ymin').text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:74:15 | `int(bbox.find('xmax').text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:75:15 | `int(bbox.find('ymax').text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:77:8 | `boxes.append([xmin, ymin, xmax, ymax])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:78:8 | `labels.append(label_map[label])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:79:8 | `difficulties.append(difficult)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:92:17 | `os.path.abspath(voc07_path)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:93:19 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:94:20 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:101:13 | `open(os.path.join(path, 'ImageSets/Main/trainval.txt'))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:101:18 | `os.path.join(path, 'ImageSets/Main/trainval.txt')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:102:18 | `f.read()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:102:18 | `f.read().splitlines()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:106:22 | `parse_annotation(os.path.join(path, 'Annotations', id + '.xml'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| utils.py:106:39 | `os.path.join(path, 'Annotations', id + '.xml')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:107:15 | `len(objects)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:109:25 | `len(objects)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:110:12 | `train_objects.append(objects)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:111:12 | `train_images.append(os.path.join(path, 'JPEGImages', id + '.jpg'))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:111:32 | `os.path.join(path, 'JPEGImages', id + '.jpg')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:113:11 | `len(train_objects)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:113:33 | `len(train_images)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:116:9 | `open(os.path.join(output_folder, 'TRAIN_images.json'), 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:116:14 | `os.path.join(output_folder, 'TRAIN_images.json')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:117:8 | `json.dump(train_images, j)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:118:9 | `open(os.path.join(output_folder, 'TRAIN_objects.json'), 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:118:14 | `os.path.join(output_folder, 'TRAIN_objects.json')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:119:8 | `json.dump(train_objects, j)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:120:9 | `open(os.path.join(output_folder, 'label_map.json'), 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:120:14 | `os.path.join(output_folder, 'label_map.json')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:121:8 | `json.dump(label_map, j)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:166:27 | `len(m)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:167:13 | `range(tensor.dim())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:170:47 | `torch.arange(start=0, end=tensor.size(d), step=m[d])` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:170:47 | `torch.arange(start=0, end=tensor.size(d), step=m[d]).long()` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:189:11 | `len(det_boxes)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:189:29 | `len(det_labels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:189:48 | `len(det_scores)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:189:67 | `len(true_boxes)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:189:86 | `len(true_labels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:190:24 | `len(true_difficulties)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:192:16 | `len(label_map)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:195:18 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:196:13 | `range(len(true_labels))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:196:19 | `len(true_labels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:197:8 | `true_images.extend([i] * true_labels[i].size(0))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:198:18 | `torch.LongTensor(true_images)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:198:18 | `torch.LongTensor(true_images).to(device)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:200:17 | `torch.cat(true_boxes, dim=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:201:18 | `torch.cat(true_labels, dim=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:202:24 | `torch.cat(true_difficulties, dim=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:207:17 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:208:13 | `range(len(det_labels))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:208:19 | `len(det_labels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:209:8 | `det_images.extend([i] * det_labels[i].size(0))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:210:17 | `torch.LongTensor(det_images)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:210:17 | `torch.LongTensor(det_images).to(device)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:211:16 | `torch.cat(det_boxes, dim=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:212:17 | `torch.cat(det_labels, dim=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:213:17 | `torch.cat(det_scores, dim=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:218:25 | `torch.zeros(n_classes - 1, dtype=torch.float)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:219:13 | `range(1, n_classes)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:228:36 | `torch.zeros(true_class_difficulties.size(0), dtype=torch.uint8)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:228:36 | `torch.zeros(true_class_difficulties.size(0), dtype=torch.uint8).to(...` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:240:37 | `torch.sort(det_class_scores, dim=0, descending=True)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:245:25 | `torch.zeros(n_class_detections, dtype=torch.float)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:245:25 | `torch.zeros(n_class_detections, dtype=torch.float).to(device)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:246:26 | `torch.zeros(n_class_detections, dtype=torch.float)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:246:26 | `torch.zeros(n_class_detections, dtype=torch.float).to(device)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:247:17 | `range(n_class_detections)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:260:23 | `find_jaccard_overlap(this_detection_box, object_boxes)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| utils.py:261:31 | `torch.max(overlaps.squeeze(0), dim=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:265:27 | `torch.LongTensor(range(true_class_boxes.size(0)))` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:265:44 | `range(true_class_boxes.size(0))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:284:31 | `torch.cumsum(true_positives, dim=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:285:32 | `torch.cumsum(false_positives, dim=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:291:28 | `torch.arange(start=0, end=1.1, step=0.1)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:291:28 | `torch.arange(start=0, end=1.1, step=0.1).tolist()` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:292:21 | `torch.zeros(len(recall_thresholds), dtype=torch.float)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:292:21 | `torch.zeros(len(recall_thresholds), dtype=torch.float).to(device)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:292:34 | `len(recall_thresholds)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:293:20 | `enumerate(recall_thresholds)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:305:62 | `enumerate(average_precisions.tolist())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:317:11 | `torch.cat([(xy[:, 2:] + xy[:, :2]) / 2, xy[:, 2:] - xy[:, :2]], 1)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:328:11 | `torch.cat([cxcy[:, :2] - cxcy[:, 2:] / 2, cxcy[:, :2] + cxcy[:, 2:]...` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:349:11 | `torch.cat([(cxcy[:, :2] - priors_cxcy[:, :2]) / (priors_cxcy[:, 2:]...` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:350:22 | `torch.log(cxcy[:, 2:] / priors_cxcy[:, 2:])` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:366:11 | `torch.cat([gcxgcy[:, :2] * priors_cxcy[:, 2:] / 10 + priors_cxcy[:,...` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:367:22 | `torch.exp(gcxgcy[:, 2:] / 5)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:380:19 | `torch.max(set_1[:, :2].unsqueeze(1), set_2[:, :2].unsqueeze(0))` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:381:19 | `torch.min(set_1[:, 2:].unsqueeze(1), set_2[:, 2:].unsqueeze(0))` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:382:24 | `torch.clamp(upper_bounds - lower_bounds, min=0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:396:19 | `find_intersection(set_1, set_2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| utils.py:427:12 | `random.uniform(1, max_scale)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:428:12 | `int(scale * original_h)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:429:12 | `int(scale * original_w)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:432:13 | `torch.FloatTensor(filler)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:433:16 | `torch.ones((3, new_h, new_w), dtype=torch.float)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:438:11 | `random.randint(0, new_w - original_w)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:440:10 | `random.randint(0, new_h - original_h)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:445:24 | `torch.FloatTensor([left, top, left, top])` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:445:24 | `torch.FloatTensor([left, top, left, top]).unsqueeze(0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:470:22 | `random.choice([0.0, 0.1, 0.3, 0.5, 0.7, 0.9, None])` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:479:17 | `range(max_trials)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:483:22 | `random.uniform(min_scale, 1)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:484:22 | `random.uniform(min_scale, 1)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:485:20 | `int(scale_h * original_h)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:486:20 | `int(scale_w * original_w)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:494:19 | `random.randint(0, original_w - new_w)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:496:18 | `random.randint(0, original_h - new_h)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:498:19 | `torch.FloatTensor([left, top, right, bottom])` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:501:22 | `find_jaccard_overlap(crop.unsqueeze(0), boxes)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| utils.py:529:31 | `torch.max(new_boxes[:, :2], crop[:2])` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:531:31 | `torch.min(new_boxes[:, 2:], crop[2:])` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:572:15 | `torch.FloatTensor([image.width, image.height, image.width, image.he...` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:572:15 | `torch.FloatTensor([image.width, image.height, image.width, image.he...` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:576:19 | `torch.FloatTensor([dims[1], dims[0], dims[1], dims[0]])` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:576:19 | `torch.FloatTensor([dims[1], dims[0], dims[1], dims[0]]).unsqueeze(0)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:596:4 | `random.shuffle(distortions)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:599:11 | `random.random()` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:602:32 | `random.uniform(-18 / 255.0, 18 / 255.0)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:605:32 | `random.uniform(0.5, 1.5)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:638:20 | `photometric_distort(new_image)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| utils.py:645:11 | `random.random()` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:646:35 | `expand(new_image, boxes, filler=mean)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| utils.py:649:61 | `random_crop(new_image, new_boxes, new_labels, new_difficulties)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| utils.py:656:11 | `random.random()` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| utils.py:657:35 | `flip(new_image, new_boxes)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| utils.py:660:27 | `resize(new_image, new_boxes, dims=(300, 300))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| utils.py:680:4 | `print('DECAYING learning rate.\n The new LR is %f\n' % (optimizer.p...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| utils.py:718:8 | `torch.save(state, 'BEST_' + filename)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| datavisualizer.py:13:0 | `matplotlib.use('Agg')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| datavisualizer.py:23:28 | `Path('dataset')` | library / pathlib | library / pathlib | direct_import | static_obvious | v: direct import-backed API call |
| datavisualizer.py:23:28 | `Path('dataset').iterdir()` | library / pathlib | library / pathlib | direct_import | static_obvious | v: direct import-backed API call |
| datavisualizer.py:27:13 | `str(f)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| datavisualizer.py:27:23 | `imagesize.get('dataset/' + f)` | library / imagesize | library / imagesize | direct_import | static_obvious | v: direct import-backed API call |
| datavisualizer.py:31:14 | `pd.DataFrame.from_dict([img_meta]).T.reset_index()` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| datavisualizer.py:31:14 | `pd.DataFrame.from_dict([img_meta]).T.reset_index().set_axis(['FileN...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| datavisualizer.py:31:14 | `pd.DataFrame.from_dict([img_meta])` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| datavisualizer.py:32:35 | `pd.DataFrame(img_meta_df['Size'].tolist(), index=img_meta_df.index)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| datavisualizer.py:33:30 | `round(img_meta_df['Width'] / img_meta_df['Height'], 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| datavisualizer.py:35:0 | `print(f'Total Nr of Images in the dataset: {len(img_meta_df)}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| datavisualizer.py:35:44 | `len(img_meta_df)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| datavisualizer.py:40:6 | `plt.figure(figsize=(8, 8))` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| generatevocdata.py:20:8 | `print('probabilities must equal 1')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:21:8 | `exit()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:28:9 | `open(filename, 'r')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:31:32 | `line.rstrip()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:37:20 | `os.listdir('C:/PhD/Objective 1/bed/JPEGImages')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| generatevocdata.py:42:4 | `print('Labels:', labels, 'imgcnt:', len(imgnames))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:42:40 | `len(imgnames)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:51:11 | `os.path.isfile(annote)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| generatevocdata.py:62:12 | `print('Missing annotation for ', annote)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:63:12 | `exit()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:71:10 | `len(sampler)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:72:15 | `random()` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| generatevocdata.py:82:4 | `print('Training set:', len(train_list), 'validation set:', len(val_...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:82:27 | `len(train_list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:82:63 | `len(val_list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:82:91 | `len(test_list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:86:4 | `create_folder('C:/PhD/Objective 1/ImageSets/Main/')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| generatevocdata.py:87:9 | `open('C:/PhD/Objective 1/ImageSets/Main/train.txt', 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:89:12 | `outfile.write(name + '\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:90:9 | `open('C:/PhD/Objective 1/ImageSets/Main/val.txt', 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:92:12 | `outfile.write(name + '\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:93:9 | `open('C:/PhD/Objective 1/ImageSets/Main/trainval.txt', 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:95:12 | `outfile.write(name + '\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:97:12 | `outfile.write(name + '\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:99:9 | `open('C:/PhD/Objective 1/ImageSets/Main/test.txt', 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:101:12 | `outfile.write(name + '\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:105:13 | `open('C:/PhD/Objective 1/ImageSets/Main/' + label + '_train.txt', 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:108:20 | `outfile.write(name + ' 1\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:110:20 | `outfile.write(name + ' -1\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:111:13 | `open('C:/PhD/Objective 1/ImageSets/Main/' + label + '_val.txt', 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:114:20 | `outfile.write(name + ' 1\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:116:20 | `outfile.write(name + ' -1\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:117:13 | `open('C:/PhD/Objective 1/ImageSets/Main/' + label + '_test.txt', 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:120:20 | `outfile.write(name + ' 1\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:122:20 | `outfile.write(name + ' -1\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:125:7 | `os.path.exists(foldername)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| generatevocdata.py:126:8 | `print('folder already exists:', foldername)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:128:8 | `os.makedirs(foldername)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| generatevocdata.py:131:7 | `len(sys.argv)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:132:8 | `print('usage: python generate_vocdata.py <labelfile>')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| generatevocdata.py:133:8 | `sys.exit()` | library / sys | library / sys | direct_import | static_obvious | v: direct import-backed API call |
| generatevocdata.py:134:4 | `main(sys.argv[1])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| xmlfilerename.py:16:0 | `print(new)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| read pascalvoc annotation.py:15:9 | `int(root.find('size')[0].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| read pascalvoc annotation.py:16:8 | `int(root.find('size')[1].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| read pascalvoc annotation.py:25:11 | `int(member[1][0].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| read pascalvoc annotation.py:26:11 | `int(member[1][1].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| read pascalvoc annotation.py:27:11 | `int(member[1][2].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| read pascalvoc annotation.py:28:11 | `int(member[1][3].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| read pascalvoc annotation.py:30:4 | `bbox_coordinates.append([class_name, xmin, ymin, xmax, ymax])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| read pascalvoc annotation.py:32:0 | `print(bbox_coordinates)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:21:19 | `list(range(1, 181))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:21:24 | `range(1, 181)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:48:21 | `category_id_to_name.items()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:79:12 | `cv2.imread(path)` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:80:12 | `cv2.cvtColor(image, cv2.COLOR_BGR2RGB)` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:102:13 | `int(root.find('size')[0].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:103:12 | `int(root.find('size')[1].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:104:15 | `int(root.find('size')[2].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:112:15 | `int(member[4][0].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:113:15 | `int(member[4][1].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:114:15 | `int(member[4][2].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:115:15 | `int(member[4][3].text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:117:8 | `bboxes.append([xmin, ymin, xmax, ymax])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:118:8 | `category_ids.append(get_key(class_name))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:118:28 | `get_key(class_name)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:127:33 | `int(x_min)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:127:45 | `int(x_max)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:127:57 | `int(y_min)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:127:69 | `int(y_max)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:130:4 | `cv2.rectangle(img, (x_min, y_min), (x_max, y_max), color=color, thi...` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:132:37 | `cv2.getTextSize(class_name, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:133:4 | `cv2.rectangle(img, (x_min, y_min - int(1.3 * text_height)), (x_min ...` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:133:39 | `int(1.3 * text_height)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:134:4 | `cv2.putText(img, text=class_name, org=(x_min, y_min - int(0.3 * tex...` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:137:28 | `int(0.3 * text_height)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:147:29 | `zip(bboxes, category_ids)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:149:14 | `visualize_bbox(img, bbox, class_name)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:221:14 | `A.Compose([], bbox_params=A.BboxParams(format='pascal_voc', min_vis...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:221:40 | `A.BboxParams(format='pascal_voc', min_visibility=min_visibility, la...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:225:21 | `ResizeImage(transformed['image'], transformed['bboxes'], transforme...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:227:21 | `CCrop(transformed['image'], transformed['bboxes'], transformed['cat...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:229:14 | `ValueError(' Crop and resize both set to True. Choose One')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:232:21 | `HFlip(transformed['image'], transformed['bboxes'], transformed['cat...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:235:21 | `AddContrast(transformed['image'], transformed['bboxes'], transforme...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:237:17 | `AddNoise(transformed['image'], transformed['bboxes'], transformed['...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:238:17 | `AddBlurs(transformed['image'], transformed['bboxes'], transformed['...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:241:4 | `visualize(transformed['image'], transformed['bboxes'], transformed[...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:277:20 | `A.Compose([A.GaussNoise(var_limit=var_limit, mean=0, per_channel=Tr...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:278:12 | `A.GaussNoise(var_limit=var_limit, mean=0, per_channel=True, always_...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:279:27 | `A.BboxParams(format='pascal_voc', min_visibility=min_visibility, la...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:281:20 | `A.Compose([A.ISONoise(color_shift=(0.01, 0.05), intensity=intensity...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:282:12 | `A.ISONoise(color_shift=(0.01, 0.05), intensity=intensity, always_ap...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:283:27 | `A.BboxParams(format='pascal_voc', min_visibility=0.1, label_fields=...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:285:20 | `A.Compose([A.RandomRain(slant_lower=-10, slant_upper=10, drop_lengt...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:286:12 | `A.RandomRain(slant_lower=-10, slant_upper=10, drop_length=5, drop_w...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:287:27 | `A.BboxParams(format='pascal_voc', min_visibility=0.1, label_fields=...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:289:14 | `ValueError('Invalid Noise Type! Choose  1- GaussNoise   2- ISONoise...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:317:20 | `A.Compose([A.Blur(blur_limit=blur_limit, always_apply=False, p=p)],...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:318:12 | `A.Blur(blur_limit=blur_limit, always_apply=False, p=p)` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:319:27 | `A.BboxParams(format='pascal_voc', min_visibility=min_visibility, la...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:321:20 | `A.Compose([A.GaussianBlur(blur_limit=(3, blur_limit), sigma_limit=0...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:322:12 | `A.GaussianBlur(blur_limit=(3, blur_limit), sigma_limit=0, always_ap...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:323:27 | `A.BboxParams(format='pascal_voc', min_visibility=0.1, label_fields=...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:325:20 | `A.Compose([A.GlassBlur(sigma=0.7, max_delta=max_delta, iterations=2...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:326:12 | `A.GlassBlur(sigma=0.7, max_delta=max_delta, iterations=2, always_ap...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:327:27 | `A.BboxParams(format='pascal_voc', min_visibility=0.1, label_fields=...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:329:21 | `A.Compose([A.MotionBlur(blur_limit=blur_limit, always_apply=False, ...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:330:13 | `A.MotionBlur(blur_limit=blur_limit, always_apply=False, p=p)` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:331:28 | `A.BboxParams(format='pascal_voc', min_visibility=0.1, label_fields=...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:333:14 | `ValueError('Invalid Blur Type! Choose 1. Normalblur  2. GaussianBlu...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| preprocess.py:339:16 | `A.Compose([A.RandomBrightnessContrast(p=p)], bbox_params=A.BboxPara...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:340:8 | `A.RandomBrightnessContrast(p=p)` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:341:23 | `A.BboxParams(format='pascal_voc', min_visibility=min_visibility, la...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:347:16 | `A.Compose([A.Resize(width=rwidth, height=rheight)], bbox_params=A.B...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:348:8 | `A.Resize(width=rwidth, height=rheight)` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:349:23 | `A.BboxParams(format='pascal_voc', min_visibility=min_visibility, la...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:355:16 | `A.Compose([A.HorizontalFlip(p=p)], bbox_params=A.BboxParams(format=...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:356:8 | `A.HorizontalFlip(p=p)` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:357:23 | `A.BboxParams(format='pascal_voc', min_visibility=min_visibility, la...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:363:16 | `A.Compose([A.CenterCrop(rwidth, rheight)], bbox_params=A.BboxParams...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:364:8 | `A.CenterCrop(rwidth, rheight)` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:365:23 | `A.BboxParams(format='pascal_voc', min_visibility=min_visibility, la...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| preprocess.py:373:7 | `ReadImage(path='C:/PhD/Objective 1/MOD016_99.jpg')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:374:51 | `ReadBBox(path='C:/PhD/Objective 1/MOD016_99.xml')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:376:32 | `preprocess(image, bboxes, category_ids, resize=True, rheight=124, r...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| preprocess.py:388:0 | `cv2.imwrite('C:/PhD/Objective 1/test.jpg', image)` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:19:19 | `list(range(1, 181))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:19:24 | `range(1, 181)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:20:0 | `print(category_ids_all)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:43:0 | `print(category_id_to_name)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:50:8 | `cv2.imread(path)` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:51:8 | `cv2.cvtColor(image, cv2.COLOR_BGR2RGB)` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:69:33 | `int(x_min)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:69:45 | `int(x_max)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:69:57 | `int(y_min)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:69:69 | `int(y_max)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:72:4 | `cv2.rectangle(img, (x_min, y_min), (x_max, y_max), color=color, thi...` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:74:37 | `cv2.getTextSize(class_name, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:75:4 | `cv2.rectangle(img, (x_min, y_min - int(1.3 * text_height)), (x_min ...` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:75:39 | `int(1.3 * text_height)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:76:4 | `cv2.putText(img, text=class_name, org=(x_min, y_min - int(0.3 * tex...` | library / cv2 | library / cv2 | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:79:28 | `int(0.3 * text_height)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:89:29 | `zip(bboxes, category_ids)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| rescaling.py:91:14 | `visualize_bbox(img, bbox, class_name)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| rescaling.py:92:4 | `plt.figure(figsize=(12, 12))` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:93:4 | `plt.axis('off')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:94:4 | `plt.imshow(img)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:101:12 | `A.Compose([A.RandomRain(slant_lower=-10, slant_upper=10, drop_lengt...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:112:4 | `A.RandomRain(slant_lower=-10, slant_upper=10, drop_length=5, drop_w...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:113:19 | `A.BboxParams(format='pascal_voc', min_visibility=0.1, label_fields=...` | library / albumentations | library / albumentations | direct_import | static_obvious | v: direct import-backed API call |
| rescaling.py:118:0 | `visualize(transformed['image'], transformed['bboxes'], transformed[...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| annotation.py:26:7 | `os.path.abspath('E:/MAHE-CUSTOM_DATASET_FOR_CONSTRAINED_MODEL_TRAIN...` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:30:12 | `glob.glob(annotation_path + '*.xml')` | library / glob | library / glob | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:31:2 | `print(file)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:36:2 | `print(image_path)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:45:11 | `int(bbox.find('xmin').text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:46:11 | `int(bbox.find('ymin').text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:47:11 | `int(bbox.find('xmax').text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:48:11 | `int(bbox.find('ymax').text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:49:4 | `boxs.append([xmin, ymin, xmax, ymax])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:50:4 | `labels.append(unique_labels[label])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:51:4 | `difficulties.append(0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:57:15 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:58:16 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:59:14 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:60:15 | `list()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:65:2 | `train_images.append(key)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:66:2 | `train_objects.append(dict[key])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:68:2 | `test_images.append(key)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:69:2 | `test_objects.append(dict[key])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:76:5 | `open(os.path.join(output_folder, 'TRAIN_images.json'), 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:76:10 | `os.path.join(output_folder, 'TRAIN_images.json')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:77:4 | `json.dump(train_images, j)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:80:5 | `open(os.path.join(output_folder, 'TRAIN_objects.json'), 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:80:10 | `os.path.join(output_folder, 'TRAIN_objects.json')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:81:4 | `json.dump(train_objects, j)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:84:5 | `open(os.path.join(output_folder, 'label_map.json'), 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:84:10 | `os.path.join(output_folder, 'label_map.json')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:85:4 | `json.dump(unique_labels, j)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:88:5 | `open(os.path.join(output_folder, 'TEST_images.json'), 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:88:10 | `os.path.join(output_folder, 'TEST_images.json')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:89:4 | `json.dump(test_images, j)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:92:5 | `open(os.path.join(output_folder, 'TEST_objects.json'), 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| annotation.py:92:10 | `os.path.join(output_folder, 'TEST_objects.json')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| annotation.py:93:4 | `json.dump(test_objects, j)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
