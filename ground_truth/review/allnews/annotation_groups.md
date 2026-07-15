# allnews -- Annotation Groups (277 groups, 553 records)

## Summary

| Evidence | Groups | Records | Needs Human |
|----------|--------|---------|-------------|
| static_obvious | 13 | 17 | 0 |
| static_context | 100 | 229 | 0 |
| manual_reasoned | 164 | 307 | 307 |
| **Total** | **277** | **553** | **307** |

## Group 1: page -> python/python (20 records)

| Evidence | static_context |
| Needs human | no (0/20) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/wikiextractor/WikiExtractor.py:2533 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>page.append(line)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2542
- <code>page.append(listClose[c])</code> -- allnews_am/wikiextractor/WikiExtractor.py:2545
- <code>page.append('')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2550
- <code>page.append('&lt;h%d&gt;%s&lt;/h%d&gt;' % (lev, title, lev))</code> -- allnews_am/wikiextractor/WikiExtractor.py:2558
- <code>page.append(title)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2576
- ... and 15 more

**All bindings (3 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2533: <code>[]</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2794: <code>[]</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2818: <code>[]</code>

## Group 2: m -> library/re (15 records)

| Evidence | static_context |
| Needs human | no (0/15) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>tagRE.search(line)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2813 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>m.group(2)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2816
- <code>m.group(3)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2822
- <code>m.group(3)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2824
- <code>m.group(3)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2826
- <code>m.group(3)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2828
- ... and 10 more

**All bindings (2 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2813: <code>tagRE.search(line)</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2878: <code>tagRE.search(line)</code>

## Group 3: m -> ?/? (14 records)

| Evidence | manual_reasoned |
| Needs human | yes (14/14) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/WikiExtractor.py:674 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>m.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:675
- <code>m.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:675
- <code>m.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:675
- <code>m.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:676
- <code>m.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:743
- <code>m.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:743
- <code>m.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:744
- <code>m.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:758
- <code>m.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:758
- <code>m.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2015
- <code>m.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2468
- <code>m.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2469
- <code>m.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2471
- <code>m.group(3)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2472

**All bindings (5 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L674: <code>for target</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L742: <code>for target</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L757: <code>for target</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2014: <code>for target</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2467: <code>for target</code>

## Group 4: groupP -> library/argparse (14 records)

| Evidence | static_context |
| Needs human | no (0/14) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.add_argument_group('Processing')</code> @ allnews_am/wikiextractor/WikiExtractor.py:3130 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>groupP.add_argument('--html', action='store_true', help='produce HTML output, subsumes --links')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3131
- <code>groupP.add_argument('-l', '--links', action='store_true', help='preserve links')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3133
- <code>groupP.add_argument('-s', '--sections', action='store_true', help='preserve sections')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3135
- <code>groupP.add_argument('--lists', action='store_true', help='preserve lists')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3137
- <code>groupP.add_argument('-ns', '--namespaces', default='', metavar='ns1,ns2', help='accepted namespaces </code> -- allnews_am/wikiextractor/WikiExtractor.py:3139
- ... and 9 more

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3130: <code>parser.add_argument_group('Processing')</code>

## Group 5: parser -> library/argparse (13 records)

| Evidence | static_context |
| Needs human | no (0/13) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>argparse.ArgumentParser(\n            formatter_class=argparse.ArgumentDefaultsH</code> @ allnews_am/__init__.py:6 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>parser.add_argument('--corpus', default=os.path.join(file_dir, '../data/corpus_100k'), help='The pat</code> -- allnews_am/__init__.py:8
- <code>parser.add_argument('--model_name', default='embeddings.model', help='The name of the model file (sa</code> -- allnews_am/__init__.py:12
- <code>parser.add_argument('--size', default=100, help='Size of the embedding.')</code> -- allnews_am/__init__.py:15
- <code>parser.add_argument('--window', default=5, help='Context window size.')</code> -- allnews_am/__init__.py:16
- <code>parser.add_argument('--min_count', default=5, help='Minimum number of occurrences for word.')</code> -- allnews_am/__init__.py:17
- ... and 8 more

**All bindings (1 unique):**
- <code>allnews_am/__init__.py</code> L6: <code>argparse.ArgumentParser(\n            formatter_class=argparse.ArgumentDefaultsH</code>

## Group 6: self -> ?/? (12 records)

| Evidence | manual_reasoned |
| Needs human | yes (12/12) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:597 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.transform(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:646
- <code>self.wiki2text(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:647
- <code>self.clean(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:648
- <code>self.write_output(out, text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:655
- <code>self.transform1(wikitext[cur:m.start()])</code> -- allnews_am/wikiextractor/WikiExtractor.py:675
- <code>self.transform1(wikitext[cur:])</code> -- allnews_am/wikiextractor/WikiExtractor.py:678
- <code>self.expand(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:687
- <code>self.expandTemplate(wikitext[s + 2:e - 2])</code> -- allnews_am/wikiextractor/WikiExtractor.py:858
- <code>self.expand(title)</code> -- allnews_am/wikiextractor/WikiExtractor.py:989
- <code>self.transform(p)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1089
- <code>self.templateParams(params)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1092
- <code>self.transform(instantiated)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1100

**All bindings (5 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L597: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L666: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L682: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L825: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L935: <code>parameter self</code>

## Group 7: Punct -> ?/? (9 records)

| Evidence | manual_reasoned |
| Needs human | yes (9/9) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>class Punct</code> @ allnews_am/tokenizer/tokenizer.py:40 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Punct.all()</code> -- allnews_am/tokenizer/tokenizer.py:127
- <code>Punct.inter()</code> -- allnews_am/tokenizer/tokenizer.py:132
- <code>Punct.metric(double=True)</code> -- allnews_am/tokenizer/tokenizer.py:133
- <code>Punct.all(linear=True)</code> -- allnews_am/tokenizer/tokenizer.py:146
- <code>Punct.all()</code> -- allnews_am/tokenizer/tokenizer.py:151
- <code>Punct.all(linear=True)</code> -- allnews_am/tokenizer/tokenizer.py:152
- <code>Punct.all(linear=True)</code> -- allnews_am/tokenizer/tokenizer.py:168
- <code>Punct.all(linear=True)</code> -- allnews_am/tokenizer/tokenizer.py:176
- <code>Punct.all(linear=True)</code> -- allnews_am/tokenizer/tokenizer.py:177

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L40: <code>class Punct</code>

## Group 8: output -> library/codecs (9 records)

| Evidence | static_context |
| Needs human | no (0/9) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>codecs.open(output_file, 'wb', 'utf-8')</code> @ allnews_am/wikiextractor/WikiExtractor.py:2751 |
| Owner | codecs |
| Proposed GT | library / codecs |

**Representative expressions:**

- <code>output.write('&lt;page&gt;\n')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2771
- <code>output.write('   &lt;title&gt;%s&lt;/title&gt;\n' % title)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2772
- <code>output.write('   &lt;ns&gt;%s&lt;/ns&gt;\n' % ns)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2773
- <code>output.write('   &lt;id&gt;%s&lt;/id&gt;\n' % id)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2774
- <code>output.write('   &lt;text&gt;')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2775
- ... and 4 more

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2751: <code>codecs.open(output_file, 'wb', 'utf-8')</code>

## Group 9: self -> ?/? (7 records)

| Evidence | manual_reasoned |
| Needs human | yes (7/7) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ allnews_am/processing.py:26 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._require(self.WORDS, self.POS, self.CHUNK)</code> -- allnews_am/processing.py:39
- <code>self._grids(fileids)</code> -- allnews_am/processing.py:44
- <code>self._require(self.WORDS, self.POS, self.CHUNK)</code> -- allnews_am/processing.py:59
- <code>self._grids(fileids)</code> -- allnews_am/processing.py:64
- <code>self._get_column(grid, self._colmap['pos'])</code> -- allnews_am/processing.py:67
- <code>self._get_column(grid, self._colmap['words'])</code> -- allnews_am/processing.py:70
- <code>self._get_column(grid, self._colmap[column])</code> -- allnews_am/processing.py:71

**All bindings (3 unique):**
- <code>allnews_am/processing.py</code> L26: <code>parameter self</code>
- <code>allnews_am/processing.py</code> L46: <code>parameter self</code>
- <code>allnews_am/processing.py</code> L66: <code>parameter self</code>

## Group 10: m -> ?/? (6 records)

| Evidence | manual_reasoned |
| Needs human | yes (6/6) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/WikiExtractor.py:762 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>m.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:763
- <code>m.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:763
- <code>m.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:768
- <code>m.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:768
- <code>m.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:770
- <code>m.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:770

**All bindings (3 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L762: <code>for target</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L767: <code>for target</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L769: <code>for target</code>

## Group 11: out -> ?/? (6 records)

| Evidence | manual_reasoned |
| Needs human | yes (6/6) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter out</code> @ allnews_am/wikiextractor/WikiExtractor.py:559 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>out.write(out_str)</code> -- allnews_am/wikiextractor/WikiExtractor.py:579
- <code>out.write('\n')</code> -- allnews_am/wikiextractor/WikiExtractor.py:580
- <code>out.write(header)</code> -- allnews_am/wikiextractor/WikiExtractor.py:589
- <code>out.write(line)</code> -- allnews_am/wikiextractor/WikiExtractor.py:593
- <code>out.write('\n')</code> -- allnews_am/wikiextractor/WikiExtractor.py:594
- <code>out.write(footer)</code> -- allnews_am/wikiextractor/WikiExtractor.py:595

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L559: <code>parameter out</code>

## Group 12: stack -> ?/? (6 records)

| Evidence | manual_reasoned |
| Needs human | yes (6/6) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[-lmatch]</code> @ allnews_am/wikiextractor/WikiExtractor.py:1238 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>stack.append(lmatch)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1249
- <code>stack.pop()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1252
- <code>stack.append(openCount - lmatch)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1261
- <code>stack.append(-lmatch)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1273
- <code>stack.pop()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1276
- <code>stack.append(lmatch - openCount)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1283

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1238: <code>[-lmatch]</code>

## Group 13: parser -> library/argparse (6 records)

| Evidence | static_context |
| Needs human | no (0/6) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),\n                   </code> @ allnews_am/wikiextractor/WikiExtractor.py:3113 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>parser.add_argument('input', help='XML wiki dump file')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3116
- <code>parser.add_argument_group('Output')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3118
- <code>parser.add_argument_group('Processing')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3130
- <code>parser.add_argument('--processes', type=int, default=default_process_count, help='Number of processe</code> -- allnews_am/wikiextractor/WikiExtractor.py:3158
- <code>parser.add_argument_group('Special')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3161
- ... and 1 more

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3113: <code>argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),\n                   </code>

## Group 14: m1 -> library/re (6 records)

| Evidence | static_context |
| Needs human | no (0/6) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>reOpen.search(text, cur)</code> @ allnews_am/wikiextractor/WikiExtractor.py:1231 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>m1.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1234
- <code>m1.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1234
- <code>m1.group()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1235
- <code>m1.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1239
- <code>m1.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1264
- ... and 1 more

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1231: <code>reOpen.search(text, cur)</code>

## Group 15: next -> ?/? (5 records)

| Evidence | manual_reasoned |
| Needs human | yes (5/5) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>nextPat.search(text, cur)</code> @ allnews_am/wikiextractor/WikiExtractor.py:1312 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>next.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1316
- <code>next.group(0)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1318
- <code>next.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1328
- <code>next.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1330
- <code>next.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1332

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1312: <code>nextPat.search(text, cur)</code>

## Group 16: params -> ?/? (5 records)

| Evidence | manual_reasoned |
| Needs human | yes (5/5) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>functionParams(args, ('source', 'pattern', 'replace', 'count', 'plain'))</code> @ allnews_am/wikiextractor/WikiExtractor.py:1457 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>params.get('source', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1458
- <code>params.get('pattern', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1459
- <code>params.get('replace', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1460
- <code>params.get('count', 0)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1461
- <code>params.get('plain', 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1462

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1457: <code>functionParams(args, ('source', 'pattern', 'replace', 'count', 'plain'))</code>

## Group 17: self -> ?/? (5 records)

| Evidence | manual_reasoned |
| Needs human | yes (5/5) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:1742 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.function(other, x)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1743
- <code>self.function(other)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1746
- <code>self.function(other, x)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1749
- <code>self.function(other)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1752
- <code>self.function(value1, value2)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1755

**All bindings (5 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1742: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1745: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1748: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1751: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1754: <code>parameter self</code>

## Group 18: self -> ?/? (5 records)

| Evidence | manual_reasoned |
| Needs human | yes (5/5) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/tokenizer/tokenizer.py:186 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.print_()</code> -- allnews_am/tokenizer/tokenizer.py:187
- <code>self.purification()</code> -- allnews_am/tokenizer/tokenizer.py:248
- <code>self.is_segment(self.text[checkpoint:], l - checkpoint)</code> -- allnews_am/tokenizer/tokenizer.py:253
- <code>self.find_token(s['segment'], l)</code> -- allnews_am/tokenizer/tokenizer.py:290
- <code>self.multitoken(clean_token)</code> -- allnews_am/tokenizer/tokenizer.py:296

**All bindings (3 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L186: <code>parameter self</code>
- <code>allnews_am/tokenizer/tokenizer.py</code> L247: <code>parameter self</code>
- <code>allnews_am/tokenizer/tokenizer.py</code> L270: <code>parameter self</code>

## Group 19: groupS -> library/argparse (5 records)

| Evidence | static_context |
| Needs human | no (0/5) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.add_argument_group('Special')</code> @ allnews_am/wikiextractor/WikiExtractor.py:3161 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>groupS.add_argument('-q', '--quiet', action='store_true', help='suppress reporting progress info')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3162
- <code>groupS.add_argument('--debug', action='store_true', help='print debug info')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3164
- <code>groupS.add_argument('-a', '--article', action='store_true', help='analyze a file containing a single</code> -- allnews_am/wikiextractor/WikiExtractor.py:3166
- <code>groupS.add_argument('--log_file', help='path to save the log info')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3168
- <code>groupS.add_argument('-v', '--version', action='version', version='%(prog)s ' + version, help='print </code> -- allnews_am/wikiextractor/WikiExtractor.py:3170

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3161: <code>parser.add_argument_group('Special')</code>

## Group 20: parser -> library/argparse (5 records)

| Evidence | static_context |
| Needs human | no (0/5) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),\n        formatter_c</code> @ allnews_am/wikiextractor/cirrus-extract.py:191 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>parser.add_argument('input', help='Cirrus Json wiki dump file')</code> -- allnews_am/wikiextractor/cirrus-extract.py:194
- <code>parser.add_argument_group('Output')</code> -- allnews_am/wikiextractor/cirrus-extract.py:196
- <code>parser.add_argument_group('Processing')</code> -- allnews_am/wikiextractor/cirrus-extract.py:205
- <code>parser.add_argument_group('Special')</code> -- allnews_am/wikiextractor/cirrus-extract.py:209
- <code>parser.parse_args()</code> -- allnews_am/wikiextractor/cirrus-extract.py:216

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L191: <code>argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),\n        formatter_c</code>

## Group 21: headers -> python/python (5 records)

| Evidence | static_context |
| Needs human | no (0/5) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>{}</code> @ allnews_am/wikiextractor/WikiExtractor.py:2534 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>headers.keys()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2563
- <code>headers.items()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2615
- <code>headers.clear()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2618
- <code>headers.items()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2643
- <code>headers.clear()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2646

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2534: <code>{}</code>

## Group 22: spans -> python/python (5 records)

| Evidence | static_context |
| Needs human | no (0/5) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/wikiextractor/WikiExtractor.py:755 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>spans.append((m.start(), m.end()))</code> -- allnews_am/wikiextractor/WikiExtractor.py:758
- <code>spans.append((m.start(), m.end()))</code> -- allnews_am/wikiextractor/WikiExtractor.py:763
- <code>spans.append((m.start(), m.end()))</code> -- allnews_am/wikiextractor/WikiExtractor.py:768
- <code>spans.append((m.start(), m.end()))</code> -- allnews_am/wikiextractor/WikiExtractor.py:770
- <code>spans.append((start.start(), end.end()))</code> -- allnews_am/wikiextractor/WikiExtractor.py:2053

**All bindings (2 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L755: <code>[]</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2036: <code>[]</code>

## Group 23: out -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>StringIO()</code> @ allnews_am/wikiextractor/WikiExtractor.py:3022 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>out.getvalue()</code> -- allnews_am/wikiextractor/WikiExtractor.py:3033
- <code>out.truncate(0)</code> -- allnews_am/wikiextractor/WikiExtractor.py:3039
- <code>out.seek(0)</code> -- allnews_am/wikiextractor/WikiExtractor.py:3040
- <code>out.close()</code> -- allnews_am/wikiextractor/WikiExtractor.py:3044

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3022: <code>StringIO()</code>

## Group 24: out -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter out</code> @ allnews_am/wikiextractor/cirrus-extract.py:120 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>out.write(header)</code> -- allnews_am/wikiextractor/cirrus-extract.py:132
- <code>out.write(line.encode('utf-8'))</code> -- allnews_am/wikiextractor/cirrus-extract.py:135
- <code>out.write('\n')</code> -- allnews_am/wikiextractor/cirrus-extract.py:136
- <code>out.write(footer)</code> -- allnews_am/wikiextractor/cirrus-extract.py:137

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L120: <code>parameter out</code>

## Group 25: params -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>functionParams(args, ('source', 'target', 'start', 'plain'))</code> @ allnews_am/wikiextractor/WikiExtractor.py:1434 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>params.get('source', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1435
- <code>params.get('target', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1436
- <code>params.get('start', 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1437
- <code>params.get('plain', 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1438

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1434: <code>functionParams(args, ('source', 'target', 'start', 'plain'))</code>

## Group 26: s['tokens'] -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>s['tokens'].append((index, dict_word['word']))</code> -- allnews_am/tokenizer/tokenizer.py:285
- <code>s['tokens'].append(('{s}-{e}'.format(s=start_p, e=end_p), clean_token))</code> -- allnews_am/tokenizer/tokenizer.py:300
- <code>s['tokens'].append((index, t))</code> -- allnews_am/tokenizer/tokenizer.py:302
- <code>s['tokens'].append((index, clean_token))</code> -- allnews_am/tokenizer/tokenizer.py:305


## Group 27: self -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:2703 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.open(next(self.nextFile))</code> -- allnews_am/wikiextractor/WikiExtractor.py:2713
- <code>self.close()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2717
- <code>self.open(next(self.nextFile))</code> -- allnews_am/wikiextractor/WikiExtractor.py:2718
- <code>self.reserve(len(data))</code> -- allnews_am/wikiextractor/WikiExtractor.py:2721

**All bindings (3 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2703: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2715: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2720: <code>parameter self</code>

## Group 28: self -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/cirrus-extract.py:86 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.open(self.nextFile.next())</code> -- allnews_am/wikiextractor/cirrus-extract.py:96
- <code>self.close()</code> -- allnews_am/wikiextractor/cirrus-extract.py:100
- <code>self.open(self.nextFile.next())</code> -- allnews_am/wikiextractor/cirrus-extract.py:101
- <code>self.reserve(len(data))</code> -- allnews_am/wikiextractor/cirrus-extract.py:104

**All bindings (3 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L86: <code>parameter self</code>
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L98: <code>parameter self</code>
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L103: <code>parameter self</code>

## Group 29: groupO -> library/argparse (4 records)

| Evidence | static_context |
| Needs human | no (0/4) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.add_argument_group('Output')</code> @ allnews_am/wikiextractor/WikiExtractor.py:3118 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>groupO.add_argument('-o', '--output', default='text', help="directory for extracted files (or '-' fo</code> -- allnews_am/wikiextractor/WikiExtractor.py:3119
- <code>groupO.add_argument('-b', '--bytes', default='1M', help='maximum bytes per output file (default %(de</code> -- allnews_am/wikiextractor/WikiExtractor.py:3121
- <code>groupO.add_argument('-c', '--compress', action='store_true', help='compress output files using bzip'</code> -- allnews_am/wikiextractor/WikiExtractor.py:3124
- <code>groupO.add_argument('--json', action='store_true', help='write output in json format instead of the </code> -- allnews_am/wikiextractor/WikiExtractor.py:3126

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3118: <code>parser.add_argument_group('Output')</code>

## Group 30: closeRE -> library/re (4 records)

| Evidence | static_context |
| Needs human | no (0/4) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(closeDelim, re.IGNORECASE)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2034 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>closeRE.search(text, start.end())</code> -- allnews_am/wikiextractor/WikiExtractor.py:2041
- <code>closeRE.search(text, end.end())</code> -- allnews_am/wikiextractor/WikiExtractor.py:2048
- <code>closeRE.search(text, end.end())</code> -- allnews_am/wikiextractor/WikiExtractor.py:2061
- <code>closeRE.search(text, next.end())</code> -- allnews_am/wikiextractor/WikiExtractor.py:2073

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2034: <code>re.compile(closeDelim, re.IGNORECASE)</code>

## Group 31: m2 -> library/re (4 records)

| Evidence | static_context |
| Needs human | no (0/4) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>reNext.search(text, end)</code> @ allnews_am/wikiextractor/WikiExtractor.py:1241 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>m2.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1244
- <code>m2.group()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1245
- <code>m2.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1246
- <code>m2.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1246

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1241: <code>reNext.search(text, end)</code>

## Group 32: start -> library/re (4 records)

| Evidence | static_context |
| Needs human | no (0/4) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>openRE.search(text, 0)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2038 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>start.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2041
- <code>start.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2053
- <code>start.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2066
- <code>start.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2070

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2038: <code>openRE.search(text, 0)</code>

## Group 33: Punct(':') -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Punct(':').regex()</code> -- allnews_am/tokenizer/tokenizer.py:119
- <code>Punct(':').regex()</code> -- allnews_am/tokenizer/tokenizer.py:122
- <code>Punct(':').regex()</code> -- allnews_am/tokenizer/tokenizer.py:125


## Group 34: Template -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>class Template</code> @ allnews_am/wikiextractor/WikiExtractor.py:398 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Template.parse(parts[0])</code> -- allnews_am/wikiextractor/WikiExtractor.py:474
- <code>Template.parse(parts[1])</code> -- allnews_am/wikiextractor/WikiExtractor.py:477
- <code>Template.parse(options.templates[title])</code> -- allnews_am/wikiextractor/WikiExtractor.py:1041

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L398: <code>class Template</code>

## Group 35: end -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>end0</code> @ allnews_am/wikiextractor/WikiExtractor.py:2050 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>end.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2053
- <code>end.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2055
- <code>end.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2060

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2050: <code>end0</code>

## Group 36: params -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>functionParams(args, ('s', 'i', 'j'))</code> @ allnews_am/wikiextractor/WikiExtractor.py:1409 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>params.get('s', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1410
- <code>params.get('i', 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1411
- <code>params.get('j', -1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1412

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1409: <code>functionParams(args, ('s', 'i', 'j'))</code>

## Group 37: params -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>functionParams(args, ('s', 'i', 'len'))</code> @ allnews_am/wikiextractor/WikiExtractor.py:1420 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>params.get('s', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1421
- <code>params.get('i', 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1422
- <code>params.get('len', 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1423

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1420: <code>functionParams(args, ('s', 'i', 'len'))</code>

## Group 38: params -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>functionParams(args, ('s'))</code> @ allnews_am/wikiextractor/WikiExtractor.py:1428 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>params.get('s', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1429
- <code>params.get('source', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1474
- <code>params.get('count', '1')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1475

**All bindings (2 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1428: <code>functionParams(args, ('s'))</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1473: <code>functionParams(args, ('s'))</code>

## Group 39: self -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:2678 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._dirname()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2682
- <code>self._filepath()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2685
- <code>self._dirname()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2695

**All bindings (2 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2678: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2694: <code>parameter self</code>

## Group 40: self -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/cirrus-extract.py:64 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._dirname()</code> -- allnews_am/wikiextractor/cirrus-extract.py:68
- <code>self._filepath()</code> -- allnews_am/wikiextractor/cirrus-extract.py:71
- <code>self._dirname()</code> -- allnews_am/wikiextractor/cirrus-extract.py:79

**All bindings (2 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L64: <code>parameter self</code>
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L78: <code>parameter self</code>

## Group 41: self.file -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:2715 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.file.tell()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2716
- <code>self.file.write(data)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2722
- <code>self.file.close()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2725

**All bindings (3 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2715: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2720: <code>parameter self</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2724: <code>parameter self</code>

## Group 42: self.file -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/cirrus-extract.py:98 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.file.tell()</code> -- allnews_am/wikiextractor/cirrus-extract.py:99
- <code>self.file.write(data)</code> -- allnews_am/wikiextractor/cirrus-extract.py:105
- <code>self.file.close()</code> -- allnews_am/wikiextractor/cirrus-extract.py:108

**All bindings (3 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L98: <code>parameter self</code>
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L103: <code>parameter self</code>
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L107: <code>parameter self</code>

## Group 43: source -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>params.get('source', '')</code> @ allnews_am/wikiextractor/WikiExtractor.py:1435 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>source.find(pattern, start)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1442
- <code>source.replace(pattern, replace, count)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1465
- <code>source.replace(pattern, replace)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1467

**All bindings (2 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1435: <code>params.get('source', '')</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1458: <code>params.get('source', '')</code>

## Group 44: string -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | UNRESOLVED |
| Proposed GT | ? / ? |

**All expressions:**

- <code>string.encode('utf-8')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1900
- <code>string.lower()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1902
- <code>string.upper()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1906


## Group 45: title -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter title</code> @ allnews_am/wikiextractor/WikiExtractor.py:2412 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>title.find(':')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2413
- <code>title.find(':', colon + 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2418
- <code>title.encode('utf-8')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2422

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2412: <code>parameter title</code>

## Group 46: tpl -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>Template()</code> @ allnews_am/wikiextractor/WikiExtractor.py:405 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>tpl.append(TemplateText(body[start:s]))</code> -- allnews_am/wikiextractor/WikiExtractor.py:413
- <code>tpl.append(TemplateArg(body[s + 3:e - 3]))</code> -- allnews_am/wikiextractor/WikiExtractor.py:414
- <code>tpl.append(TemplateText(body[start:]))</code> -- allnews_am/wikiextractor/WikiExtractor.py:416

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L405: <code>Template()</code>

## Group 47: groupO -> library/argparse (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.add_argument_group('Output')</code> @ allnews_am/wikiextractor/cirrus-extract.py:196 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>groupO.add_argument('-o', '--output', default='text', help="directory for extracted files (or '-' fo</code> -- allnews_am/wikiextractor/cirrus-extract.py:197
- <code>groupO.add_argument('-b', '--bytes', default='1M', help='maximum bytes per output file (default %(de</code> -- allnews_am/wikiextractor/cirrus-extract.py:199
- <code>groupO.add_argument('-c', '--compress', action='store_true', help='compress output files using bzip'</code> -- allnews_am/wikiextractor/cirrus-extract.py:202

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L196: <code>parser.add_argument_group('Output')</code>

## Group 48: logger -> library/logging (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>logging.getLogger()</code> @ allnews_am/wikiextractor/WikiExtractor.py:3286 |
| Owner | logging |
| Proposed GT | library / logging |

**Representative expressions:**

- <code>logger.setLevel(logging.INFO)</code> -- allnews_am/wikiextractor/WikiExtractor.py:3288
- <code>logger.setLevel(logging.DEBUG)</code> -- allnews_am/wikiextractor/WikiExtractor.py:3290
- <code>logger.addHandler(fileHandler)</code> -- allnews_am/wikiextractor/WikiExtractor.py:3294

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3286: <code>logging.getLogger()</code>

## Group 49: m -> library/re (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.match(r'([^:]*):(\s*)(\S(?:.*))', title)</code> @ allnews_am/wikiextractor/WikiExtractor.py:293 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>m.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:295
- <code>m.group(2)</code> -- allnews_am/wikiextractor/WikiExtractor.py:296
- <code>m.group(3)</code> -- allnews_am/wikiextractor/WikiExtractor.py:300

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L293: <code>re.match(r'([^:]*):(\s*)(\S(?:.*))', title)</code>

## Group 50: next -> library/re (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>openRE.search(text, next.end())</code> @ allnews_am/wikiextractor/WikiExtractor.py:2044 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>next.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2044
- <code>next.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2055
- <code>next.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2073

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2044: <code>openRE.search(text, next.end())</code>

## Group 51: quote -> library/urllib (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | FLOW_MERGE |
| Key binding | <code>from urllib.parse import quote</code> @ allnews_am/wikiextractor/WikiExtractor.py:95 |
| Owner | urllib |
| Proposed GT | library / urllib |

**Representative expressions:**

- <code>quote(string.encode('utf-8'))</code> -- allnews_am/wikiextractor/WikiExtractor.py:1900
- <code>quote(title.encode('utf-8'))</code> -- allnews_am/wikiextractor/WikiExtractor.py:2422
- <code>quote(url.encode('utf-8'))</code> -- allnews_am/wikiextractor/WikiExtractor.py:2500

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L95: <code>from urllib.parse import quote</code>

## Group 52: Punct(1) -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Punct(1).regex()</code> -- allnews_am/tokenizer/tokenizer.py:127
- <code>Punct(1).regex()</code> -- allnews_am/tokenizer/tokenizer.py:157


## Group 53: Punct(3) -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Punct(3).regex()</code> -- allnews_am/tokenizer/tokenizer.py:121
- <code>Punct(3).regex()</code> -- allnews_am/tokenizer/tokenizer.py:124


## Group 54: Punct(4) -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Punct(4).regex()</code> -- allnews_am/tokenizer/tokenizer.py:120
- <code>Punct(4).regex()</code> -- allnews_am/tokenizer/tokenizer.py:123


## Group 55: Punct(['dot', 6, 16]) -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Punct(['dot', 6, 16]).regex()</code> -- allnews_am/tokenizer/tokenizer.py:169
- <code>Punct(['dot', 6, 16]).regex()</code> -- allnews_am/tokenizer/tokenizer.py:169


## Group 56: args -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter args</code> @ allnews_am/wikiextractor/WikiExtractor.py:1388 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>args.get(var)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1397
- <code>args.get(str(index))</code> -- allnews_am/wikiextractor/WikiExtractor.py:1399

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1388: <code>parameter args</code>

## Group 57: args -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter args</code> @ allnews_am/wikiextractor/WikiExtractor.py:1485 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>args.get('1')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1487
- <code>args.get('2', 'N/A')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1491

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1485: <code>parameter args</code>

## Group 58: cursor -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>with alias</code> @ allnews_am/db.py:76 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>cursor.execute(sql, (offset, limit))</code> -- allnews_am/db.py:79
- <code>cursor.fetchall()</code> -- allnews_am/db.py:82

**All bindings (1 unique):**
- <code>allnews_am/db.py</code> L76: <code>with alias</code>

## Group 59: extr -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter extr</code> @ allnews_am/wikiextractor/WikiExtractor.py:1777 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extr.expand(valueIfTrue.strip())</code> -- allnews_am/wikiextractor/WikiExtractor.py:1783
- <code>extr.expand(valueIfFalse.strip())</code> -- allnews_am/wikiextractor/WikiExtractor.py:1787

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1777: <code>parameter extr</code>

## Group 60: extr -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter extr</code> @ allnews_am/wikiextractor/WikiExtractor.py:1791 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extr.expand(valueIfTrue.strip())</code> -- allnews_am/wikiextractor/WikiExtractor.py:1802
- <code>extr.expand(valueIfFalse.strip())</code> -- allnews_am/wikiextractor/WikiExtractor.py:1805

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1791: <code>parameter extr</code>

## Group 61: extr -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter extr</code> @ allnews_am/wikiextractor/WikiExtractor.py:1809 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extr.expand(then.strip())</code> -- allnews_am/wikiextractor/WikiExtractor.py:1811
- <code>extr.expand(Else.strip())</code> -- allnews_am/wikiextractor/WikiExtractor.py:1815

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1809: <code>parameter extr</code>

## Group 62: extr -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter extr</code> @ allnews_am/wikiextractor/WikiExtractor.py:1818 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extr.expand(pair[0].strip())</code> -- allnews_am/wikiextractor/WikiExtractor.py:1838
- <code>extr.expand(pair[1].strip())</code> -- allnews_am/wikiextractor/WikiExtractor.py:1842

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1818: <code>parameter extr</code>

## Group 63: extractor -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter extractor</code> @ allnews_am/wikiextractor/WikiExtractor.py:488 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extractor.transform(paramName)</code> -- allnews_am/wikiextractor/WikiExtractor.py:497
- <code>extractor.transform(defaultValue)</code> -- allnews_am/wikiextractor/WikiExtractor.py:503

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L488: <code>parameter extractor</code>

## Group 64: inner -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>text[s + 2:e - 2]</code> @ allnews_am/wikiextractor/WikiExtractor.py:2126 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>inner.find('&#124;')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2128
- <code>inner.rfind('&#124;', curp, s1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2137

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2126: <code>text[s + 2:e - 2]</code>

## Group 65: jobs_queue -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>Queue(maxsize=maxsize)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2954 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>jobs_queue.put(job)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2981
- <code>jobs_queue.put(None)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2989

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2954: <code>Queue(maxsize=maxsize)</code>

## Group 66: line -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>line.decode('utf-8')</code> @ allnews_am/wikiextractor/WikiExtractor.py:2803 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>line.decode('utf-8')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2803
- <code>line.lstrip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2808

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2803: <code>line.decode('utf-8')</code>

## Group 67: m -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter m</code> @ allnews_am/wikiextractor/WikiExtractor.py:332 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>m.group(0)</code> -- allnews_am/wikiextractor/WikiExtractor.py:333
- <code>m.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:334

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L332: <code>parameter m</code>

## Group 68: m -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>tailRE.match(text, e)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2119 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>m.group(0)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2121
- <code>m.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2122

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2119: <code>tailRE.match(text, e)</code>

## Group 69: model -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>Model(input, out)</code> @ allnews_am/NER_models/ner.py:94 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=[metrics.categorical_accura</code> -- allnews_am/NER_models/ner.py:95
- <code>model.summary()</code> -- allnews_am/NER_models/ner.py:97

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L94: <code>Model(input, out)</code>

## Group 70: next -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | UNRESOLVED |
| Proposed GT | ? / ? |

**All expressions:**

- <code>next(self.nextFile)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2713
- <code>next(self.nextFile)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2718


## Group 71: pagename -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>self.title</code> @ allnews_am/wikiextractor/WikiExtractor.py:615 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>pagename.rfind('/')</code> -- allnews_am/wikiextractor/WikiExtractor.py:620
- <code>pagename.find('/')</code> -- allnews_am/wikiextractor/WikiExtractor.py:627

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L615: <code>self.title</code>

## Group 72: params -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>functionParams(args, ('target', 'pos'))</code> @ allnews_am/wikiextractor/WikiExtractor.py:1448 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>params.get('target', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1449
- <code>params.get('pos', 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1450

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1448: <code>functionParams(args, ('target', 'pos'))</code>

## Group 73: pattern -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/WikiExtractor.py:761 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>pattern.finditer(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:762
- <code>pattern.finditer(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:786

**All bindings (2 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L761: <code>for target</code>
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L784: <code>for target</code>

## Group 74: reduce -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>Process(target=reduce_process,\n                     args=(options, output_queue</code> @ allnews_am/wikiextractor/WikiExtractor.py:2948 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>reduce.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2951
- <code>reduce.join()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2997

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2948: <code>Process(target=reduce_process,\n                     args=(options, output_queue</code>

## Group 75: self -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/processing.py:26 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._get_iob_words(grid, tagset, column)</code> -- allnews_am/processing.py:42
- <code>self._get_iob_words(grid, tagset, column)</code> -- allnews_am/processing.py:62

**All bindings (2 unique):**
- <code>allnews_am/processing.py</code> L26: <code>parameter self</code>
- <code>allnews_am/processing.py</code> L46: <code>parameter self</code>

## Group 76: self.frame -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:935 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.frame.push(title, params)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1098
- <code>self.frame.pop()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1101

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L935: <code>parameter self</code>

## Group 77: self.nextFile -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/cirrus-extract.py:86 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.nextFile.next()</code> -- allnews_am/wikiextractor/cirrus-extract.py:96
- <code>self.nextFile.next()</code> -- allnews_am/wikiextractor/cirrus-extract.py:101

**All bindings (2 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L86: <code>parameter self</code>
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L98: <code>parameter self</code>

## Group 78: string[0] -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>string[0].upper()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1674
- <code>string[0].lower()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1683


## Group 79: token -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>self.find_token(s['segment'], l)</code> @ allnews_am/tokenizer/tokenizer.py:290 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>token.end()</code> -- allnews_am/tokenizer/tokenizer.py:292
- <code>token.group(0)</code> -- allnews_am/tokenizer/tokenizer.py:293

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L290: <code>self.find_token(s['segment'], l)</code>

## Group 80: groupS -> library/argparse (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.add_argument_group('Special')</code> @ allnews_am/wikiextractor/cirrus-extract.py:209 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>groupS.add_argument('-q', '--quiet', action='store_true', help='suppress reporting progress info')</code> -- allnews_am/wikiextractor/cirrus-extract.py:210
- <code>groupS.add_argument('-v', '--version', action='version', version='%(prog)s ' + version, help='print </code> -- allnews_am/wikiextractor/cirrus-extract.py:212

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L209: <code>parser.add_argument_group('Special')</code>

## Group 81: input -> library/gzip (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>gzip.open(input_file)</code> @ allnews_am/wikiextractor/cirrus-extract.py:150 |
| Owner | gzip |
| Proposed GT | library / gzip |

**Representative expressions:**

- <code>input.readline()</code> -- allnews_am/wikiextractor/cirrus-extract.py:165
- <code>input.readline()</code> -- allnews_am/wikiextractor/cirrus-extract.py:169

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L150: <code>gzip.open(input_file)</code>

## Group 82: Dense -> library/keras (2 records)

| Evidence | static_obvious |
| Needs human | no (0/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from keras.layers import Dense</code> @ allnews_am/NER_models/ner.py:11 |
| Owner | keras |
| Proposed GT | library / keras |

**Representative expressions:**

- <code>Dense(50, activation='relu')</code> -- allnews_am/NER_models/ner.py:90
- <code>Dense(n_tags + 1, activation='softmax')</code> -- allnews_am/NER_models/ner.py:92

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L11: <code>from keras.layers import Dense</code>

## Group 83: TimeDistributed -> library/keras (2 records)

| Evidence | static_obvious |
| Needs human | no (0/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from keras.layers import TimeDistributed</code> @ allnews_am/NER_models/ner.py:11 |
| Owner | keras |
| Proposed GT | library / keras |

**Representative expressions:**

- <code>TimeDistributed(Dense(50, activation='relu'))</code> -- allnews_am/NER_models/ner.py:90
- <code>TimeDistributed(Dense(n_tags + 1, activation='softmax'))</code> -- allnews_am/NER_models/ner.py:92

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L11: <code>from keras.layers import TimeDistributed</code>

## Group 84: pad_sequences -> library/keras (2 records)

| Evidence | static_obvious |
| Needs human | no (0/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from keras.preprocessing.sequence import pad_sequences</code> @ allnews_am/NER_models/ner.py:12 |
| Owner | keras |
| Proposed GT | library / keras |

**Representative expressions:**

- <code>pad_sequences(maxlen=MAX_LEN, sequences=X, padding='post', value=word2idx['PAD'])</code> -- allnews_am/NER_models/ner.py:103
- <code>pad_sequences(maxlen=MAX_LEN, sequences=y, padding='post', value=tag2idx['PAD'])</code> -- allnews_am/NER_models/ner.py:106

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L12: <code>from keras.preprocessing.sequence import pad_sequences</code>

## Group 85: LazyMap -> library/nltk (2 records)

| Evidence | static_obvious |
| Needs human | no (0/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from nltk.util import LazyMap</code> @ allnews_am/processing.py:3 |
| Owner | nltk |
| Proposed GT | library / nltk |

**Representative expressions:**

- <code>LazyMap(get_iob_words, self._grids(fileids))</code> -- allnews_am/processing.py:44
- <code>LazyMap(get_iob_words, self._grids(fileids))</code> -- allnews_am/processing.py:64

**All bindings (1 unique):**
- <code>allnews_am/processing.py</code> L3: <code>from nltk.util import LazyMap</code>

## Group 86: stack -> python/python (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/wikiextractor/WikiExtractor.py:1304 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>stack.append(delim)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1320
- <code>stack.pop()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1323

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1304: <code>[]</code>

## Group 87: bold -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r"'''(.*?)'''")</code> @ allnews_am/wikiextractor/WikiExtractor.py:383 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>bold.sub('&lt;b&gt;\\1&lt;/b&gt;', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:717
- <code>bold.sub('\\1', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:721

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L383: <code>re.compile(r"'''(.*?)'''")</code>

## Group 88: bold_italic -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r"'''''(.*?)'''''")</code> @ allnews_am/wikiextractor/WikiExtractor.py:382 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>bold_italic.sub('&lt;b&gt;\\1&lt;/b&gt;', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:716
- <code>bold_italic.sub('\\1', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:720

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L382: <code>re.compile(r"'''''(.*?)'''''")</code>

## Group 89: comment -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'&lt;!--.*?--&gt;', re.DOTALL)</code> @ allnews_am/wikiextractor/WikiExtractor.py:351 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>comment.finditer(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:757
- <code>comment.sub('', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2005

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L351: <code>re.compile(r'&lt;!--.*?--&gt;', re.DOTALL)</code>

## Group 90: end -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>closeRE.search(text, end.end())</code> @ allnews_am/wikiextractor/WikiExtractor.py:2061 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>end.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2061
- <code>end.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2070

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2061: <code>closeRE.search(text, end.end())</code>

## Group 91: italic -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r"''(.*?)''")</code> @ allnews_am/wikiextractor/WikiExtractor.py:385 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>italic.sub('&lt;i&gt;\\1&lt;/i&gt;', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:718
- <code>italic.sub('"\\1"', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:723

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L385: <code>re.compile(r"''(.*?)''")</code>

## Group 92: m -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.match(' *([^=]*?) *?=(.*)', param, re.DOTALL)</code> @ allnews_am/wikiextractor/WikiExtractor.py:911 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>m.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:918
- <code>m.group(2)</code> -- allnews_am/wikiextractor/WikiExtractor.py:919

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L911: <code>re.match(' *([^=]*?) *?=(.*)', param, re.DOTALL)</code>

## Group 93: m -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.match('([^:]*)(:.*)', templateTitle)</code> @ allnews_am/wikiextractor/WikiExtractor.py:1699 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>m.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1703
- <code>m.group(2)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1705

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1699: <code>re.match('([^:]*)(:.*)', templateTitle)</code>

## Group 94: m -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>section.match(line)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2553 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>m.group(2)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2555
- <code>m.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2556

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2553: <code>section.match(line)</code>

## Group 95: openRE -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(openDelim, re.IGNORECASE)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2033 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>openRE.search(text, 0)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2038
- <code>openRE.search(text, next.end())</code> -- allnews_am/wikiextractor/WikiExtractor.py:2044

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2033: <code>re.compile(openDelim, re.IGNORECASE)</code>

## Group 96: split_part -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.match(s, word)</code> @ allnews_am/tokenizer/tokenizer.py:233 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>split_part.group(0)</code> -- allnews_am/tokenizer/tokenizer.py:235
- <code>split_part.end()</code> -- allnews_am/tokenizer/tokenizer.py:236

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L233: <code>re.match(s, word)</code>

## Group 97: tagRE -> library/re (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'(.*?)&lt;(/?\w+)[^&gt;]*?&gt;(?:([^&lt;]*)(&lt;.*?&gt;)?)?')</code> @ allnews_am/wikiextractor/WikiExtractor.py:2737 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>tagRE.search(line)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2813
- <code>tagRE.search(line)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2878

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2737: <code>re.compile(r'(.*?)&lt;(/?\w+)[^&gt;]*?&gt;(?:([^&lt;]*)(&lt;.*?&gt;)?)?')</code>

## Group 98: output -> library/sys (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>sys.stdout if PY2 else sys.stdout.buffer</code> @ allnews_am/wikiextractor/WikiExtractor.py:3068 |
| Owner | sys |
| Proposed GT | library / sys |

**Representative expressions:**

- <code>output.write(spool.pop(next_page).encode('utf-8'))</code> -- allnews_am/wikiextractor/WikiExtractor.py:3078
- <code>output.close()</code> -- allnews_am/wikiextractor/WikiExtractor.py:3103

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3068: <code>sys.stdout if PY2 else sys.stdout.buffer</code>

## Group 99: Bidirectional(LSTM(units=25, return_sequences=True, recurrent_dropout=0 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Bidirectional(LSTM(units=25, return_sequences=True, recurrent_dropout=0.3))(model)</code> -- allnews_am/NER_models/ner.py:88


## Group 100: Else -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter Else</code> @ allnews_am/wikiextractor/WikiExtractor.py:1809 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Else.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1815

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1809: <code>parameter Else</code>

## Group 101: Embedding(input_dim=n_words + 2, output_dim=EMBEDDING, input_length=MAX_LEN, mask_zero=True) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Embedding(input_dim=n_words + 2, output_dim=EMBEDDING, input_length=MAX_LEN, mask_zero=True)(input)</code> -- allnews_am/NER_models/ner.py:86


## Group 102: Extractor(id, revid, title, page) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Extractor(id, revid, title, page).extract(sys.stdout)</code> -- allnews_am/wikiextractor/WikiExtractor.py:3248


## Group 103: Punct(2) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>Punct(2).regex()</code> -- allnews_am/tokenizer/tokenizer.py:157


## Group 104: TimeDistributed(Dense(50, activation='relu')) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>TimeDistributed(Dense(50, activation='relu'))(model)</code> -- allnews_am/NER_models/ner.py:90


## Group 105: TimeDistributed(Dense(n_tags + 1, activation='softmax')) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>TimeDistributed(Dense(n_tags + 1, activation='softmax'))(model)</code> -- allnews_am/NER_models/ner.py:92


## Group 106: args[0] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>args[0].strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1929


## Group 107: args[1] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>args[1].strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1929


## Group 108: catSet -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Proposed GT | ? / ? |

**All expressions:**

- <code>catSet.add(mCat.group(1))</code> -- allnews_am/wikiextractor/WikiExtractor.py:2811


## Group 109: clean -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Proposed GT | ? / ? |

**All expressions:**

- <code>clean(self, text)</code> -- allnews_am/wikiextractor/cirrus-extract.py:133


## Group 110: cls.LINEAR_PUNCTUATION -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter cls</code> @ allnews_am/tokenizer/tokenizer.py:98 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>cls.LINEAR_PUNCTUATION.values()</code> -- allnews_am/tokenizer/tokenizer.py:100

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L98: <code>parameter cls</code>

## Group 111: cls.PUNCTUATION -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter cls</code> @ allnews_am/tokenizer/tokenizer.py:98 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>cls.PUNCTUATION.values()</code> -- allnews_am/tokenizer/tokenizer.py:100

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L98: <code>parameter cls</code>

## Group 112: compact -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Proposed GT | ? / ? |

**All expressions:**

- <code>compact(text)</code> -- allnews_am/wikiextractor/cirrus-extract.py:134


## Group 113: dict -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>AbbreviationsDictionary</code> @ allnews_am/tokenizer/tokenizer.py:280 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>dict.get_word(s['segment'][l:])</code> -- allnews_am/tokenizer/tokenizer.py:281

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L280: <code>AbbreviationsDictionary</code>

## Group 114: e -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>Extractor(*job[:4])</code> @ allnews_am/wikiextractor/WikiExtractor.py:3030 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>e.extract(out)</code> -- allnews_am/wikiextractor/WikiExtractor.py:3032

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3030: <code>Extractor(*job[:4])</code>

## Group 115: extr -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter extr</code> @ allnews_am/wikiextractor/WikiExtractor.py:1764 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extr.expand(expr)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1767

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1764: <code>parameter extr</code>

## Group 116: extr -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extr.expand(ifnex)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1884


## Group 117: extractor -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter extractor</code> @ allnews_am/wikiextractor/WikiExtractor.py:1915 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extractor.transform(p)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1946

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1915: <code>parameter extractor</code>

## Group 118: extractor -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter extractor</code> @ allnews_am/wikiextractor/WikiExtractor.py:1915 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extractor.templateParams(params)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1947

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1915: <code>parameter extractor</code>

## Group 119: extractor -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>Process(target=extract_process,\n                            args=(options, i, j</code> @ allnews_am/wikiextractor/WikiExtractor.py:2960 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>extractor.start()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2963

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2960: <code>Process(target=extract_process,\n                            args=(options, i, j</code>

## Group 120: functionName -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>functionName.lower()</code> @ allnews_am/wikiextractor/WikiExtractor.py:1927 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>functionName.lower()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1927

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1927: <code>functionName.lower()</code>

## Group 121: get_url -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Proposed GT | ? / ? |

**All expressions:**

- <code>get_url(self.id)</code> -- allnews_am/wikiextractor/cirrus-extract.py:126


## Group 122: header -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>header.encode('utf-8')</code> @ allnews_am/wikiextractor/WikiExtractor.py:588 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>header.encode('utf-8')</code> -- allnews_am/wikiextractor/WikiExtractor.py:588

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L588: <code>header.encode('utf-8')</code>

## Group 123: header -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>header.encode('utf-8')</code> @ allnews_am/wikiextractor/cirrus-extract.py:130 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>header.encode('utf-8')</code> -- allnews_am/wikiextractor/cirrus-extract.py:130

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L130: <code>header.encode('utf-8')</code>

## Group 124: inner[:pipe] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>inner[:pipe].rstrip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2133


## Group 125: inner[pipe + 1:] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>inner[pipe + 1:].strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2141


## Group 126: jobs_queue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter jobs_queue</code> @ allnews_am/wikiextractor/WikiExtractor.py:3010 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>jobs_queue.get()</code> -- allnews_am/wikiextractor/WikiExtractor.py:3026

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3010: <code>parameter jobs_queue</code>

## Group 127: left -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/WikiExtractor.py:766 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>left.finditer(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:767

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L766: <code>for target</code>

## Group 128: line -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>line.encode('utf-8')</code> @ allnews_am/wikiextractor/WikiExtractor.py:592 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>line.encode('utf-8')</code> -- allnews_am/wikiextractor/WikiExtractor.py:592

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L592: <code>line.encode('utf-8')</code>

## Group 129: line -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/WikiExtractor.py:2538 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>line.startswith('++')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2571

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2538: <code>for target</code>

## Group 130: line -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>line[i:].strip()</code> @ allnews_am/wikiextractor/WikiExtractor.py:2610 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>line.strip('.-')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2639

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2610: <code>line[i:].strip()</code>

## Group 131: line -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>line.decode('utf-8')</code> @ allnews_am/wikiextractor/WikiExtractor.py:2877 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>line.decode('utf-8')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2877

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2877: <code>line.decode('utf-8')</code>

## Group 132: line -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/cirrus-extract.py:134 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>line.encode('utf-8')</code> -- allnews_am/wikiextractor/cirrus-extract.py:135

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L134: <code>for target</code>

## Group 133: line.lstrip() -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>line.decode('utf-8')</code> @ allnews_am/wikiextractor/WikiExtractor.py:2803 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>line.lstrip().startswith('[[Category:')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2808

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2803: <code>line.decode('utf-8')</code>

## Group 134: line[i:] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>line[i:].strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2610


## Group 135: listCount -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>listCount[:-1]</code> @ allnews_am/wikiextractor/WikiExtractor.py:2603 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>listCount.append(0)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2605

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2603: <code>listCount[:-1]</code>

## Group 136: lvalue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter lvalue</code> @ allnews_am/wikiextractor/WikiExtractor.py:1791 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>lvalue.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1795

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1791: <code>parameter lvalue</code>

## Group 137: lvalue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>extr.expand(pair[0].strip())</code> @ allnews_am/wikiextractor/WikiExtractor.py:1838 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>lvalue.split('&#124;')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1844

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1838: <code>extr.expand(pair[0].strip())</code>

## Group 138: magicWordsRE -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>magicWordsRE.sub('', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:735


## Group 139: match -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/WikiExtractor.py:786 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>match.group()</code> -- allnews_am/wikiextractor/WikiExtractor.py:787

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L786: <code>for target</code>

## Group 140: model -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter model</code> @ allnews_am/NER_models/ner.py:100 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>model.fit(X_tr, np.array(y_tr), batch_size=BATCH_SIZE, epochs=EPOCHS, validation_split=0.1, validati</code> -- allnews_am/NER_models/ner.py:112

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L100: <code>parameter model</code>

## Group 141: new_segment -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>self.text[checkpoint:(l + punct_len)]</code> @ allnews_am/tokenizer/tokenizer.py:256 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>new_segment.rstrip()</code> -- allnews_am/tokenizer/tokenizer.py:257

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L256: <code>self.text[checkpoint:(l + punct_len)]</code>

## Group 142: new_segment.rstrip() -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>self.text[checkpoint:(l + punct_len)]</code> @ allnews_am/tokenizer/tokenizer.py:256 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>new_segment.rstrip().lstrip()</code> -- allnews_am/tokenizer/tokenizer.py:257

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L256: <code>self.text[checkpoint:(l + punct_len)]</code>

## Group 143: new_token -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>token.group(0)</code> @ allnews_am/tokenizer/tokenizer.py:293 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>new_token.rstrip()</code> -- allnews_am/tokenizer/tokenizer.py:294

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L293: <code>token.group(0)</code>

## Group 144: new_token.rstrip() -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>token.group(0)</code> @ allnews_am/tokenizer/tokenizer.py:293 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>new_token.rstrip().lstrip()</code> -- allnews_am/tokenizer/tokenizer.py:294

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L293: <code>token.group(0)</code>

## Group 145: nextPat -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>startPat</code> @ allnews_am/wikiextractor/WikiExtractor.py:1310 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>nextPat.search(text, cur)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1312

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1310: <code>startPat</code>

## Group 146: options.filter_category_exclude -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code> @ allnews_am/wikiextractor/WikiExtractor.py:109 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>options.filter_category_exclude.add(line.lstrip('^'))</code> -- allnews_am/wikiextractor/WikiExtractor.py:3270

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L109: <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code>

## Group 147: options.filter_category_include -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code> @ allnews_am/wikiextractor/WikiExtractor.py:109 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>options.filter_category_include.add(line)</code> -- allnews_am/wikiextractor/WikiExtractor.py:3272

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L109: <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code>

## Group 148: options.ignored_tag_patterns -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code> @ allnews_am/wikiextractor/WikiExtractor.py:109 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>options.ignored_tag_patterns.append((left, right))</code> -- allnews_am/wikiextractor/WikiExtractor.py:361

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L109: <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code>

## Group 149: options.knownNamespaces -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code> @ allnews_am/wikiextractor/WikiExtractor.py:109 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>options.knownNamespaces.get(ns, '0')</code> -- allnews_am/wikiextractor/WikiExtractor.py:617

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L109: <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code>

## Group 150: options.redirects -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code> @ allnews_am/wikiextractor/WikiExtractor.py:109 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>options.redirects.get(title)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1033

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L109: <code>SimpleNamespace(\n\n    ##\n    # Defined in &lt;siteinfo&gt;\n    # We include as def</code>

## Group 151: output -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>OutputSplitter(nextFile, file_size, file_compress)</code> @ allnews_am/wikiextractor/cirrus-extract.py:158 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>output.write(page.encode('utf-8'))</code> -- allnews_am/wikiextractor/cirrus-extract.py:183

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L158: <code>OutputSplitter(nextFile, file_size, file_compress)</code>

## Group 152: output_queue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>Queue(maxsize=maxsize)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2936 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>output_queue.put(None)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2995

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2936: <code>Queue(maxsize=maxsize)</code>

## Group 153: output_queue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter output_queue</code> @ allnews_am/wikiextractor/WikiExtractor.py:3010 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>output_queue.put((page_num, text))</code> -- allnews_am/wikiextractor/WikiExtractor.py:3038

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3010: <code>parameter output_queue</code>

## Group 154: output_queue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter output_queue</code> @ allnews_am/wikiextractor/WikiExtractor.py:3048 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>output_queue.get()</code> -- allnews_am/wikiextractor/WikiExtractor.py:3090

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3048: <code>parameter output_queue</code>

## Group 155: page -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>header + title + '\n\n' + text + '\n&lt;/doc&gt;\n'</code> @ allnews_am/wikiextractor/cirrus-extract.py:182 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>page.encode('utf-8')</code> -- allnews_am/wikiextractor/cirrus-extract.py:183

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L182: <code>header + title + '\n\n' + text + '\n&lt;/doc&gt;\n'</code>

## Group 156: pair[0] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>pair[0].strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1838


## Group 157: pair[1] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>pair[1].strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1842


## Group 158: param -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>param.strip()</code> @ allnews_am/wikiextractor/WikiExtractor.py:929 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>param.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:929

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L929: <code>param.strip()</code>

## Group 159: param -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/WikiExtractor.py:1834 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>param.split('=', 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1837

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1834: <code>for target</code>

## Group 160: parameters -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>['']</code> @ allnews_am/wikiextractor/WikiExtractor.py:1163 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>parameters.extend(par[1:])</code> -- allnews_am/wikiextractor/WikiExtractor.py:1175

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1163: <code>['']</code>

## Group 161: paramsList[cur:] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>paramsList[cur:].split(sep)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1168


## Group 162: paramsList[cur:s] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>paramsList[cur:s].split(sep)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1152


## Group 163: parts[0] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>parts[0].strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:988


## Group 164: primary -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>primary.strip()</code> @ allnews_am/wikiextractor/WikiExtractor.py:1829 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>primary.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1829

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1829: <code>primary.strip()</code>

## Group 165: right -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/WikiExtractor.py:766 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>right.finditer(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:769

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L766: <code>for target</code>

## Group 166: rvalue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>rvalue.strip()</code> @ allnews_am/wikiextractor/WikiExtractor.py:1792 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>rvalue.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1792

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1792: <code>rvalue.strip()</code>

## Group 167: s -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>s.strip()</code> @ allnews_am/processing.py:84 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>s.strip()</code> -- allnews_am/processing.py:84

**All bindings (1 unique):**
- <code>allnews_am/processing.py</code> L84: <code>s.strip()</code>

## Group 168: self.__dict__ -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:86 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__dict__.update(kwargs)</code> -- allnews_am/wikiextractor/WikiExtractor.py:87

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L86: <code>parameter self</code>

## Group 169: self.connection -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/db.py:64 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.connection.cursor()</code> -- allnews_am/db.py:76

**All bindings (1 unique):**
- <code>allnews_am/db.py</code> L64: <code>parameter self</code>

## Group 170: self.default -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:488 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.default.subst(params, extractor, depth + 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:502

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L488: <code>parameter self</code>

## Group 171: self.name -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:488 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.name.subst(params, extractor, depth + 1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:496

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L488: <code>parameter self</code>

## Group 172: self.segments -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/tokenizer/tokenizer.py:247 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.segments.append({'segment': clean_segment, 'id': len(self.segments) + 1, 'tokens': []})</code> -- allnews_am/tokenizer/tokenizer.py:258

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L247: <code>parameter self</code>

## Group 173: self.title -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:597 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.title.find(':')</code> -- allnews_am/wikiextractor/WikiExtractor.py:609

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L597: <code>parameter self</code>

## Group 174: self.values -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ allnews_am/wikiextractor/WikiExtractor.py:1634 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.values.get(name)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1635

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1634: <code>parameter self</code>

## Group 175: self.xml -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ allnews_am/tokenizer/tokenizer.py:20 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.xml.getElementsByTagName('unit')</code> -- allnews_am/tokenizer/tokenizer.py:24

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L20: <code>parameter self</code>

## Group 176: spans -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[span]</code> @ allnews_am/wikiextractor/WikiExtractor.py:2067 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>spans.append((start.start(), end.end()))</code> -- allnews_am/wikiextractor/WikiExtractor.py:2070

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2067: <code>[span]</code>

## Group 177: spans -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter spans</code> @ allnews_am/wikiextractor/WikiExtractor.py:2082 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>spans.sort()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2086

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2082: <code>parameter spans</code>

## Group 178: string -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter string</code> @ allnews_am/wikiextractor/WikiExtractor.py:1679 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>string.lower()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1685

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1679: <code>parameter string</code>

## Group 179: syntaxhighlight -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>syntaxhighlight.finditer(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:742


## Group 180: tag2idx -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>{t: i+1 for i, t in enumerate(tags)}</code> @ allnews_am/NER_models/ner.py:73 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>tag2idx.items()</code> -- allnews_am/NER_models/ner.py:76

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L73: <code>{t: i+1 for i, t in enumerate(tags)}</code>

## Group 181: tailRE -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>tailRE.match(text, e)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2119


## Group 182: template -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>Template.parse(options.templates[title])</code> @ allnews_am/wikiextractor/WikiExtractor.py:1041 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>template.subst(params, self)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1099

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1041: <code>Template.parse(options.templates[title])</code>

## Group 183: templateTitle -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter templateTitle</code> @ allnews_am/wikiextractor/WikiExtractor.py:1690 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>templateTitle.startswith(':')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1695

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1690: <code>parameter templateTitle</code>

## Group 184: test -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter test</code> @ allnews_am/wikiextractor/WikiExtractor.py:1809 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>test.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1813

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1809: <code>parameter test</code>

## Group 185: testValue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter testValue</code> @ allnews_am/wikiextractor/WikiExtractor.py:1777 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>testValue.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1780

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1777: <code>parameter testValue</code>

## Group 186: text -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>text.replace(match.group(), '%s_%d' % (placeholder, index))</code> @ allnews_am/wikiextractor/WikiExtractor.py:787 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>text.replace(match.group(), '%s_%d' % (placeholder, index))</code> -- allnews_am/wikiextractor/WikiExtractor.py:787

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L787: <code>text.replace(match.group(), '%s_%d' % (placeholder, index))</code>

## Group 187: text -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>text.replace('&lt;&lt;', '«').replace('&gt;&gt;', '»')</code> @ allnews_am/wikiextractor/WikiExtractor.py:790 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>text.replace('&lt;&lt;', '«')</code> -- allnews_am/wikiextractor/WikiExtractor.py:790

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L790: <code>text.replace('&lt;&lt;', '«').replace('&gt;&gt;', '»')</code>

## Group 188: text -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | FLOW_MERGE |
| Key binding | <code>text.replace('\t', ' ')</code> @ allnews_am/wikiextractor/WikiExtractor.py:795 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>text.replace('\t', ' ')</code> -- allnews_am/wikiextractor/WikiExtractor.py:795

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L795: <code>text.replace('\t', ' ')</code>

## Group 189: text -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter text</code> @ allnews_am/wikiextractor/WikiExtractor.py:2528 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>text.split('\n')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2538

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2528: <code>parameter text</code>

## Group 190: text.replace('&lt;&lt;', '«') -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | FLOW_MERGE |
| Key binding | <code>text.replace('&lt;&lt;', '«').replace('&gt;&gt;', '»')</code> @ allnews_am/wikiextractor/WikiExtractor.py:790 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>text.replace('&lt;&lt;', '«').replace('&gt;&gt;', '»')</code> -- allnews_am/wikiextractor/WikiExtractor.py:790

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L790: <code>text.replace('&lt;&lt;', '«').replace('&gt;&gt;', '»')</code>

## Group 191: then -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter then</code> @ allnews_am/wikiextractor/WikiExtractor.py:1809 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>then.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1811

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1809: <code>parameter then</code>

## Group 192: title -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>title.strip(' _')</code> @ allnews_am/wikiextractor/WikiExtractor.py:289 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>title.strip(' _')</code> -- allnews_am/wikiextractor/WikiExtractor.py:289

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L289: <code>title.strip(' _')</code>

## Group 193: title[colon + 1:] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>title[colon + 1:].strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1022


## Group 194: tpl -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>comprehension target</code> @ allnews_am/wikiextractor/WikiExtractor.py:441 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>tpl.subst(params, extractor, depth)</code> -- allnews_am/wikiextractor/WikiExtractor.py:441

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L441: <code>comprehension target</code>

## Group 195: unit -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>for target</code> @ allnews_am/tokenizer/tokenizer.py:25 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>unit.getElementsByTagName('p')</code> -- allnews_am/tokenizer/tokenizer.py:26

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L25: <code>for target</code>

## Group 196: url -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter url</code> @ allnews_am/wikiextractor/WikiExtractor.py:2497 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>url.encode('utf-8')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2500

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2497: <code>parameter url</code>

## Group 197: v -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>comprehension target</code> @ allnews_am/wikiextractor/WikiExtractor.py:1844 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>v.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1844

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1844: <code>comprehension target</code>

## Group 198: valueIfFalse -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter valueIfFalse</code> @ allnews_am/wikiextractor/WikiExtractor.py:1777 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>valueIfFalse.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1787

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1777: <code>parameter valueIfFalse</code>

## Group 199: valueIfFalse -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter valueIfFalse</code> @ allnews_am/wikiextractor/WikiExtractor.py:1791 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>valueIfFalse.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1805

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1791: <code>parameter valueIfFalse</code>

## Group 200: valueIfTrue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>extr.expand(valueIfTrue.strip())</code> @ allnews_am/wikiextractor/WikiExtractor.py:1783 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>valueIfTrue.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1783

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1783: <code>extr.expand(valueIfTrue.strip())</code>

## Group 201: valueIfTrue -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter valueIfTrue</code> @ allnews_am/wikiextractor/WikiExtractor.py:1791 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>valueIfTrue.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:1802

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1791: <code>parameter valueIfTrue</code>

## Group 202: w -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ allnews_am/wikiextractor/WikiExtractor.py:2991 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>w.join()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2992

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2991: <code>for target</code>

## Group 203: word2idx -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>{w: i + 2 for i, w in enumerate(words)}</code> @ allnews_am/NER_models/ner.py:68 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>word2idx.items()</code> -- allnews_am/NER_models/ner.py:71

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L68: <code>{w: i + 2 for i, w in enumerate(words)}</code>

## Group 204: allnews_am -> library/allnews_am (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>import allnews_am.processing</code> @ train_fastext.py:6 |
| Owner | allnews_am |
| Proposed GT | library / allnews_am |

**Representative expressions:**

- <code>allnews_am.parse_w2v_ft_args(file_dir)</code> -- train_fastext.py:54

**All bindings (1 unique):**
- <code>train_fastext.py</code> L6: <code>import allnews_am.processing</code>

## Group 205: allnews_am.processing -> library/allnews_am (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>import allnews_am.processing</code> @ train_fastext.py:6 |
| Owner | allnews_am |
| Proposed GT | library / allnews_am |

**Representative expressions:**

- <code>allnews_am.processing.ConllReader(root=os.path.join(file_dir, 'allnews_am/NER_datasets'), fileids=['</code> -- train_fastext.py:19

**All bindings (1 unique):**
- <code>train_fastext.py</code> L6: <code>import allnews_am.processing</code>

## Group 206: allnews_am.processing.ConllReader(root=os.path.join(file_dir, 'allnews_am/NER_datasets'), fileids=['train.conll03', 'dev.conll03', 'test.conll03'], columntypes=(allnews_am.processing.ConllReader.WORDS, allnews_am.processing.ConllReader.POS, allnews_am.processing.ConllReader.CHUNK, allnews_am.processing.ConllReader.NE)) -> library/allnews_am (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>import allnews_am.processing</code> @ train_fastext.py:6 |
| Owner | allnews_am |
| Proposed GT | library / allnews_am |

**Representative expressions:**

- <code>allnews_am.processing.ConllReader(root=os.path.join(file_dir, 'allnews_am/NER_datasets'), fileids=['</code> -- train_fastext.py:19

**All bindings (1 unique):**
- <code>train_fastext.py</code> L6: <code>import allnews_am.processing</code>

## Group 207: t -> library/allnews_am (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>tokenizer.Tokenizer(s)</code> @ allnews_am/processing.py:89 |
| Owner | allnews_am |
| Proposed GT | library / allnews_am |

**Representative expressions:**

- <code>t.segmentation()</code> -- allnews_am/processing.py:90

**All bindings (1 unique):**
- <code>allnews_am/processing.py</code> L89: <code>tokenizer.Tokenizer(s)</code>

## Group 208: t.segmentation() -> library/allnews_am (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>tokenizer.Tokenizer(s)</code> @ allnews_am/processing.py:89 |
| Owner | allnews_am |
| Proposed GT | library / allnews_am |

**Representative expressions:**

- <code>t.segmentation().tokenization()</code> -- allnews_am/processing.py:90

**All bindings (1 unique):**
- <code>allnews_am/processing.py</code> L89: <code>tokenizer.Tokenizer(s)</code>

## Group 209: tokenizer -> library/allnews_am (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>import allnews_am.tokenizer.tokenizer</code> @ allnews_am/processing.py:6 |
| Owner | allnews_am |
| Proposed GT | library / allnews_am |

**Representative expressions:**

- <code>tokenizer.Tokenizer(s)</code> -- allnews_am/processing.py:89

**All bindings (1 unique):**
- <code>allnews_am/processing.py</code> L6: <code>import allnews_am.tokenizer.tokenizer</code>

## Group 210: args.bytes[-1] -> library/argparse (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.parse_args()</code> @ allnews_am/wikiextractor/WikiExtractor.py:3176 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>args.bytes[-1].lower()</code> -- allnews_am/wikiextractor/WikiExtractor.py:3193

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3176: <code>parser.parse_args()</code>

## Group 211: args.bytes[-1] -> library/argparse (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.parse_args()</code> @ allnews_am/wikiextractor/cirrus-extract.py:216 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>args.bytes[-1].lower()</code> -- allnews_am/wikiextractor/cirrus-extract.py:219

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L216: <code>parser.parse_args()</code>

## Group 212: args.discard_elements -> library/argparse (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.parse_args()</code> @ allnews_am/wikiextractor/WikiExtractor.py:3176 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>args.discard_elements.split(',')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3220

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3176: <code>parser.parse_args()</code>

## Group 213: args.ignored_tags -> library/argparse (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.parse_args()</code> @ allnews_am/wikiextractor/WikiExtractor.py:3176 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>args.ignored_tags.split(',')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3206

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3176: <code>parser.parse_args()</code>

## Group 214: args.namespaces -> library/argparse (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.parse_args()</code> @ allnews_am/wikiextractor/WikiExtractor.py:3176 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>args.namespaces.split(',')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3202

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3176: <code>parser.parse_args()</code>

## Group 215: groupP -> library/argparse (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.add_argument_group('Processing')</code> @ allnews_am/wikiextractor/cirrus-extract.py:205 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>groupP.add_argument('-ns', '--namespaces', default='', metavar='ns1,ns2', help='accepted namespaces'</code> -- allnews_am/wikiextractor/cirrus-extract.py:206

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L205: <code>parser.add_argument_group('Processing')</code>

## Group 216: file -> library/fileinput (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>fileinput.FileInput(template_file,\n                                           o</code> @ allnews_am/wikiextractor/WikiExtractor.py:2910 |
| Owner | fileinput |
| Proposed GT | library / fileinput |

**Representative expressions:**

- <code>file.close()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2913

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2910: <code>fileinput.FileInput(template_file,\n                                           o</code>

## Group 217: file -> library/fileinput (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>fileinput.FileInput(input_file, openhook=fileinput.hook_compressed)</code> @ allnews_am/wikiextractor/WikiExtractor.py:3245 |
| Owner | fileinput |
| Proposed GT | library / fileinput |

**Representative expressions:**

- <code>file.close()</code> -- allnews_am/wikiextractor/WikiExtractor.py:3249

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3245: <code>fileinput.FileInput(input_file, openhook=fileinput.hook_compressed)</code>

## Group 218: input -> library/fileinput (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>fileinput.FileInput(input_file, openhook=fileinput.hook_encoded(\n            en</code> @ allnews_am/wikiextractor/WikiExtractor.py:2871 |
| Owner | fileinput |
| Proposed GT | library / fileinput |

**Representative expressions:**

- <code>input.close()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2920

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2871: <code>fileinput.FileInput(input_file, openhook=fileinput.hook_encoded(\n            en</code>

## Group 219: input -> library/fileinput (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>fileinput.FileInput(input_file, openhook=fileinput.hook_compressed)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2921 |
| Owner | fileinput |
| Proposed GT | library / fileinput |

**Representative expressions:**

- <code>input.close()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2985

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2921: <code>fileinput.FileInput(input_file, openhook=fileinput.hook_compressed)</code>

## Group 220: my_model -> library/gensim (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>gensim.models.fasttext.FastText(\n        sentences=sentences,\n        size=int</code> @ train_fastext.py:32 |
| Owner | gensim |
| Proposed GT | library / gensim |

**Representative expressions:**

- <code>my_model.save(os.path.join(file_dir, 'models/', args.model_name))</code> -- train_fastext.py:46

**All bindings (1 unique):**
- <code>train_fastext.py</code> L32: <code>gensim.models.fasttext.FastText(\n        sentences=sentences,\n        size=int</code>

## Group 221: my_model.wv -> library/gensim (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>gensim.models.fasttext.FastText(\n        sentences=sentences,\n        size=int</code> @ train_fastext.py:32 |
| Owner | gensim |
| Proposed GT | library / gensim |

**Representative expressions:**

- <code>my_model.wv.evaluate_word_analogies(analogy_file)</code> -- train_fastext.py:50

**All bindings (1 unique):**
- <code>train_fastext.py</code> L32: <code>gensim.models.fasttext.FastText(\n        sentences=sentences,\n        size=int</code>

## Group 222: zip_longest -> library/itertools (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | FLOW_MERGE |
| Key binding | <code>from itertools import zip_longest</code> @ allnews_am/wikiextractor/WikiExtractor.py:97 |
| Owner | itertools |
| Proposed GT | library / itertools |

**Representative expressions:**

- <code>zip_longest(listLevel, line, fillvalue='')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2586

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L97: <code>from itertools import zip_longest</code>

## Group 223: out_str -> library/json (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>out_str.encode('utf-8')</code> @ allnews_am/wikiextractor/WikiExtractor.py:578 |
| Owner | json |
| Proposed GT | library / json |

**Representative expressions:**

- <code>out_str.encode('utf-8')</code> -- allnews_am/wikiextractor/WikiExtractor.py:578

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L578: <code>out_str.encode('utf-8')</code>

## Group 224: Bidirectional -> library/keras (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from keras.layers import Bidirectional</code> @ allnews_am/NER_models/ner.py:11 |
| Owner | keras |
| Proposed GT | library / keras |

**Representative expressions:**

- <code>Bidirectional(LSTM(units=25, return_sequences=True, recurrent_dropout=0.3))</code> -- allnews_am/NER_models/ner.py:88

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L11: <code>from keras.layers import Bidirectional</code>

## Group 225: Embedding -> library/keras (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from keras.layers import Embedding</code> @ allnews_am/NER_models/ner.py:11 |
| Owner | keras |
| Proposed GT | library / keras |

**Representative expressions:**

- <code>Embedding(input_dim=n_words + 2, output_dim=EMBEDDING, input_length=MAX_LEN, mask_zero=True)</code> -- allnews_am/NER_models/ner.py:86

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L11: <code>from keras.layers import Embedding</code>

## Group 226: Input -> library/keras (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from keras.models import Input</code> @ allnews_am/NER_models/ner.py:10 |
| Owner | keras |
| Proposed GT | library / keras |

**Representative expressions:**

- <code>Input(shape=(MAX_LEN,))</code> -- allnews_am/NER_models/ner.py:85

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L10: <code>from keras.models import Input</code>

## Group 227: LSTM -> library/keras (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from keras.layers import LSTM</code> @ allnews_am/NER_models/ner.py:11 |
| Owner | keras |
| Proposed GT | library / keras |

**Representative expressions:**

- <code>LSTM(units=25, return_sequences=True, recurrent_dropout=0.3)</code> -- allnews_am/NER_models/ner.py:88

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L11: <code>from keras.layers import LSTM</code>

## Group 228: Model -> library/keras (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from keras.models import Model</code> @ allnews_am/NER_models/ner.py:10 |
| Owner | keras |
| Proposed GT | library / keras |

**Representative expressions:**

- <code>Model(input, out)</code> -- allnews_am/NER_models/ner.py:94

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L10: <code>from keras.models import Model</code>

## Group 229: to_categorical -> library/keras (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from keras.utils import to_categorical</code> @ allnews_am/NER_models/ner.py:13 |
| Owner | keras |
| Proposed GT | library / keras |

**Representative expressions:**

- <code>to_categorical(i, num_classes=n_tags + 1)</code> -- allnews_am/NER_models/ner.py:107

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L13: <code>from keras.utils import to_categorical</code>

## Group 230: logger -> library/logging (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>logging.getLogger()</code> @ allnews_am/wikiextractor/cirrus-extract.py:230 |
| Owner | logging |
| Proposed GT | library / logging |

**Representative expressions:**

- <code>logger.setLevel(logging.INFO)</code> -- allnews_am/wikiextractor/cirrus-extract.py:232

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/cirrus-extract.py</code> L230: <code>logging.getLogger()</code>

## Group 231: LazyConcatenation -> library/nltk (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from nltk.util import LazyConcatenation</code> @ allnews_am/processing.py:3 |
| Owner | nltk |
| Proposed GT | library / nltk |

**Representative expressions:**

- <code>LazyConcatenation(LazyMap(get_iob_words, self._grids(fileids)))</code> -- allnews_am/processing.py:44

**All bindings (1 unique):**
- <code>allnews_am/processing.py</code> L3: <code>from nltk.util import LazyConcatenation</code>

## Group 232: map_tag -> library/nltk (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from nltk.tag import map_tag</code> @ allnews_am/processing.py:4 |
| Owner | nltk |
| Proposed GT | library / nltk |

**Representative expressions:**

- <code>map_tag(self._tagset, tagset, t)</code> -- allnews_am/processing.py:69

**All bindings (1 unique):**
- <code>allnews_am/processing.py</code> L4: <code>from nltk.tag import map_tag</code>

## Group 233: corpus -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/NER_models/ner.py:24 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>corpus.append(sentence)</code> -- allnews_am/NER_models/ner.py:31

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L24: <code>[]</code>

## Group 234: label -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/NER_models/ner.py:35 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>label.append(line.split()[3])</code> -- allnews_am/NER_models/ner.py:39

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L35: <code>[]</code>

## Group 235: labels -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/NER_models/ner.py:25 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>labels.append(label)</code> -- allnews_am/NER_models/ner.py:32

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L25: <code>[]</code>

## Group 236: multitoken -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/tokenizer/tokenizer.py:231 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>multitoken.append(split_part.group(0))</code> -- allnews_am/tokenizer/tokenizer.py:235

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L231: <code>[]</code>

## Group 237: parameters -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/wikiextractor/WikiExtractor.py:1148 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>parameters.extend(par[1:])</code> -- allnews_am/wikiextractor/WikiExtractor.py:1159

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1148: <code>[]</code>

## Group 238: reg_arr -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/tokenizer/tokenizer.py:99 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>reg_arr.append(j)</code> -- allnews_am/tokenizer/tokenizer.py:103

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L99: <code>[]</code>

## Group 239: sentence -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/NER_models/ner.py:34 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>sentence.append(line.split()[0])</code> -- allnews_am/NER_models/ner.py:38

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L34: <code>[]</code>

## Group 240: sentences_entities -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/NER_models/ner.py:43 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>sentences_entities.append(temp)</code> -- allnews_am/NER_models/ner.py:49

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L43: <code>[]</code>

## Group 241: spool -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>{}</code> @ allnews_am/wikiextractor/WikiExtractor.py:3074 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>spool.pop(next_page)</code> -- allnews_am/wikiextractor/WikiExtractor.py:3078

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3074: <code>{}</code>

## Group 242: spool.pop(next_page) -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>{}</code> @ allnews_am/wikiextractor/WikiExtractor.py:3074 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>spool.pop(next_page).encode('utf-8')</code> -- allnews_am/wikiextractor/WikiExtractor.py:3078

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L3074: <code>{}</code>

## Group 243: tags -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/NER_models/ner.py:60 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>tags.extend(tag)</code> -- allnews_am/NER_models/ner.py:62

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L60: <code>[]</code>

## Group 244: temp -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/NER_models/ner.py:45 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>temp.append((corpus[i][j], labels[i][j]))</code> -- allnews_am/NER_models/ner.py:48

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L45: <code>[]</code>

## Group 245: words -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/NER_models/ner.py:54 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>words.extend(sent)</code> -- allnews_am/NER_models/ner.py:57

**All bindings (1 unique):**
- <code>allnews_am/NER_models/ner.py</code> L54: <code>[]</code>

## Group 246: workers -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ allnews_am/wikiextractor/WikiExtractor.py:2958 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>workers.append(extractor)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2964

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2958: <code>[]</code>

## Group 247: EXT_IMAGE_REGEX -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(\n    r"""^(http://&#124;https://)([^][&lt;&gt;"\x00-\x20\x7F\s]+)\n    /([A-Za-</code> @ allnews_am/wikiextractor/WikiExtractor.py:2454 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>EXT_IMAGE_REGEX.match(label)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2484

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2454: <code>re.compile(\n    r"""^(http://&#124;https://)([^][&lt;&gt;"\x00-\x20\x7F\s]+)\n    /([A-Za-</code>

## Group 248: ExtLinkBracketedRegex -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(\n    '\[(((?i)' + '&#124;'.join(wgUrlProtocols) + ')' + EXT_LINK_URL_CLAS</code> @ allnews_am/wikiextractor/WikiExtractor.py:2447 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>ExtLinkBracketedRegex.finditer(text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2467

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2447: <code>re.compile(\n    '\[(((?i)' + '&#124;'.join(wgUrlProtocols) + ')' + EXT_LINK_URL_CLAS</code>

## Group 249: base -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>m.group(3)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2885 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>base.rfind('/')</code> -- allnews_am/wikiextractor/WikiExtractor.py:2886

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2885: <code>m.group(3)</code>

## Group 250: catRE -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'\[\[Category:([^\&#124;]+).*\]\].*')</code> @ allnews_am/wikiextractor/WikiExtractor.py:2740 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>catRE.search(line)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2809

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2740: <code>re.compile(r'\[\[Category:([^\&#124;]+).*\]\].*')</code>

## Group 251: dots -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'\.{4,}')</code> @ allnews_am/wikiextractor/WikiExtractor.py:392 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>dots.sub('...', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:797

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L392: <code>re.compile(r'\.{4,}')</code>

## Group 252: end -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>closeRE.search(text, start.end())</code> @ allnews_am/wikiextractor/WikiExtractor.py:2041 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>end.end()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2048

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2041: <code>closeRE.search(text, start.end())</code>

## Group 253: filter_disambig_page_pattern -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile("{{disambig(uation)?(\&#124;[^}]*)?}}&#124;__DISAMBIG__")</code> @ allnews_am/wikiextractor/WikiExtractor.py:213 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>filter_disambig_page_pattern.match(line)</code> -- allnews_am/wikiextractor/WikiExtractor.py:229

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L213: <code>re.compile("{{disambig(uation)?(\&#124;[^}]*)?}}&#124;__DISAMBIG__")</code>

## Group 254: italic_quote -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r"''\"([^\"]*?)\"''")</code> @ allnews_am/wikiextractor/WikiExtractor.py:384 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>italic_quote.sub('"\\1"', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:722

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L384: <code>re.compile(r"''\"([^\"]*?)\"''")</code>

## Group 255: keyRE -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'key="(\d*)"')</code> @ allnews_am/wikiextractor/WikiExtractor.py:2739 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>keyRE.search(line)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2888

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2739: <code>re.compile(r'key="(\d*)"')</code>

## Group 256: m -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.match('#REDIRECT.*?\[\[([^\]]*)]]', page[0], re.IGNORECASE)</code> @ allnews_am/wikiextractor/WikiExtractor.py:1988 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>m.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1990

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1988: <code>re.match('#REDIRECT.*?\[\[([^\]]*)]]', page[0], re.IGNORECASE)</code>

## Group 257: m.group(1) -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.match(' *([^=]*?) *?=(.*)', param, re.DOTALL)</code> @ allnews_am/wikiextractor/WikiExtractor.py:911 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>m.group(1).strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:918

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L911: <code>re.match(' *([^=]*?) *?=(.*)', param, re.DOTALL)</code>

## Group 258: mCat -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>catRE.search(line)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2809 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>mCat.group(1)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2811

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2809: <code>catRE.search(line)</code>

## Group 259: mk -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>keyRE.search(line)</code> @ allnews_am/wikiextractor/WikiExtractor.py:2888 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>mk.groups()</code> -- allnews_am/wikiextractor/WikiExtractor.py:2890

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2888: <code>keyRE.search(line)</code>

## Group 260: nowiki -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'&lt;nowiki&gt;.*?&lt;/nowiki&gt;')</code> @ allnews_am/wikiextractor/WikiExtractor.py:355 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>nowiki.finditer(wikitext, cur)</code> -- allnews_am/wikiextractor/WikiExtractor.py:674

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L355: <code>re.compile(r'&lt;nowiki&gt;.*?&lt;/nowiki&gt;')</code>

## Group 261: parameterValue -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parameterValue.strip()</code> @ allnews_am/wikiextractor/WikiExtractor.py:922 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>parameterValue.strip()</code> -- allnews_am/wikiextractor/WikiExtractor.py:922

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L922: <code>parameterValue.strip()</code>

## Group 262: quote_quote -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'""([^"]*?)""')</code> @ allnews_am/wikiextractor/WikiExtractor.py:386 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>quote_quote.sub('"\\1"', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:724

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L386: <code>re.compile(r'""([^"]*?)""')</code>

## Group 263: reIncludeonly -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'&lt;includeonly&gt;&#124;&lt;/includeonly&gt;', re.DOTALL)</code> @ allnews_am/wikiextractor/WikiExtractor.py:1975 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>reIncludeonly.sub('', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2019

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1975: <code>re.compile(r'&lt;includeonly&gt;&#124;&lt;/includeonly&gt;', re.DOTALL)</code>

## Group 264: reNext -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile('{{2,}&#124;}{2,}&#124;\[{2,}&#124;]{2,}')</code> @ allnews_am/wikiextractor/WikiExtractor.py:1227 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>reNext.search(text, end)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1241

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1227: <code>re.compile('{{2,}&#124;}{2,}&#124;\[{2,}&#124;]{2,}')</code>

## Group 265: reNoinclude -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'&lt;noinclude&gt;(?:.*?)&lt;/noinclude&gt;', re.DOTALL)</code> @ allnews_am/wikiextractor/WikiExtractor.py:1974 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>reNoinclude.sub('', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2008

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1974: <code>re.compile(r'&lt;noinclude&gt;(?:.*?)&lt;/noinclude&gt;', re.DOTALL)</code>

## Group 266: reOpen -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile('{{2,}&#124;\[{2,}')</code> @ allnews_am/wikiextractor/WikiExtractor.py:1226 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>reOpen.search(text, cur)</code> -- allnews_am/wikiextractor/WikiExtractor.py:1231

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L1226: <code>re.compile('{{2,}&#124;\[{2,}')</code>

## Group 267: section -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r'(==+)\s*(.*?)\s*\1')</code> @ allnews_am/wikiextractor/WikiExtractor.py:2520 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>section.match(line)</code> -- allnews_am/wikiextractor/WikiExtractor.py:2553

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L2520: <code>re.compile(r'(==+)\s*(.*?)\s*\1')</code>

## Group 268: spaces -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.compile(r' {2,}')</code> @ allnews_am/wikiextractor/WikiExtractor.py:389 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>spaces.sub(' ', text)</code> -- allnews_am/wikiextractor/WikiExtractor.py:796

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L389: <code>re.compile(r' {2,}')</code>

## Group 269: text -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>text.replace("'''", '').replace("''", '"')</code> @ allnews_am/wikiextractor/WikiExtractor.py:726 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>text.replace("'''", '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:726

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L726: <code>text.replace("'''", '').replace("''", '"')</code>

## Group 270: text -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>text.replace(',,', ',').replace(',.', '.')</code> @ allnews_am/wikiextractor/WikiExtractor.py:801 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>text.replace(',,', ',')</code> -- allnews_am/wikiextractor/WikiExtractor.py:801

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L801: <code>text.replace(',,', ',').replace(',.', '.')</code>

## Group 271: text -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>text.replace('&#124;-', '')</code> @ allnews_am/wikiextractor/WikiExtractor.py:808 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>text.replace('&#124;-', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:808

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L808: <code>text.replace('&#124;-', '')</code>

## Group 272: text -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>text.replace('&#124;', '')</code> @ allnews_am/wikiextractor/WikiExtractor.py:809 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>text.replace('&#124;', '')</code> -- allnews_am/wikiextractor/WikiExtractor.py:809

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L809: <code>text.replace('&#124;', '')</code>

## Group 273: text.replace("'''", '') -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>text.replace("'''", '').replace("''", '"')</code> @ allnews_am/wikiextractor/WikiExtractor.py:726 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>text.replace("'''", '').replace("''", '"')</code> -- allnews_am/wikiextractor/WikiExtractor.py:726

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L726: <code>text.replace("'''", '').replace("''", '"')</code>

## Group 274: text.replace(',,', ',') -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>text.replace(',,', ',').replace(',.', '.')</code> @ allnews_am/wikiextractor/WikiExtractor.py:801 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>text.replace(',,', ',').replace(',.', '.')</code> -- allnews_am/wikiextractor/WikiExtractor.py:801

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L801: <code>text.replace(',,', ',').replace(',.', '.')</code>

## Group 275: title -> library/re (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>re.sub(substWords, '', title, 1, re.IGNORECASE)</code> @ allnews_am/wikiextractor/WikiExtractor.py:998 |
| Owner | re |
| Proposed GT | library / re |

**Representative expressions:**

- <code>title.find(':')</code> -- allnews_am/wikiextractor/WikiExtractor.py:1019

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L998: <code>re.sub(substWords, '', title, 1, re.IGNORECASE)</code>

## Group 276: SimpleNamespace -> library/types (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | FLOW_MERGE |
| Key binding | <code>from types import SimpleNamespace</code> @ allnews_am/wikiextractor/WikiExtractor.py:98 |
| Owner | types |
| Proposed GT | library / types |

**Representative expressions:**

- <code>SimpleNamespace(knownNamespaces={'Template': 10}, templateNamespace='', templatePrefix='', moduleNam</code> -- allnews_am/wikiextractor/WikiExtractor.py:109

**All bindings (1 unique):**
- <code>allnews_am/wikiextractor/WikiExtractor.py</code> L98: <code>from types import SimpleNamespace</code>

## Group 277: minidom -> library/xml (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from xml.dom import minidom</code> @ allnews_am/tokenizer/tokenizer.py:2 |
| Owner | xml |
| Proposed GT | library / xml |

**Representative expressions:**

- <code>minidom.parse(fullpath)</code> -- allnews_am/tokenizer/tokenizer.py:13

**All bindings (1 unique):**
- <code>allnews_am/tokenizer/tokenizer.py</code> L2: <code>from xml.dom import minidom</code>
