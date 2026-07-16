# EJPLab — Suspicious Records (2)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| extract_model_embeddings.py:39:20 | `input_ids.to(device)` | library / torch | local / local | framework_tensor_receiver | manual_reasoned | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=torch pcresolve=local<br>expected library, pcresolve=local<br>verification_level=manual_reasoned |
| extract_model_embeddings.py:40:25 | `attention_mask.to(device)` | library / torch | local / local | framework_tensor_receiver | manual_reasoned | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=torch pcresolve=local<br>expected library, pcresolve=local<br>verification_level=manual_reasoned |
