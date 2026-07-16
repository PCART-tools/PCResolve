# MAHE_OD_DATASET — static_context (139 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| utils.py:57:11 | `ET.parse(annotation_path)` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:58:11 | `tree.getroot()` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:63:18 | `root.iter('object')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:65:24 | `object.find('difficult')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:67:16 | `object.find('name').text.lower()` | python / python | library / xml | builtin_string_method | static_context | v: Element.text is a Python string |
| utils.py:67:16 | `object.find('name').text.lower().strip()` | python / python | library / xml | builtin_string_method | static_context | v: Element.text is a Python string |
| utils.py:67:16 | `object.find('name')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:71:15 | `object.find('bndbox')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:72:19 | `bbox.find('xmin')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:73:19 | `bbox.find('ymin')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:74:19 | `bbox.find('xmax')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:75:19 | `bbox.find('ymax')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| utils.py:166:11 | `tensor.dim()` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:167:19 | `tensor.dim()` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:169:21 | `tensor.index_select(dim=d, index=torch.arange(start=0, end=tensor.s...` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:170:73 | `tensor.size(d)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:197:33 | `true_labels[i].size(0)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:204:11 | `true_images.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:204:34 | `true_boxes.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:204:56 | `true_labels.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:209:32 | `det_labels[i].size(0)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:215:11 | `det_images.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:215:33 | `det_boxes.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:215:54 | `det_labels.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:215:76 | `det_scores.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:224:31 | `(1 - true_class_difficulties).sum()` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:224:31 | `(1 - true_class_difficulties).sum().item()` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:228:49 | `true_class_difficulties.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:235:29 | `det_class_boxes.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:248:33 | `det_class_boxes[d].unsqueeze(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:255:15 | `object_boxes.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:261:41 | `overlaps.squeeze(0)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:265:50 | `true_class_boxes.size(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:269:15 | `max_overlap.item()` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:295:15 | `recalls_above_t.any()` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:296:32 | `cumul_precision[recalls_above_t].max()` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:299:36 | `precisions.mean()` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:302:29 | `average_precisions.mean()` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:302:29 | `average_precisions.mean().item()` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:305:72 | `average_precisions.tolist()` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:380:29 | `set_1[:, :2].unsqueeze(1)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:380:56 | `set_2[:, :2].unsqueeze(0)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:381:29 | `set_1[:, 2:].unsqueeze(1)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:381:56 | `set_2[:, 2:].unsqueeze(0)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:404:12 | `areas_set_1.unsqueeze(1)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:404:39 | `areas_set_2.unsqueeze(0)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:424:17 | `image.size(1)` | library / torch | library / torchvision | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:425:17 | `image.size(2)` | library / torch | library / torchvision | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:433:67 | `filler.unsqueeze(1)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:433:67 | `filler.unsqueeze(1).unsqueeze(1)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:465:17 | `image.size(1)` | library / torch | library / torchvision | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:466:17 | `image.size(2)` | library / torch | library / torchvision | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:501:43 | `crop.unsqueeze(0)` | library / torch | library / torch | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:503:22 | `overlap.squeeze(0)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:506:15 | `overlap.max()` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:506:15 | `overlap.max().item()` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:520:19 | `centers_in_crop.any()` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:546:16 | `FT.hflip(image)` | library / torchvision | library / torchvision | torchvision_callable | static_context | v: callable is imported from torchvision.transforms.functional |
| utils.py:569:16 | `FT.resize(image, dims)` | library / torchvision | library / torchvision | torchvision_callable | static_context | v: callable is imported from torchvision.transforms.functional |
| utils.py:608:24 | `d(new_image, adjust_factor)` | library / torchvision | library / torchvision | torchvision_callable | static_context | v: callable is imported from torchvision.transforms.functional |
| utils.py:641:20 | `FT.to_tensor(new_image)` | library / torchvision | library / torchvision | torchvision_callable | static_context | v: callable is imported from torchvision.transforms.functional |
| utils.py:653:20 | `FT.to_pil_image(new_image)` | library / torchvision | library / torchvision | torchvision_callable | static_context | v: callable is imported from torchvision.transforms.functional |
| utils.py:663:16 | `FT.to_tensor(new_image)` | library / torchvision | library / torchvision | torchvision_callable | static_context | v: callable is imported from torchvision.transforms.functional |
| utils.py:666:16 | `FT.normalize(new_image, mean=mean, std=std)` | library / torchvision | library / torchvision | torchvision_callable | static_context | v: callable is imported from torchvision.transforms.functional |
| utils.py:692:17 | `targets.size(0)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:693:13 | `scores.topk(k, 1, True, True)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:694:14 | `ind.eq(targets.view(-1, 1).expand_as(ind))` | library / torch | unknown / unknown | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:694:21 | `targets.view(-1, 1)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:694:21 | `targets.view(-1, 1).expand_as(ind)` | library / torch | local / local | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:695:20 | `correct.view(-1)` | library / torch | unknown / unknown | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:695:20 | `correct.view(-1).float()` | library / torch | unknown / unknown | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:695:20 | `correct.view(-1).float().sum()` | library / torch | unknown / unknown | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:696:11 | `correct_total.item()` | library / torch | unknown / unknown | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| utils.py:727:8 | `self.reset()` | local / local | local / local | local_method | static_context | v: AverageMeter.reset is defined on the project-local class |
| utils.py:752:16 | `param.grad.data.clamp_(-grad_clip, grad_clip)` | library / torch | unknown / unknown | torch_tensor_receiver | static_context | v: receiver is a torch Tensor by the function contract and surrounding tensor opera |
| datavisualizer.py:32:48 | `img_meta_df['Size'].tolist()` | library / pandas | library / pandas | pandas_receiver | static_context | v: img_meta_df is created by pandas.read_csv |
| datavisualizer.py:36:0 | `img_meta_df.head()` | library / pandas | library / pandas | pandas_receiver | static_context | v: img_meta_df is created by pandas.read_csv |
| datavisualizer.py:41:5 | `fig.add_subplot(111)` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: figure and axes receivers are created by matplotlib |
| datavisualizer.py:42:9 | `ax.scatter(img_meta_df.Width, img_meta_df.Height, color='blue', alp...` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: figure and axes receivers are created by matplotlib |
| datavisualizer.py:43:0 | `ax.set_title('Image Resolution')` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: figure and axes receivers are created by matplotlib |
| datavisualizer.py:44:0 | `ax.set_xlabel('Width', size=14)` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: figure and axes receivers are created by matplotlib |
| datavisualizer.py:45:0 | `ax.set_ylabel('Height', size=14)` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: figure and axes receivers are created by matplotlib |
| generatevocdata.py:33:13 | `label_string.split(',')` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:34:15 | `elem.replace(' ', '')` | python / python | local / local | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:38:11 | `filename.endswith('.jpg')` | python / python | library / os | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:39:18 | `filename.rstrip('.jpg')` | python / python | library / os | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:40:12 | `imgnames.append(img)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:52:19 | `ET.parse(annote)` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| generatevocdata.py:53:19 | `tree.getroot()` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| generatevocdata.py:55:29 | `root.findall('*/name')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| generatevocdata.py:57:16 | `annote_labels.append(labelname)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:59:20 | `annotations[labelname].append(img)` | python / python | local / local | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:66:14 | `imgnames.copy()` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:73:15 | `sampler.pop()` | python / python | local / local | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:76:12 | `test_list.append(elem)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:78:12 | `val_list.append(elem)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| generatevocdata.py:80:12 | `train_list.append(elem)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python string, list, or dict value |
| xmlfilerename.py:10:7 | `ET.parse(path)` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| xmlfilerename.py:11:7 | `tree.getroot()` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| xmlfilerename.py:12:5 | `root.find('filename')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| xmlfilerename.py:15:4 | `string.replace('jpg', 'JPEG')` | python / python | library / xml | builtin_string_method | static_context | v: Element.text is assigned to string and is a Python string |
| xmlfilerename.py:20:0 | `tree.write(path)` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| read pascalvoc annotation.py:12:7 | `ET.parse(path)` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| read pascalvoc annotation.py:13:7 | `tree.getroot()` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| read pascalvoc annotation.py:15:13 | `root.find('size')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| read pascalvoc annotation.py:16:12 | `root.find('size')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| read pascalvoc annotation.py:21:14 | `root.findall('object')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| preprocess.py:99:11 | `ET.parse(path)` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| preprocess.py:100:11 | `tree.getroot()` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| preprocess.py:102:17 | `root.find('size')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| preprocess.py:103:16 | `root.find('size')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| preprocess.py:104:19 | `root.find('size')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| preprocess.py:108:18 | `root.findall('object')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| preprocess.py:146:10 | `image.copy()` | library / numpy | local / local | numpy_array_receiver | static_context | v: image is returned by cv2.imread as a numpy.ndarray |
| preprocess.py:150:4 | `plt.figure(figsize=(12, 12))` | library / matplotlib | library / matplotlib | direct_import | static_context | v: plt is the matplotlib.pyplot import alias |
| preprocess.py:151:4 | `plt.axis('off')` | library / matplotlib | library / matplotlib | direct_import | static_context | v: plt is the matplotlib.pyplot import alias |
| preprocess.py:152:4 | `plt.imshow(img)` | library / matplotlib | library / matplotlib | direct_import | static_context | v: plt is the matplotlib.pyplot import alias |
| preprocess.py:222:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` | library / albumentations | library / albumentations | albumentations_callable | static_context | v: transform is created by albumentations.Compose |
| preprocess.py:291:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` | library / albumentations | library / albumentations | albumentations_callable | static_context | v: transform is created by albumentations.Compose |
| preprocess.py:335:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` | library / albumentations | library / albumentations | albumentations_callable | static_context | v: transform is created by albumentations.Compose |
| preprocess.py:343:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` | library / albumentations | library / albumentations | albumentations_callable | static_context | v: transform is created by albumentations.Compose |
| preprocess.py:351:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` | library / albumentations | library / albumentations | albumentations_callable | static_context | v: transform is created by albumentations.Compose |
| preprocess.py:359:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` | library / albumentations | library / albumentations | albumentations_callable | static_context | v: transform is created by albumentations.Compose |
| preprocess.py:367:18 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` | library / albumentations | library / albumentations | albumentations_callable | static_context | v: transform is created by albumentations.Compose |
| rescaling.py:88:10 | `image.copy()` | library / numpy | local / local | numpy_array_receiver | static_context | v: image is returned by cv2.imread as a numpy.ndarray |
| rescaling.py:115:14 | `transform(image=image, bboxes=bboxes, category_ids=category_ids)` | library / albumentations | library / albumentations | albumentations_callable | static_context | v: transform is created by albumentations.Compose |
| annotation.py:32:9 | `file.split('/')` | python / python | library / glob | builtin_string_method | static_context | v: receiver is a project string value |
| annotation.py:37:9 | `ET.parse(file)` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| annotation.py:38:9 | `tree.getroot()` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| annotation.py:42:16 | `root.iter('object')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| annotation.py:43:12 | `object.find('name').text.lower()` | python / python | library / xml | builtin_string_method | static_context | v: Element.text is a Python string |
| annotation.py:43:12 | `object.find('name').text.lower().strip()` | python / python | library / xml | builtin_string_method | static_context | v: Element.text is a Python string |
| annotation.py:43:12 | `object.find('name')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| annotation.py:44:11 | `object.find('bndbox')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| annotation.py:45:15 | `bbox.find('xmin')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| annotation.py:46:15 | `bbox.find('ymin')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| annotation.py:47:15 | `bbox.find('xmax')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| annotation.py:48:15 | `bbox.find('ymax')` | library / xml | library / xml | xml_element_receiver | static_context | v: receiver is produced by xml.etree.ElementTree |
| annotation.py:63:8 | `key.split('/')` | python / python | local / local | builtin_string_method | static_context | v: receiver is a project string value |
