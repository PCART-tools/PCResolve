# allnews — static_obvious (459 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| train_fastext.py:10:0 | `logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| train_fastext.py:12:11 | `os.path.dirname(os.path.realpath(__file__))` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| train_fastext.py:12:27 | `os.path.realpath(__file__)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| train_fastext.py:16:16 | `gensim.models.word2vec.LineSentence(args.corpus)` | library / gensim | library / gensim | direct_import | static_obvious | v: import-backed dotted module call: gensim.models.word2vec.LineSentence |
| train_fastext.py:20:17 | `os.path.join(file_dir, 'allnews_am/NER_datasets')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| train_fastext.py:32:15 | `gensim.models.fasttext.FastText(sentences=sentences, size=int(args....` | library / gensim | library / gensim | direct_import | static_obvious | v: import-backed dotted module call: gensim.models.fasttext.FastText |
| train_fastext.py:34:13 | `int(args.size)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| train_fastext.py:35:15 | `int(args.window)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| train_fastext.py:36:18 | `int(args.min_count)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| train_fastext.py:37:16 | `int(args.workers)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| train_fastext.py:38:14 | `float(args.alpha)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| train_fastext.py:39:15 | `float(args.subsample)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| train_fastext.py:40:17 | `int(args.negative)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| train_fastext.py:44:13 | `int(args.epochs)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| train_fastext.py:47:8 | `os.path.join(file_dir, 'models/', args.model_name)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| train_fastext.py:48:19 | `os.path.join(file_dir, 'data/coarse_avetisyan_ghukasyan_analogies.t...` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| train_fastext.py:55:4 | `main(fast_args)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/processing.py:70:15 | `list(zip(self._get_column(grid, self._colmap['words']), pos_tags, s...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/processing.py:70:20 | `zip(self._get_column(grid, self._colmap['words']), pos_tags, self._...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/processing.py:86:7 | `len(s)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/processing.py:97:45 | `isinstance(t[0], int)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/db.py:37:31 | `object.__new__(cls)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/db.py:59:42 | `pymysql.connect(host=db_host, user=db_user, password=db_pass, db=db...` | library / pymysql | library / pymysql | direct_import | static_obvious | v: import-backed dotted module call: pymysql.connect |
| allnews_am/__init__.py:6:13 | `argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHe...` | library / argparse | library / argparse | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/__init__.py:10:20 | `os.path.join(file_dir, '../data/corpus_100k')` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/NER_models/ner.py:22:11 | `open(link, 'r', encoding='utf8')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:29:16 | `data.readlines()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:38:24 | `line.split()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:39:21 | `line.split()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:41:4 | `data.close()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:44:13 | `range(len(corpus))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:44:19 | `len(corpus)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:46:17 | `range(len(corpus[i]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:46:23 | `len(corpus[i])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:58:10 | `set(words)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:63:9 | `set(tags)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:65:12 | `len(words)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:66:11 | `len(tags)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:68:35 | `enumerate(words)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:73:32 | `enumerate(tags)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/NER_models/ner.py:109:27 | `train_test_split(X, y, test_size=0.2)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/NER_models/ner.py:110:26 | `np.array(y_tr)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/NER_models/ner.py:110:48 | `np.array(y_te)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/NER_models/ner.py:112:28 | `np.array(y_tr)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/NER_models/ner.py:113:80 | `np.array(y_te)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:89:19 | `sorted(self.__dict__)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:90:21 | `'{}={!r}'.format(k, self.__dict__[k])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:91:19 | `'{}({})'.format(type(self).__name__, ', '.join(items))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:91:35 | `type(self)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:91:56 | `', '.join(items)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:192:30 | `set()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:193:30 | `set()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:209:15 | `set(['10', '828'])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:213:31 | `re.compile('{{disambig(uation)?(\\\|[^}]*)?}}\|__DISAMBIG__')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:231:7 | `len(options.filter_category_include)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:231:52 | `len(options.filter_category_include & catSet)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:232:8 | `logging.debug('***No include  ' + str(catSet))` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:232:42 | `str(catSet)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:234:7 | `len(options.filter_category_exclude)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:234:52 | `len(options.filter_category_exclude & catSet)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:235:8 | `logging.debug('***Exclude  ' + str(catSet))` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:235:39 | `str(catSet)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:291:12 | `re.sub('[\\s_]+', ' ', title)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:293:8 | `re.match('([^:]*):(\\s*)(\\S(?:.*))', title)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:302:13 | `normalizeNamespace(prefix)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:308:31 | `ucfirst(rest)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:317:20 | `ucfirst(prefix)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:317:65 | `ucfirst(rest)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:320:16 | `ucfirst(title)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:338:27 | `chr(int(code[1:], 16))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:338:31 | `int(code[1:], 16)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:340:27 | `chr(int(code))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:340:31 | `int(code)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:342:23 | `chr(name2codepoint[code])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:346:11 | `re.sub('&#?(\\w+);', fixup, text)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:351:10 | `re.compile('<!--.*?-->', re.DOTALL)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:355:9 | `re.compile('<nowiki>.*?</nowiki>')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:359:11 | `re.compile('<%s\\b.*?>' % tag, re.IGNORECASE \| re.DOTALL)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:360:12 | `re.compile('</\\s*%s>' % tag, re.IGNORECASE)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:365:4 | `re.compile('<\\s*%s\\b[^>]*/\\s*>' % tag, re.DOTALL \| re.IGNORECASE)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:370:5 | `re.compile('<\\s*%s(\\s*\| [^>]+?)>.*?<\\s*/\\s*%s\\s*>' % (tag, ta...` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:371:28 | `placeholder_tags.items()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:375:15 | `re.compile('^ .*?$')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:378:15 | `re.compile('\\[\\w+[^ ]*? (.*?)]')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:379:23 | `re.compile('\\[\\w+[&\\]]*\\]')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:382:14 | `re.compile("'''''(.*?)'''''")` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:383:7 | `re.compile("'''(.*?)'''")` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:384:15 | `re.compile('\'\'\\"([^\\"]*?)\\"\'\'')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:385:9 | `re.compile("''(.*?)''")` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:386:14 | `re.compile('""([^"]*?)""')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:389:9 | `re.compile(' {2,}')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:392:7 | `re.compile('\\.{4,}')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:405:14 | `Template()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:412:20 | `findMatchingBraces(body, 3)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:413:23 | `TemplateText(body[start:s])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:414:23 | `TemplateArg(body[s + 3:e - 3])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:416:19 | `TemplateText(body[start:])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:441:15 | `''.join([tpl.subst(params, extractor, depth) for tpl in self])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:444:15 | `''.join([text_type(x) for x in self])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:444:24 | `text_type(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:473:16 | `splitParts(parameter)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:475:11 | `len(parts)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:518:15 | `Frame(title, args, self)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:551:20 | `''.join(lines)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:552:26 | `MagicWords()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:553:21 | `Frame()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:564:14 | `get_url(self.id)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:570:24 | `'\n'.join(text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:576:22 | `json.dumps(json_data, ensure_ascii=False)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:601:8 | `logging.info('%s\t%s', self.id, self.title)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:632:41 | `time.strftime('%Y')` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:633:42 | `time.strftime('%m')` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:634:40 | `time.strftime('%d')` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:635:41 | `time.strftime('%H')` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:636:41 | `time.strftime('%H:%M:%S')` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:648:15 | `compact(self.clean(text))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:652:11 | `sum((len(line) for line in text))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:652:15 | `len(line)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:661:11 | `any(errs)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:662:12 | `logging.warn("Template errors in article '%s' (%s): title(%d) recur...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:690:19 | `dropNested(text, '{{', '}}')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:711:19 | `dropNested(text, '{{', '}}')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:712:19 | `dropNested(text, '{\\\|', '\\\|}')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:729:15 | `replaceInternalLinks(text)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:732:15 | `replaceExternalLinks(text)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:743:19 | `unescape(text[cur:m.start()])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:745:21 | `unescape(text[cur:])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:773:15 | `dropSpans(spans, text)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:777:19 | `dropNested(text, '<\\s*%s\\b[^>/]*>' % tag, '<\\s*/\\s*%s>' % tag)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:781:19 | `unescape(text)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:798:15 | `re.sub(' (,:\\.\\)\\]»)', '\\1', text)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:799:15 | `re.sub('(\\[\\(«) ', '\\1', text)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:800:15 | `re.sub('\\n\\W+?\\n', '\n', text, flags=re.U)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:806:19 | `re.sub('!(?:\\s)?style=\\"[a-z]+:(?:\\d+)%;\\"', '', text)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:807:19 | `re.sub('!(?:\\s)?style="[a-z]+:(?:\\d+)%;[a-z]+:(?:#)?(?:[0-9a-z]+)...` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:811:19 | `cgi.escape(text)` | library / cgi | library / cgi | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:822:13 | `re.compile('(?<!{){{(?!{)', re.DOTALL)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:857:20 | `findMatchingBraces(wikitext, 2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:911:16 | `re.match(' *([^=]*?) *?=(.*)', param, re.DOTALL)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:930:31 | `str(unnamedParameterCounter)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:985:8 | `logging.debug('%*sEXPAND %s', self.frame.depth, '', body)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:986:16 | `splitParts(body)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:997:11 | `re.match(substWords, title, re.IGNORECASE)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:998:20 | `re.sub(substWords, '', title, 1, re.IGNORECASE)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1003:12 | `logging.debug('%*s<EXPAND %s %s', self.frame.depth, '', title, ret)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1024:18 | `callParserFunction(funct, parts, self)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1025:12 | `logging.debug('%*s<EXPAND %s %s', self.frame.depth, '', funct, ret)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1028:16 | `fullyQualifiedTemplateTitle(title)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1047:12 | `logging.debug('%*s<EXPAND %s %s', self.frame.depth, '', title, '')` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1050:8 | `logging.debug('%*sTEMPLATE %s: %s', self.frame.depth, '', title, te...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1102:8 | `logging.debug('%*s<EXPAND %s %s', self.frame.depth, '', title, value)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1151:16 | `findMatchingBraces(paramsList)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1157:19 | `len(par)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1173:15 | `len(par)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1223:17 | `re.compile('[{]{%d,}' % ldelim)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1224:17 | `re.compile('[{]{2,}\|}{2,}')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1226:17 | `re.compile('{{2,}\|\\[{2,}')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1227:17 | `re.compile('{{2,}\|}{2,}\|\\[{2,}\|]{2,}')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1267:21 | `len(stack)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1301:14 | `'\|'.join([re.escape(x) for x in openDelim])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1301:24 | `re.escape(x)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1303:19 | `re.compile(openPat + '\|' + c, re.DOTALL)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1303:72 | `zip(openDelim, closeDelim)` | library / itertools | library / itertools | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1309:15 | `re.compile(openPat)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1399:29 | `str(index)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1409:13 | `functionParams(args, ('s', 'i', 'j'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1411:8 | `int(params.get('i', 1) or 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1412:8 | `int(params.get('j', -1) or -1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1415:19 | `len(s)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1420:13 | `functionParams(args, ('s', 'i', 'len'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1422:8 | `int(params.get('i', 1) or 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1423:10 | `int(params.get('len', 1) or 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1428:13 | `functionParams(args, 's')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1430:11 | `len(s)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1434:13 | `functionParams(args, ('source', 'target', 'start', 'plain'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1437:12 | `int('0' + params.get('start', 1))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1438:12 | `int('0' + params.get('plain', 1))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1444:16 | `re.compile(pattern)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1444:16 | `re.compile(pattern).search(source, start)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1448:13 | `functionParams(args, ('target', 'pos'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1450:10 | `int(params.get('pos', 1) or 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1457:13 | `functionParams(args, ('source', 'pattern', 'replace', 'count', 'pla...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1461:12 | `int(params.get('count', 0) or 0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1462:12 | `int(params.get('plain', 1) or 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1469:15 | `re.compile(pattern)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1469:15 | `re.compile(pattern).sub(replace, source, count)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1473:13 | `functionParams(args, 's')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1475:12 | `int(params.get('count', '1'))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1487:10 | `int(float(args.get('1')))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1487:14 | `float(args.get('1'))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1509:11 | `toRoman(num, smallRomans)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1662:15 | `re.compile('\|'.join(MagicWords.switches))` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1662:26 | `'\|'.join(MagicWords.switches)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1682:11 | `len(string)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1697:15 | `ucfirst(templateTitle[1:])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1699:12 | `re.match('([^:]*)(:.*)', templateTitle)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1703:21 | `normalizeNamespace(m.group(1))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1705:32 | `ucfirst(m.group(2))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1718:40 | `ucfirst(templateTitle)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1724:11 | `ucfirst(ns)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1743:15 | `Infix(lambda x, self=self, other=other: self.function(other, x))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1749:15 | `Infix(lambda x, self=self, other=other: self.function(other, x))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1758:8 | `Infix(lambda x, y: round(x, y))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1758:27 | `round(x, y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1768:15 | `re.sub('(?<![!<>])=', '==', expr)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1769:15 | `re.sub('mod', '%', expr)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1770:15 | `re.sub('\x08div\x08', '/', expr)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1771:15 | `re.sub('\x08round\x08', '\|ROUND\|', expr)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1772:15 | `text_type(eval(expr))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1772:25 | `eval(expr)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1810:7 | `re.match('<(?:strong\|span\|p\|div)\\s(?:[^\\s>]*\\s+)*?class="(?:[...` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1840:11 | `len(pair)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1864:16 | `modules.get(module)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1866:16 | `functions.get(function)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1868:19 | `text_type(funct(args))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1868:29 | `funct(args)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1904:43 | `lcfirst(string)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1908:43 | `ucfirst(string)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1910:39 | `text_type(int(string))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1910:49 | `int(string)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1930:12 | `logging.debug('%*s#invoke %s %s %s', extractor.frame.depth, '', mod...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1932:15 | `len(args)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:1935:32 | `fullyQualifiedTemplateTitle(module)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1937:20 | `logging.warn('Template with empty title')` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1948:18 | `sharp_invoke(module, fun, params)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1949:12 | `logging.debug('%*s<#invoke %s %s %s', extractor.frame.depth, '', mo...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1953:19 | `parserFunctions[functionName](extractor, *args)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1974:14 | `re.compile('<noinclude>(?:.*?)</noinclude>', re.DOTALL)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1975:16 | `re.compile('<includeonly>\|</includeonly>', re.DOTALL)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1988:8 | `re.match('#REDIRECT.*?\\[\\[([^\\]]*)]]', page[0], re.IGNORECASE)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:1993:11 | `unescape(''.join(page))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:1993:20 | `''.join(page)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2010:11 | `re.sub('<noinclude\\s*>.*$', '', text, flags=re.DOTALL)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2011:11 | `re.sub('<noinclude/>', '', text)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2014:13 | `re.finditer('<onlyinclude>(.*?)</onlyinclude>', text, re.DOTALL)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2023:12 | `logging.warn('Redefining: %s', title)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2033:13 | `re.compile(openDelim, re.IGNORECASE)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2034:14 | `re.compile(closeDelim, re.IGNORECASE)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2079:11 | `dropSpans(spans, text)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2118:16 | `findBalanced(text)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2136:26 | `findBalanced(inner)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2142:29 | `makeInternalLink(title, label)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2447:24 | `re.compile('\\[(((?i)' + '\|'.join(wgUrlProtocols) + ')' + EXT_LINK...` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2448:17 | `'\|'.join(wgUrlProtocols)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2454:18 | `re.compile('^(http://\|https://)([^][<>"\\x00-\\x20\\x7F\\s]+)\n   ...` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2486:20 | `makeExternalImage(label)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2492:13 | `makeExternalLink(url, label)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2515:9 | `re.compile('\\w+')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2517:18 | `re.compile('&lt;syntaxhighlight .*?&gt;(.*?)&lt;/syntaxhighlight&gt...` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2520:10 | `re.compile('(==+)\\s*(.*?)\\s*\\1')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2541:15 | `len(listLevel)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2544:29 | `reversed(listLevel)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2556:18 | `len(m.group(1))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2563:21 | `list(headers.keys())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2615:32 | `sorted(headers.items())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2622:32 | `'{0:{1}s}'.format(bullet, len(listLevel))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2622:58 | `len(listLevel)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2627:13 | `len(listLevel)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2629:25 | `reversed(listLevel)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2641:13 | `len(headers)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2643:24 | `sorted(headers.items())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2657:19 | `int(entity[2:-1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2659:11 | `chr(numeric_code)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2683:15 | `os.path.isdir(dirname)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.isdir |
| allnews_am/wikiextractor/WikiExtractor.py:2684:12 | `os.makedirs(dirname)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.makedirs |
| allnews_am/wikiextractor/WikiExtractor.py:2692:15 | `os.path.join(self.path_name, '%c%c' % (ord('A') + char2, ord('A') +...` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.join |
| allnews_am/wikiextractor/WikiExtractor.py:2692:54 | `ord('A')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2692:72 | `ord('A')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2721:21 | `len(data)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2729:19 | `bz2.BZ2File(filename + '.bz2', 'w')` | library / bz2 | library / bz2 | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2731:19 | `open(filename, 'wb')` | python / python | python / python | builtin | static_obvious | v: open() is builtins.open; class method def open(self, ...) only reachable via sel |
| allnews_am/wikiextractor/WikiExtractor.py:2737:8 | `re.compile('(.*?)<(/?\\w+)[^>]*?>(?:([^<]*)(<.*?>)?)?')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2739:8 | `re.compile('key="(\\d*)"')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2740:8 | `re.compile('\\[\\[Category:([^\\\|]+).*\\]\\].*')` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2751:17 | `codecs.open(output_file, 'wb', 'utf-8')` | library / codecs | library / codecs | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2752:33 | `enumerate(pages_from(file))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2752:43 | `pages_from(file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2767:19 | `''.join(page)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2768:12 | `define_template(title, text)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2781:12 | `logging.info('Preprocessed %d pages', page_count)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2784:8 | `logging.info("Saved %d templates to '%s'", len(options.templates), ...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2784:51 | `len(options.templates)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2803:15 | `isinstance(line, text_type)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2819:21 | `set()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2871:16 | `fileinput.FileInput(input_file, openhook=fileinput.hook_encoded(enc...` | library / fileinput | library / fileinput | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2871:57 | `fileinput.hook_encoded(encoding='utf-8')` | library / fileinput | library / fileinput | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2877:15 | `isinstance(line, text_type)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2890:23 | `''.join(mk.groups())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2894:15 | `re.search('key="10"', line)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2897:17 | `re.search('key="828"', line)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2905:30 | `default_timer()` | library / timeit | library / timeit | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2907:15 | `os.path.exists(template_file)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.exists |
| allnews_am/wikiextractor/WikiExtractor.py:2908:16 | `logging.info('Loading template definitions from: %s', template_file)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2910:23 | `fileinput.FileInput(template_file, openhook=fileinput.hook_compressed)` | library / fileinput | library / fileinput | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2912:16 | `load_templates(file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2917:26 | `ValueError('to use templates with stdin dump, must supply explicit ...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2918:16 | `logging.info("Preprocessing '%s' to collect template definitions: t...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2919:16 | `load_templates(input, template_file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2921:24 | `fileinput.FileInput(input_file, openhook=fileinput.hook_compressed)` | library / fileinput | library / fileinput | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2922:32 | `default_timer()` | library / timeit | library / timeit | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2923:8 | `logging.info('Loaded %d templates in %.1fs', len(options.templates)...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2923:53 | `len(options.templates)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2926:4 | `logging.info('Starting page extraction from %s.', input_file)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2927:20 | `default_timer()` | library / timeit | library / timeit | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2933:20 | `max(1, process_count)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2936:19 | `Queue(maxsize=maxsize)` | library / multiprocessing | library / multiprocessing | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2945:19 | `Value('i', 0, lock=False)` | library / multiprocessing | library / multiprocessing | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2948:13 | `Process(target=reduce_process, args=(options, output_queue, spool_l...` | library / multiprocessing | library / multiprocessing | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2954:17 | `Queue(maxsize=maxsize)` | library / multiprocessing | library / multiprocessing | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2957:4 | `logging.info('Using %d extract processes.', worker_count)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2959:13 | `range(worker_count)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:2960:20 | `Process(target=extract_process, args=(options, i, jobs_queue, outpu...` | library / multiprocessing | library / multiprocessing | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2968:21 | `pages_from(input)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2970:11 | `keepPage(ns, catSet, page)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:2976:20 | `time.sleep(10)` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2979:16 | `logging.info('Delay %ds', delay)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:2999:23 | `default_timer()` | library / timeit | library / timeit | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3001:4 | `logging.info('Finished %d-process extraction of %d articles in %.1f...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3003:4 | `logging.info('total of page: %d, total of articl page: %d; total of...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3020:4 | `createLogger(options.quiet, options.debug, options.log_file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3022:10 | `StringIO()` | library / io | library / io | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3030:20 | `Extractor(*job[:4])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3036:16 | `logging.exception('Processing page: %s %s', id, title)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3042:12 | `logging.debug('Quit extractor')` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3062:4 | `createLogger(options.quiet, options.debug, options.log_file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3065:19 | `NextFile(out_file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3066:17 | `OutputSplitter(nextFile, file_size, file_compress)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3070:12 | `logging.warn('writing to stdout, so no output compression (use an e...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3072:21 | `default_timer()` | library / timeit | library / timeit | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3081:33 | `len(spool)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3084:49 | `default_timer()` | library / timeit | library / timeit | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3085:16 | `logging.info('Extracted %d articles (%.1f art/s)', next_page, inter...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3087:33 | `default_timer()` | library / timeit | library / timeit | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3096:33 | `len(spool)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3099:15 | `len(spool)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3100:16 | `logging.debug('Collected %d, waiting: %d, %d', len(spool), next_pag...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3100:63 | `len(spool)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3113:13 | `argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), formatt...` | library / argparse | library / argparse | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3113:42 | `os.path.basename(sys.argv[0])` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.basename |
| allnews_am/wikiextractor/WikiExtractor.py:3157:28 | `max(1, cpu_count() - 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3157:35 | `cpu_count()` | library / multiprocessing | library / multiprocessing | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3193:16 | `'kmg'.find(args.bytes[-1].lower())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3194:20 | `int(args.bytes[:-1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3196:18 | `ValueError()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3198:8 | `logging.error('Insufficient or invalid size: %s', args.bytes)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3202:37 | `set(args.namespaces.split(','))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3206:22 | `set(args.ignored_tags.split(','))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3217:8 | `ignoreTag(tag)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3220:34 | `set(args.discard_elements.split(','))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3223:4 | `logging.basicConfig(format=FORMAT)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3228:4 | `createLogger(options.quiet, options.debug, options.log_file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3233:8 | `ignoreTag('a')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3241:15 | `os.path.exists(args.templates)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.exists |
| allnews_am/wikiextractor/WikiExtractor.py:3242:21 | `open(args.templates)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3243:20 | `load_templates(file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3245:15 | `fileinput.FileInput(input_file, openhook=fileinput.hook_compressed)` | library / fileinput | library / fileinput | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3246:25 | `pages_from(file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3248:12 | `Extractor(id, revid, title, page)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3253:34 | `os.path.isdir(output_path)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.isdir |
| allnews_am/wikiextractor/WikiExtractor.py:3255:12 | `os.makedirs(output_path)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.makedirs |
| allnews_am/wikiextractor/WikiExtractor.py:3257:12 | `logging.error('Could not create: %s', output_path)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3261:36 | `len(filter_category)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3262:13 | `open(filter_category)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3264:24 | `f.readlines()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3266:27 | `str(line.strip())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3266:31 | `line.strip()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3267:23 | `line.startswith('#')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3267:47 | `len(line)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3269:25 | `line.startswith('^')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3270:60 | `line.lstrip('^')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3275:20 | `print(u'Category not in utf8, ignored. error cnt %d:\t%s' % (error_...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3276:20 | `print(line)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3277:12 | `logging.info('Excluding categories:')` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3278:12 | `logging.info(str(options.filter_category_exclude))` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3278:25 | `str(options.filter_category_exclude)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3279:12 | `logging.info('Including categories:')` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3280:12 | `logging.info(str(len(options.filter_category_include)))` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3280:25 | `str(len(options.filter_category_include))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3280:29 | `len(options.filter_category_include)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/WikiExtractor.py:3282:4 | `process_dump(input_file, args.templates, output_path, file_size, ar...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/WikiExtractor.py:3286:13 | `logging.getLogger()` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3293:22 | `logging.FileHandler(log_file)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/WikiExtractor.py:3297:4 | `main()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/cirrus-extract.py:69:15 | `os.path.isdir(dirname)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.isdir |
| allnews_am/wikiextractor/cirrus-extract.py:70:12 | `os.makedirs(dirname)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.makedirs |
| allnews_am/wikiextractor/cirrus-extract.py:76:15 | `os.path.join(self.path_name, '%c%c' % (ord('A') + char2, ord('A') +...` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.join |
| allnews_am/wikiextractor/cirrus-extract.py:76:54 | `ord('A')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/cirrus-extract.py:76:72 | `ord('A')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/cirrus-extract.py:104:21 | `len(data)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/cirrus-extract.py:112:19 | `bz2.BZ2File(filename + '.bz2', 'w')` | library / bz2 | library / bz2 | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:114:19 | `open(filename, 'w')` | python / python | python / python | builtin | static_obvious | v: open() is builtins.open; class method def open(self, ...) only reachable via sel |
| allnews_am/wikiextractor/cirrus-extract.py:124:8 | `logging.debug('%s\t%s', self.id, self.title)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:125:15 | `''.join(self.page)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/cirrus-extract.py:150:16 | `gzip.open(input_file)` | library / gzip | library / gzip | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:155:12 | `logging.warn('writing to stdout, so no output compression (use exte...` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:157:19 | `NextFile(out_file)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/cirrus-extract.py:158:17 | `OutputSplitter(nextFile, file_size, file_compress)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/cirrus-extract.py:168:16 | `json.loads(line)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:169:18 | `json.loads(input.readline())` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:179:19 | `re.sub('  \\^ .*', '', text)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:191:13 | `argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]), formatt...` | library / argparse | library / argparse | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:191:42 | `os.path.basename(sys.argv[0])` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.basename |
| allnews_am/wikiextractor/cirrus-extract.py:219:16 | `'kmg'.find(args.bytes[-1].lower())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/cirrus-extract.py:220:20 | `int(args.bytes[:-1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/cirrus-extract.py:222:18 | `ValueError()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/wikiextractor/cirrus-extract.py:224:8 | `logging.error('Insufficient or invalid size: %s', args.bytes)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:228:4 | `logging.basicConfig(format=FORMAT)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:230:13 | `logging.getLogger()` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:237:34 | `os.path.isdir(output_path)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.path.isdir |
| allnews_am/wikiextractor/cirrus-extract.py:239:12 | `os.makedirs(output_path)` | library / os | library / os | direct_import | static_obvious | v: import-backed dotted module call: os.makedirs |
| allnews_am/wikiextractor/cirrus-extract.py:241:12 | `logging.error('Could not create: %s', output_path)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/wikiextractor/cirrus-extract.py:244:4 | `process_dump(input_file, output_path, file_size, args.compress)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/wikiextractor/cirrus-extract.py:248:4 | `main()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:9:12 | `KeyError('Please write dictionary name')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:11:15 | `'{path}/{name}'.format(path=self.PATH, name=name)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:21:11 | `hasattr(self, 'xml')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:22:12 | `Exception('Dictionary is not initialized')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:28:14 | `re.match(text, sentence)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:78:13 | `isinstance(punct, list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:83:14 | `KeyError('Please write punctuation symbol.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:95:11 | `u'\|'.join(reg_arr)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:104:11 | `u'\|'.join(reg_arr)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:108:11 | `u'\|'.join(cls.INTERNATIONAL)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:113:13 | `u'\|'.join(['{}/{}'.format(i, j) for i in cls.METRIC for j in cls.M...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:113:24 | `'{}/{}'.format(i, j)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:115:13 | `u'\|'.join(cls.METRIC)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:119:15 | `Punct(':')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:120:16 | `Punct(4)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:121:16 | `Punct(3)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:122:15 | `Punct(':')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:123:16 | `Punct(4)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:124:16 | `Punct(3)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:125:15 | `Punct(':')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:127:39 | `Punct(1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:157:33 | `Punct(1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:157:113 | `Punct(2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:169:42 | `Punct(['dot', 6, 16])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:169:115 | `Punct(['dot', 6, 16])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:183:23 | `len(text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:192:16 | `'{num}. {string}\n{line}\n'.format(num=s['id'], string=s['segment']...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:194:18 | `'{token}\n'.format(token=t)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:205:9 | `re.match(r, text[pointer:])` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:207:14 | `isinstance(s_r[0], list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:208:22 | `re.findall(s_r[2], text[:pointer])` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:208:79 | `re.findall(s_r[2], text[:pointer])` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:216:14 | `re.match(r, text[pointer:])` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:219:14 | `isinstance(t_r[0], list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:220:22 | `re.findall(t_r[2], text[:pointer])` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:220:79 | `re.findall(t_r[2], text[:pointer])` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:229:14 | `re.match(r['regex'], word)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:233:23 | `re.match(s, word)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:242:18 | `re.sub(r[0], r[1], self.text)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| allnews_am/tokenizer/tokenizer.py:244:23 | `len(self.text)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:260:16 | `len(self.segments)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:271:30 | `Dictionary('abbreviations.xml')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| allnews_am/tokenizer/tokenizer.py:276:16 | `len(s['segment'])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:287:15 | `len(dict_word['word'])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:299:32 | `len(multi)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| allnews_am/tokenizer/tokenizer.py:300:35 | `'{s}-{e}'.format(s=start_p, e=end_p)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
