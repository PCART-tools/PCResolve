# allnews — Needs Annotation (553 records)

These records do not yet have `verification_level` or
`expected_*` fields confirmed by a human annotator.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| train_fastext.py:19:24 | `allnews_am.processing.ConllReader(root=os.path.join(file_dir, 'alln...` |  /  | local / local | - | - |  |
| train_fastext.py:19:24 | `allnews_am.processing.ConllReader(root=os.path.join(file_dir, 'alln...` |  /  | local / local | - | - |  |
| train_fastext.py:46:4 | `my_model.save(os.path.join(file_dir, 'models/', args.model_name))` |  /  | library / gensim | - | - |  |
| train_fastext.py:50:4 | `my_model.wv.evaluate_word_analogies(analogy_file)` |  /  | library / gensim | - | - |  |
| train_fastext.py:54:16 | `allnews_am.parse_w2v_ft_args(file_dir)` |  /  | local / local | - | - |  |
| allnews_am/processing.py:39:8 | `self._require(self.WORDS, self.POS, self.CHUNK)` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:42:19 | `self._get_iob_words(grid, tagset, column)` |  /  | local / local | - | - |  |
| allnews_am/processing.py:44:15 | `LazyConcatenation(LazyMap(get_iob_words, self._grids(fileids)))` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:44:33 | `LazyMap(get_iob_words, self._grids(fileids))` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:44:56 | `self._grids(fileids)` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:59:8 | `self._require(self.WORDS, self.POS, self.CHUNK)` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:62:19 | `self._get_iob_words(grid, tagset, column)` |  /  | local / local | - | - |  |
| allnews_am/processing.py:64:15 | `LazyMap(get_iob_words, self._grids(fileids))` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:64:38 | `self._grids(fileids)` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:67:19 | `self._get_column(grid, self._colmap['pos'])` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:69:24 | `map_tag(self._tagset, tagset, t)` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:70:24 | `self._get_column(grid, self._colmap['words'])` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:71:24 | `self._get_column(grid, self._colmap[column])` |  /  | library / nltk | - | - |  |
| allnews_am/processing.py:84:8 | `s.strip()` |  /  | local / local | - | - |  |
| allnews_am/processing.py:89:8 | `tokenizer.Tokenizer(s)` |  /  | local / local | - | - |  |
| allnews_am/processing.py:90:4 | `t.segmentation()` |  /  | local / local | - | - |  |
| allnews_am/processing.py:90:4 | `t.segmentation().tokenization()` |  /  | local / local | - | - |  |
| allnews_am/db.py:76:13 | `self.connection.cursor()` |  /  | local / local | - | - |  |
| allnews_am/db.py:79:12 | `cursor.execute(sql, (offset, limit))` |  /  | local / local | - | - |  |
| allnews_am/db.py:82:33 | `cursor.fetchall()` |  /  | local / local | - | - |  |
| allnews_am/__init__.py:8:4 | `parser.add_argument('--corpus', default=os.path.join(file_dir, '../...` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:12:4 | `parser.add_argument('--model_name', default='embeddings.model', hel...` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:15:4 | `parser.add_argument('--size', default=100, help='Size of the embedd...` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:16:4 | `parser.add_argument('--window', default=5, help='Context window siz...` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:17:4 | `parser.add_argument('--min_count', default=5, help='Minimum number ...` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:20:4 | `parser.add_argument('-sg', action='store_true', help='If set, will ...` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:23:4 | `parser.add_argument('--workers', default=4, help='Number of workers.')` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:25:4 | `parser.add_argument('--alpha', default=0.025, help='Learning rate.')` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:27:4 | `parser.add_argument('--negative', default=10, help='Number of negat...` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:29:4 | `parser.add_argument('--epochs', default=30, help='Number of epochs.')` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:31:4 | `parser.add_argument('--subsample', default=1e-05, help='Sub-samplin...` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:33:4 | `parser.add_argument('-add_ner_sents', action='store_true', help='If...` |  /  | library / argparse | - | - |  |
| allnews_am/__init__.py:36:11 | `parser.parse_args()` |  /  | library / argparse | - | - |  |
| allnews_am/NER_models/ner.py:31:12 | `corpus.append(sentence)` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:32:12 | `labels.append(label)` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:38:8 | `sentence.append(line.split()[0])` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:39:8 | `label.append(line.split()[3])` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:48:12 | `temp.append((corpus[i][j], labels[i][j]))` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:49:8 | `sentences_entities.append(temp)` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:57:4 | `words.extend(sent)` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:62:4 | `tags.extend(tag)` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:71:31 | `word2idx.items()` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:76:30 | `tag2idx.items()` |  /  | local / local | - | - |  |
| allnews_am/NER_models/ner.py:85:10 | `Input(shape=(MAX_LEN,))` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:86:10 | `Embedding(input_dim=n_words + 2, output_dim=EMBEDDING, input_length...` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:86:10 | `Embedding(input_dim=n_words + 2, output_dim=EMBEDDING, input_length...` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:88:10 | `Bidirectional(LSTM(units=25, return_sequences=True, recurrent_dropo...` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:88:10 | `Bidirectional(LSTM(units=25, return_sequences=True, recurrent_dropo...` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:88:24 | `LSTM(units=25, return_sequences=True, recurrent_dropout=0.3)` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:90:10 | `TimeDistributed(Dense(50, activation='relu'))(model)` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:90:10 | `TimeDistributed(Dense(50, activation='relu'))` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:90:26 | `Dense(50, activation='relu')` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:92:8 | `TimeDistributed(Dense(n_tags + 1, activation='softmax'))(model)` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:92:8 | `TimeDistributed(Dense(n_tags + 1, activation='softmax'))` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:92:24 | `Dense(n_tags + 1, activation='softmax')` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:94:10 | `Model(input, out)` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:95:2 | `model.compile(optimizer='adam', loss='categorical_crossentropy', me...` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:97:2 | `model.summary()` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:103:5 | `pad_sequences(maxlen=MAX_LEN, sequences=X, padding='post', value=wo...` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:106:6 | `pad_sequences(maxlen=MAX_LEN, sequences=y, padding='post', value=ta...` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:107:7 | `to_categorical(i, num_classes=n_tags + 1)` |  /  | library / keras | - | - |  |
| allnews_am/NER_models/ner.py:112:12 | `model.fit(X_tr, np.array(y_tr), batch_size=BATCH_SIZE, epochs=EPOCH...` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:87:12 | `self.__dict__.update(kwargs)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:109:10 | `SimpleNamespace(knownNamespaces={'Template': 10}, templateNamespace...` |  /  | library / types | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:229:15 | `filter_disambig_page_pattern.match(line)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:289:12 | `title.strip(' _')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:295:17 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:296:11 | `m.group(2)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:300:15 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:333:15 | `m.group(0)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:334:15 | `m.group(1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:361:4 | `options.ignored_tag_patterns.append((left, right))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:413:12 | `tpl.append(TemplateText(body[start:s]))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:414:12 | `tpl.append(TemplateArg(body[s + 3:e - 3]))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:416:8 | `tpl.append(TemplateText(body[start:]))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:441:24 | `tpl.subst(params, extractor, depth)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:474:20 | `Template.parse(parts[0])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:477:27 | `Template.parse(parts[1])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:496:20 | `self.name.subst(params, extractor, depth + 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:497:20 | `extractor.transform(paramName)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:502:27 | `self.default.subst(params, extractor, depth + 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:503:18 | `extractor.transform(defaultValue)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:578:26 | `out_str.encode('utf-8')` |  /  | library / json | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:579:12 | `out.write(out_str)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:580:12 | `out.write('\n')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:588:25 | `header.encode('utf-8')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:589:12 | `out.write(header)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:592:27 | `line.encode('utf-8')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:593:16 | `out.write(line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:594:16 | `out.write('\n')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:595:12 | `out.write(footer)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:609:16 | `self.title.find(':')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:617:45 | `options.knownNamespaces.get(ns, '0')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:620:16 | `pagename.rfind('/')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:627:16 | `pagename.find('/')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:646:15 | `self.transform(text)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:647:15 | `self.wiki2text(text)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:648:23 | `self.clean(text)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:655:8 | `self.write_output(out, text)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:674:17 | `nowiki.finditer(wikitext, cur)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:675:19 | `self.transform1(wikitext[cur:m.start()])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:675:48 | `m.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:675:71 | `m.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:675:81 | `m.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:676:18 | `m.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:678:15 | `self.transform1(wikitext[cur:])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:687:19 | `self.expand(text)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:716:19 | `bold_italic.sub('<b>\\1</b>', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:717:19 | `bold.sub('<b>\\1</b>', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:718:19 | `italic.sub('<i>\\1</i>', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:720:19 | `bold_italic.sub('\\1', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:721:19 | `bold.sub('\\1', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:722:19 | `italic_quote.sub('"\\1"', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:723:19 | `italic.sub('"\\1"', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:724:19 | `quote_quote.sub('"\\1"', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:726:15 | `text.replace("'''", '')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:726:15 | `text.replace("'''", '').replace("''", '"')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:735:15 | `magicWordsRE.sub('', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:742:17 | `syntaxhighlight.finditer(text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:743:37 | `m.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:743:51 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:744:18 | `m.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:757:17 | `comment.finditer(text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:758:12 | `spans.append((m.start(), m.end()))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:758:26 | `m.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:758:37 | `m.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:762:21 | `pattern.finditer(text)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:763:16 | `spans.append((m.start(), m.end()))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:763:30 | `m.start()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:763:41 | `m.end()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:767:21 | `left.finditer(text)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:768:16 | `spans.append((m.start(), m.end()))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:768:30 | `m.start()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:768:41 | `m.end()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:769:21 | `right.finditer(text)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:770:16 | `spans.append((m.start(), m.end()))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:770:30 | `m.start()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:770:41 | `m.end()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:786:25 | `pattern.finditer(text)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:787:23 | `text.replace(match.group(), '%s_%d' % (placeholder, index))` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:787:36 | `match.group()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:790:15 | `text.replace('<<', '«')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:790:15 | `text.replace('<<', '«').replace('>>', '»')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:795:15 | `text.replace('\t', ' ')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:796:15 | `spaces.sub(' ', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:797:15 | `dots.sub('...', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:801:15 | `text.replace(',,', ',')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:801:15 | `text.replace(',,', ',').replace(',.', '.')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:808:19 | `text.replace('\|-', '')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:809:19 | `text.replace('\|', '')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:858:37 | `self.expandTemplate(wikitext[s + 2:e - 2])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:918:32 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:918:32 | `m.group(1).strip()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:919:33 | `m.group(2)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:922:37 | `parameterValue.strip()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:929:28 | `param.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:988:16 | `parts[0].strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:989:16 | `self.expand(title)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1019:16 | `title.find(':')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1022:23 | `title[colon + 1:].strip()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1033:21 | `options.redirects.get(title)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1041:23 | `Template.parse(options.templates[title])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1089:22 | `self.transform(p)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1092:17 | `self.templateParams(params)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1098:21 | `self.frame.push(title, params)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1099:23 | `template.subst(params, self)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1100:16 | `self.transform(instantiated)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1101:21 | `self.frame.pop()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1152:14 | `paramsList[cur:s].split(sep)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1159:20 | `parameters.extend(par[1:])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1168:10 | `paramsList[cur:].split(sep)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1175:16 | `parameters.extend(par[1:])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1231:13 | `reOpen.search(text, cur)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1234:17 | `m1.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1234:28 | `m1.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1235:11 | `m1.group()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1239:14 | `m1.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1241:17 | `reNext.search(text, end)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1244:18 | `m2.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1245:19 | `m2.group()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1246:21 | `m2.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1246:32 | `m2.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1249:16 | `stack.append(lmatch)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1252:32 | `stack.pop()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1261:24 | `stack.append(openCount - lmatch)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1264:26 | `m1.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1273:16 | `stack.append(-lmatch)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1276:33 | `stack.pop()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1283:24 | `stack.append(lmatch - openCount)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1286:26 | `m1.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1312:15 | `nextPat.search(text, cur)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1316:20 | `next.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1318:16 | `next.group(0)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1320:12 | `stack.append(delim)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1323:22 | `stack.pop()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1328:29 | `next.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1330:24 | `next.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1332:14 | `next.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1397:16 | `args.get(var)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1399:20 | `args.get(str(index))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1410:8 | `params.get('s', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1411:12 | `params.get('i', 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1412:12 | `params.get('j', -1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1421:8 | `params.get('s', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1422:12 | `params.get('i', 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1423:14 | `params.get('len', 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1429:8 | `params.get('s', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1435:13 | `params.get('source', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1436:14 | `params.get('target', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1437:20 | `params.get('start', 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1438:20 | `params.get('plain', 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1442:15 | `source.find(pattern, start)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1449:13 | `params.get('target', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1450:14 | `params.get('pos', 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1458:13 | `params.get('source', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1459:14 | `params.get('pattern', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1460:14 | `params.get('replace', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1461:16 | `params.get('count', 0)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1462:16 | `params.get('plain', 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1465:19 | `source.replace(pattern, replace, count)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1467:19 | `source.replace(pattern, replace)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1474:13 | `params.get('source', '')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1475:16 | `params.get('count', '1')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1487:20 | `args.get('1')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1491:15 | `args.get('2', 'N/A')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1635:15 | `self.values.get(name)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1674:15 | `string[0].upper()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1683:19 | `string[0].lower()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1685:19 | `string.lower()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1695:7 | `templateTitle.startswith(':')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1703:40 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1705:40 | `m.group(2)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1743:55 | `self.function(other, x)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1746:15 | `self.function(other)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1749:55 | `self.function(other, x)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1752:15 | `self.function(other)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1755:15 | `self.function(value1, value2)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1767:15 | `extr.expand(expr)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1780:7 | `testValue.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1783:22 | `extr.expand(valueIfTrue.strip())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1783:34 | `valueIfTrue.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1787:15 | `extr.expand(valueIfFalse.strip())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1787:27 | `valueIfFalse.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1792:13 | `rvalue.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1795:11 | `lvalue.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1802:23 | `extr.expand(valueIfTrue.strip())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1802:35 | `valueIfTrue.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1805:23 | `extr.expand(valueIfFalse.strip())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1805:35 | `valueIfFalse.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1811:15 | `extr.expand(then.strip())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1811:27 | `then.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1813:15 | `test.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1815:15 | `extr.expand(Else.strip())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1815:27 | `Else.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1829:14 | `primary.strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1837:15 | `param.split('=', 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1838:17 | `extr.expand(pair[0].strip())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1838:29 | `pair[0].strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1842:21 | `extr.expand(pair[1].strip())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1842:33 | `pair[1].strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1844:36 | `v.strip()` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1844:55 | `lvalue.split('\|')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1884:49 | `extr.expand(ifnex)` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1900:45 | `quote(string.encode('utf-8'))` |  /  | library / urllib | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1900:51 | `string.encode('utf-8')` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1902:38 | `string.lower()` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1906:38 | `string.upper()` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1927:23 | `functionName.lower()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1929:26 | `args[0].strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1929:43 | `args[1].strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1946:26 | `extractor.transform(p)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1947:25 | `extractor.templateParams(params)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:1990:35 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2005:11 | `comment.sub('', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2008:11 | `reNoinclude.sub('', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2015:34 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2019:15 | `reIncludeonly.sub('', text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2038:12 | `openRE.search(text, 0)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2041:10 | `closeRE.search(text, start.end())` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2041:31 | `start.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2044:15 | `openRE.search(text, next.end())` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2044:35 | `next.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2048:23 | `closeRE.search(text, end.end())` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2048:44 | `end.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2053:12 | `spans.append((start.start(), end.end()))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2053:26 | `start.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2053:41 | `end.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2055:14 | `end.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2055:26 | `next.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2060:23 | `end.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2061:22 | `closeRE.search(text, end.end())` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2061:43 | `end.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2066:32 | `start.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2070:16 | `spans.append((start.start(), end.end()))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2070:30 | `start.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2070:45 | `end.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2073:22 | `closeRE.search(text, next.end())` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2073:43 | `next.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2086:4 | `spans.sort()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2119:12 | `tailRE.match(text, e)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2121:20 | `m.group(0)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2122:18 | `m.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2128:15 | `inner.find('\|')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2133:20 | `inner[:pipe].rstrip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2137:23 | `inner.rfind('\|', curp, s1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2141:20 | `inner[pipe + 1:].strip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2413:12 | `title.find(':')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2418:17 | `title.find(':', colon + 1)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2422:40 | `quote(title.encode('utf-8'))` |  /  | library / urllib | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2422:46 | `title.encode('utf-8')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2467:13 | `ExtLinkBracketedRegex.finditer(text)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2468:22 | `m.start()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2469:14 | `m.end()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2471:14 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2472:16 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2484:12 | `EXT_IMAGE_REGEX.match(label)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2500:40 | `quote(url.encode('utf-8'))` |  /  | library / urllib | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2500:46 | `url.encode('utf-8')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2538:16 | `text.split('\n')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2542:16 | `page.append(line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2545:24 | `page.append(listClose[c])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2550:16 | `page.append('')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2553:12 | `section.match(line)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2555:20 | `m.group(2)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2556:22 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2558:16 | `page.append('<h%d>%s</h%d>' % (lev, title, lev))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2563:26 | `headers.keys()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2571:13 | `line.startswith('++')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2576:16 | `page.append(title)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2586:24 | `zip_longest(listLevel, line, fillvalue='')` |  /  | library / itertools | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2590:28 | `page.append(listClose[c])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2601:28 | `page.append(listClose[c])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2605:20 | `listCount.append(0)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2607:24 | `page.append(listOpen[n])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2610:19 | `line[i:].strip()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2615:39 | `headers.items()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2617:28 | `page.append('Section::::' + v)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2618:20 | `headers.clear()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2622:20 | `page.append('{0:{1}s}'.format(bullet, len(listLevel)) + line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2626:20 | `page.append(listItem[n] % line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2630:20 | `page.append(listClose[c])` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2633:12 | `page.append(line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2639:53 | `line.strip('.-')` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2643:31 | `headers.items()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2645:20 | `page.append('Section::::' + v)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2646:12 | `headers.clear()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2647:12 | `page.append(line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2652:16 | `page.append(line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2682:18 | `self._dirname()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2685:15 | `self._filepath()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2695:33 | `self._dirname()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2713:20 | `self.open(next(self.nextFile))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2713:30 | `next(self.nextFile)` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2716:11 | `self.file.tell()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2717:12 | `self.close()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2718:24 | `self.open(next(self.nextFile))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2718:34 | `next(self.nextFile)` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2721:8 | `self.reserve(len(data))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2722:8 | `self.file.write(data)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2725:8 | `self.file.close()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2771:16 | `output.write('<page>\n')` |  /  | library / codecs | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2772:16 | `output.write('   <title>%s</title>\n' % title)` |  /  | library / codecs | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2773:16 | `output.write('   <ns>%s</ns>\n' % ns)` |  /  | library / codecs | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2774:16 | `output.write('   <id>%s</id>\n' % id)` |  /  | library / codecs | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2775:16 | `output.write('   <text>')` |  /  | library / codecs | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2777:20 | `output.write(line)` |  /  | library / codecs | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2778:16 | `output.write('   </text>\n')` |  /  | library / codecs | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2779:16 | `output.write('</page>\n')` |  /  | library / codecs | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2783:8 | `output.close()` |  /  | library / codecs | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2803:51 | `line.decode('utf-8')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2806:16 | `page.append(line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2808:19 | `line.lstrip()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2808:19 | `line.lstrip().startswith('[[Category:')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2809:27 | `catRE.search(line)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2811:24 | `catSet.add(mCat.group(1))` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2811:35 | `mCat.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2813:12 | `tagRE.search(line)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2816:14 | `m.group(2)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2822:17 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2824:20 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2826:20 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2828:17 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2832:41 | `m.start(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2836:24 | `m.start(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2836:35 | `m.end(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2837:12 | `page.append(line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2841:15 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2842:16 | `page.append(m.group(1))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2842:28 | `m.group(1)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2845:12 | `page.append(line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2877:51 | `line.decode('utf-8')` |  /  | library / fileinput | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2878:12 | `tagRE.search(line)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2881:14 | `m.group(2)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2885:19 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2886:36 | `base.rfind('/')` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2888:17 | `keyRE.search(line)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2890:31 | `mk.groups()` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2893:36 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2895:44 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2898:42 | `m.group(3)` |  /  | library / re | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2913:16 | `file.close()` |  /  | library / fileinput | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2920:16 | `input.close()` |  /  | library / fileinput | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2951:4 | `reduce.start()` |  /  | library / multiprocessing | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2963:8 | `extractor.start()` |  /  | library / multiprocessing | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2964:8 | `workers.append(extractor)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2981:12 | `jobs_queue.put(job)` |  /  | library / multiprocessing | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2985:4 | `input.close()` |  /  | library / fileinput | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2989:8 | `jobs_queue.put(None)` |  /  | library / multiprocessing | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2992:8 | `w.join()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2995:4 | `output_queue.put(None)` |  /  | library / multiprocessing | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:2997:4 | `reduce.join()` |  /  | library / multiprocessing | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3026:14 | `jobs_queue.get()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3032:16 | `e.extract(out)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3033:23 | `out.getvalue()` |  /  | library / io | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3038:12 | `output_queue.put((page_num, text))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3039:12 | `out.truncate(0)` |  /  | library / io | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3040:12 | `out.seek(0)` |  /  | library / io | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3044:4 | `out.close()` |  /  | library / io | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3078:12 | `output.write(spool.pop(next_page).encode('utf-8'))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3078:25 | `spool.pop(next_page)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3078:25 | `spool.pop(next_page).encode('utf-8')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3090:19 | `output_queue.get()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3103:8 | `output.close()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3116:4 | `parser.add_argument('input', help='XML wiki dump file')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3118:13 | `parser.add_argument_group('Output')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3119:4 | `groupO.add_argument('-o', '--output', default='text', help="directo...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3121:4 | `groupO.add_argument('-b', '--bytes', default='1M', help='maximum by...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3124:4 | `groupO.add_argument('-c', '--compress', action='store_true', help='...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3126:4 | `groupO.add_argument('--json', action='store_true', help='write outp...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3130:13 | `parser.add_argument_group('Processing')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3131:4 | `groupP.add_argument('--html', action='store_true', help='produce HT...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3133:4 | `groupP.add_argument('-l', '--links', action='store_true', help='pre...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3135:4 | `groupP.add_argument('-s', '--sections', action='store_true', help='...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3137:4 | `groupP.add_argument('--lists', action='store_true', help='preserve ...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3139:4 | `groupP.add_argument('-ns', '--namespaces', default='', metavar='ns1...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3141:4 | `groupP.add_argument('--templates', help='use or create file contain...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3143:4 | `groupP.add_argument('--no_templates', action='store_false', help='D...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3145:4 | `groupP.add_argument('-r', '--revision', action='store_true', defaul...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3147:4 | `groupP.add_argument('--min_text_length', type=int, default=options....` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3149:4 | `groupP.add_argument('--filter_disambig_pages', action='store_true',...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3151:4 | `groupP.add_argument('-it', '--ignored_tags', default='', metavar='a...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3153:4 | `groupP.add_argument('-de', '--discard_elements', default='', metava...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3155:4 | `groupP.add_argument('--keep_tables', action='store_true', default=o...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3158:4 | `parser.add_argument('--processes', type=int, default=default_proces...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3161:13 | `parser.add_argument_group('Special')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3162:4 | `groupS.add_argument('-q', '--quiet', action='store_true', help='sup...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3164:4 | `groupS.add_argument('--debug', action='store_true', help='print deb...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3166:4 | `groupS.add_argument('-a', '--article', action='store_true', help='a...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3168:4 | `groupS.add_argument('--log_file', help='path to save the log info')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3170:4 | `groupS.add_argument('-v', '--version', action='version', version='%...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3173:4 | `groupP.add_argument('--filter_category', help="specify the file tha...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3176:11 | `parser.parse_args()` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3193:27 | `args.bytes[-1].lower()` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3202:41 | `args.namespaces.split(',')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3206:26 | `args.ignored_tags.split(',')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3220:38 | `args.discard_elements.split(',')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3248:12 | `Extractor(id, revid, title, page).extract(sys.stdout)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3249:8 | `file.close()` |  /  | library / fileinput | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3270:24 | `options.filter_category_exclude.add(line.lstrip('^'))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3272:24 | `options.filter_category_include.add(line)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3288:8 | `logger.setLevel(logging.INFO)` |  /  | library / logging | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3290:8 | `logger.setLevel(logging.DEBUG)` |  /  | library / logging | - | - |  |
| allnews_am/wikiextractor/WikiExtractor.py:3294:8 | `logger.addHandler(fileHandler)` |  /  | library / logging | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:68:18 | `self._dirname()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:71:15 | `self._filepath()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:79:33 | `self._dirname()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:96:20 | `self.open(self.nextFile.next())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:96:30 | `self.nextFile.next()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:99:11 | `self.file.tell()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:100:12 | `self.close()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:101:24 | `self.open(self.nextFile.next())` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:101:34 | `self.nextFile.next()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:104:8 | `self.reserve(len(data))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:105:8 | `self.file.write(data)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:108:8 | `self.file.close()` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:126:14 | `get_url(self.id)` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:130:17 | `header.encode('utf-8')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:132:8 | `out.write(header)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:133:15 | `clean(self, text)` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:134:20 | `compact(text)` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:135:12 | `out.write(line.encode('utf-8'))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:135:22 | `line.encode('utf-8')` |  /  | unknown / unknown | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:136:12 | `out.write('\n')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:137:8 | `out.write(footer)` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:165:15 | `input.readline()` |  /  | library / gzip | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:169:29 | `input.readline()` |  /  | library / gzip | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:183:12 | `output.write(page.encode('utf-8'))` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:183:25 | `page.encode('utf-8')` |  /  | local / local | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:194:4 | `parser.add_argument('input', help='Cirrus Json wiki dump file')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:196:13 | `parser.add_argument_group('Output')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:197:4 | `groupO.add_argument('-o', '--output', default='text', help="directo...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:199:4 | `groupO.add_argument('-b', '--bytes', default='1M', help='maximum by...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:202:4 | `groupO.add_argument('-c', '--compress', action='store_true', help='...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:205:13 | `parser.add_argument_group('Processing')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:206:4 | `groupP.add_argument('-ns', '--namespaces', default='', metavar='ns1...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:209:13 | `parser.add_argument_group('Special')` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:210:4 | `groupS.add_argument('-q', '--quiet', action='store_true', help='sup...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:212:4 | `groupS.add_argument('-v', '--version', action='version', version='%...` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:216:11 | `parser.parse_args()` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:219:27 | `args.bytes[-1].lower()` |  /  | library / argparse | - | - |  |
| allnews_am/wikiextractor/cirrus-extract.py:232:8 | `logger.setLevel(logging.INFO)` |  /  | library / logging | - | - |  |
| allnews_am/tokenizer/tokenizer.py:13:12 | `minidom.parse(fullpath)` |  /  | library / xml | - | - |  |
| allnews_am/tokenizer/tokenizer.py:24:15 | `self.xml.getElementsByTagName('unit')` |  /  | library / xml | - | - |  |
| allnews_am/tokenizer/tokenizer.py:26:18 | `unit.getElementsByTagName('p')` |  /  | library / xml | - | - |  |
| allnews_am/tokenizer/tokenizer.py:100:14 | `cls.PUNCTUATION.values()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:100:63 | `cls.LINEAR_PUNCTUATION.values()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:103:14 | `reg_arr.append(j)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:119:15 | `Punct(':').regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:120:16 | `Punct(4).regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:121:16 | `Punct(3).regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:122:15 | `Punct(':').regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:123:16 | `Punct(4).regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:124:16 | `Punct(3).regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:125:15 | `Punct(':').regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:127:15 | `Punct.all()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:127:39 | `Punct(1).regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:132:15 | `Punct.inter()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:133:8 | `Punct.metric(double=True)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:146:33 | `Punct.all(linear=True)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:151:17 | `Punct.all()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:152:17 | `Punct.all(linear=True)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:157:33 | `Punct(1).regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:157:113 | `Punct(2).regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:168:50 | `Punct.all(linear=True)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:169:42 | `Punct(['dot', 6, 16]).regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:169:115 | `Punct(['dot', 6, 16]).regex()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:176:40 | `Punct.all(linear=True)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:177:50 | `Punct.all(linear=True)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:187:11 | `self.print_()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:235:12 | `multitoken.append(split_part.group(0))` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:235:30 | `split_part.group(0)` |  /  | library / re | - | - |  |
| allnews_am/tokenizer/tokenizer.py:236:24 | `split_part.end()` |  /  | library / re | - | - |  |
| allnews_am/tokenizer/tokenizer.py:248:4 | `self.purification()` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:253:12 | `self.is_segment(self.text[checkpoint:], l - checkpoint)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:257:24 | `new_segment.rstrip()` |  /  | library / re | - | - |  |
| allnews_am/tokenizer/tokenizer.py:257:24 | `new_segment.rstrip().lstrip()` |  /  | library / re | - | - |  |
| allnews_am/tokenizer/tokenizer.py:258:8 | `self.segments.append({'segment': clean_segment, 'id': len(self.segm...` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:281:22 | `dict.get_word(s['segment'][l:])` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:285:10 | `s['tokens'].append((index, dict_word['word']))` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:290:18 | `self.find_token(s['segment'], l)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:292:17 | `token.end()` |  /  | library / re | - | - |  |
| allnews_am/tokenizer/tokenizer.py:293:24 | `token.group(0)` |  /  | library / re | - | - |  |
| allnews_am/tokenizer/tokenizer.py:294:26 | `new_token.rstrip()` |  /  | library / re | - | - |  |
| allnews_am/tokenizer/tokenizer.py:294:26 | `new_token.rstrip().lstrip()` |  /  | library / re | - | - |  |
| allnews_am/tokenizer/tokenizer.py:296:20 | `self.multitoken(clean_token)` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:300:14 | `s['tokens'].append(('{s}-{e}'.format(s=start_p, e=end_p), clean_tok...` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:302:16 | `s['tokens'].append((index, t))` |  /  | local / local | - | - |  |
| allnews_am/tokenizer/tokenizer.py:305:14 | `s['tokens'].append((index, clean_token))` |  /  | local / local | - | - |  |
