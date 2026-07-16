# EJPLab — manual_reasoned (2 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| extract_model_embeddings.py:39:20 | `input_ids.to(device)` | library / torch | local / local | framework_tensor_receiver | manual_reasoned | gt: datasets set_format("torch") and DataLoader produce torch.Tensor batch values<br>v: set_format("torch") + DataLoader imply torch.Tensor; call unreachable in source |
| extract_model_embeddings.py:40:25 | `attention_mask.to(device)` | library / torch | local / local | framework_tensor_receiver | manual_reasoned | gt: datasets set_format("torch") and DataLoader produce torch.Tensor batch values<br>v: set_format("torch") + DataLoader imply torch.Tensor; call unreachable in source |
