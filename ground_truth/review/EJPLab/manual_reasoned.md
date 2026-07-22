# EJPLab — manual_reasoned (2 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| extract_model_embeddings.py:39:20 | `input_ids.to(device)` | unknown / unknown | unknown / unknown | unconstrained_dead_code_parameter | manual_reasoned | gt: call is unreachable and input_ids has no concrete call-site value in the source <br>v: surrounding framework context suggests Tensor, but unreachable parameter has no  |
| extract_model_embeddings.py:40:25 | `attention_mask.to(device)` | unknown / unknown | unknown / unknown | unconstrained_dead_code_parameter | manual_reasoned | gt: call is unreachable and attention_mask has no concrete call-site value in the so<br>v: surrounding framework context suggests Tensor, but unreachable parameter has no  |
