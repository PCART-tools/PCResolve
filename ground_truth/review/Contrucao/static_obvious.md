# Contrucao — static_obvious (42 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| main.py:9:16 | `soup(['style', 'script', 'head', 'header', 'meta', '[document]', 't...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| main.py:13:11 | `' '.join(soup.stripped_strings)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:23:9 | `spacy.load('en_core_web_sm')` | library / spacy | library / spacy | direct_import | static_obvious | v: direct import-backed API call |
| main.py:38:9 | `requests.get(url)` | library / requests | library / requests | direct_import | static_obvious | v: direct import-backed API call |
| main.py:39:9 | `BeautifulSoup(html, 'html.parser')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| main.py:40:10 | `removerTags(soup)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| main.py:45:4 | `texto.append(sentence.text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:48:14 | `set()` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:51:21 | `filtrar(palavra.strip())` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| main.py:53:8 | `vocabulario.add(palavraFinal)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:54:14 | `sorted(vocabulario)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:61:0 | `bagOfWords.append(vocabulario)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:62:0 | `tfidf.append(vocabulario)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:71:20 | `len(sentence)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:72:16 | `len(vocabulario)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:74:19 | `filtrar(palavra.strip())` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| main.py:76:12 | `vocabulario.index(palavraFinal)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:77:2 | `bagOfWords.append(vetor)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:87:9 | `range(len(bagOfWords[0]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:87:15 | `len(bagOfWords[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:90:11 | `range(1, len(bagOfWords))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:90:20 | `len(bagOfWords)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:96:9 | `range(1, len(bagOfWords))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:96:18 | `len(bagOfWords)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:99:11 | `range(len(bagOfWords[i]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:99:17 | `len(bagOfWords[i])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:102:22 | `len(bagOfWords)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:104:42 | `np.log(qtdDocumentos / qtdDocumentosQueTemAPalavra)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main.py:106:4 | `vetor.append(digito)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:107:2 | `tfidf.append(vetor)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:110:0 | `np.seterr(all='raise')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main.py:114:9 | `range(1, len(tfidf))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:114:18 | `len(tfidf)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:116:11 | `range(1, len(tfidf))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:116:20 | `len(tfidf)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:118:16 | `np.dot(tfidf[x], tfidf[i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main.py:118:44 | `np.linalg.norm(tfidf[x])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main.py:118:69 | `np.linalg.norm(tfidf[i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main.py:121:4 | `vetor.append(cos_sim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:122:2 | `matrizCosseno.append(vetor)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| main.py:124:17 | `pd.DataFrame(tfidf)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| main.py:128:25 | `pd.DataFrame(matrizCosseno)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
