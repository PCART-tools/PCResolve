# EJPLab — static_obvious (40 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| extract_model_embeddings.py:21:0 | `sns.set_palette('colorblind')` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:22:0 | `plt.rc('legend', fontsize=13)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:24:0 | `sns.set_style('darkgrid')` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:25:0 | `plt.rc('axes', titlesize=18)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:26:0 | `plt.rc('axes', labelsize=14)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:27:0 | `plt.rc('xtick', labelsize=13)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:28:0 | `plt.rc('ytick', labelsize=13)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:29:0 | `plt.rc('legend', fontsize=13)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:30:0 | `plt.rc('font', size=13)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:33:34 | `plt.cycler(color=sns.color_palette())` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:33:51 | `sns.color_palette()` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:41:17 | `model(input_ids, attention_mask=attention_mask, output_hidden_state...` | library / sys | library / sys | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:43:24 | `torch.stack(output.hidden_states)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:43:24 | `torch.stack(output.hidden_states).transpose(0, 1)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:44:24 | `torch.max(hidden_states, dim=1)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:45:24 | `torch.mean(hidden_states, dim=1)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:48:14 | `datasets.Dataset.from_pandas(df)` | library / datasets | library / datasets | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:51:17 | `DataLoader(tokenized_dataset, batch_size=batch_size, shuffle=False)` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:53:4 | `model.eval()` | library / sys | library / sys | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:56:9 | `torch.no_grad()` | library / torch | library / torch | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:57:26 | `enumerate(dataloader)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| extract_model_embeddings.py:58:28 | `process_batch(batch)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| extract_model_embeddings.py:61:24 | `np.concatenate(all_hidden_states, axis=0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:69:14 | `pd.read_csv('TestingDataset.csv')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:70:15 | `pd.read_csv('TrainingDataset.csv')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:71:13 | `pl.read_csv('PeptideManifold.csv')` | library / polars | library / polars | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:75:22 | `' '.join(list(i))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| extract_model_embeddings.py:75:31 | `list(i)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| extract_model_embeddings.py:79:23 | `' '.join(list(i))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| extract_model_embeddings.py:79:32 | `list(i)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| extract_model_embeddings.py:83:21 | `' '.join(list(i))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| extract_model_embeddings.py:83:30 | `list(i)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| extract_model_embeddings.py:84:33 | `pl.lit(big_sequences)` | library / polars | library / polars | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:84:33 | `pl.lit(big_sequences).alias('Sequence')` | library / polars | library / polars | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:85:28 | `pl.col('Sequence')` | library / polars | library / polars | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:85:28 | `pl.col('Sequence').is_in(test_sequences)` | library / polars | library / polars | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:86:33 | `pl.lit([0 for i in range(63999999 - len(test_sequences))])` | library / polars | library / polars | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:86:33 | `pl.lit([0 for i in range(63999999 - len(test_sequences))]).alias('l...` | library / polars | library / polars | direct_import | static_obvious | v: direct import-backed API call |
| extract_model_embeddings.py:86:52 | `range(63999999 - len(test_sequences))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| extract_model_embeddings.py:86:69 | `len(test_sequences)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
