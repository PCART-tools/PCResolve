# allnews — manual_reasoned (26 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| allnews_am/wikiextractor/WikiExtractor.py:579:12 | `out.write(out_str)` | unknown / unknown | unknown / unknown | file_like_parameter | manual_reasoned | v: out is an unconstrained file-like parameter |
| allnews_am/wikiextractor/WikiExtractor.py:580:12 | `out.write('\n')` | unknown / unknown | unknown / unknown | file_like_parameter | manual_reasoned | v: out is an unconstrained file-like parameter |
| allnews_am/wikiextractor/WikiExtractor.py:589:12 | `out.write(header)` | unknown / unknown | unknown / unknown | file_like_parameter | manual_reasoned | v: out is an unconstrained file-like parameter |
| allnews_am/wikiextractor/WikiExtractor.py:593:16 | `out.write(line)` | unknown / unknown | unknown / unknown | file_like_parameter | manual_reasoned | v: out is an unconstrained file-like parameter |
| allnews_am/wikiextractor/WikiExtractor.py:594:16 | `out.write('\n')` | unknown / unknown | unknown / unknown | file_like_parameter | manual_reasoned | v: out is an unconstrained file-like parameter |
| allnews_am/wikiextractor/WikiExtractor.py:595:12 | `out.write(footer)` | unknown / unknown | unknown / unknown | file_like_parameter | manual_reasoned | v: out is an unconstrained file-like parameter |
| allnews_am/wikiextractor/WikiExtractor.py:2716:11 | `self.file.tell()` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: self.file can be bz2.BZ2File or a Python file object |
| allnews_am/wikiextractor/WikiExtractor.py:2722:8 | `self.file.write(data)` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: self.file can be bz2.BZ2File or a Python file object |
| allnews_am/wikiextractor/WikiExtractor.py:2725:8 | `self.file.close()` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: self.file can be bz2.BZ2File or a Python file object |
| allnews_am/wikiextractor/WikiExtractor.py:2920:16 | `input.close()` | unknown / unknown | library / fileinput | branch_dependent_io_receiver | manual_reasoned | v: input can be sys.stdin or fileinput.FileInput depending on input_file |
| allnews_am/wikiextractor/WikiExtractor.py:2985:4 | `input.close()` | unknown / unknown | library / fileinput | branch_dependent_io_receiver | manual_reasoned | v: input can be sys.stdin or fileinput.FileInput depending on input_file |
| allnews_am/wikiextractor/WikiExtractor.py:3078:12 | `output.write(spool.pop(next_page).encode('utf-8'))` | unknown / unknown | local / local | branch_dependent_io_receiver | manual_reasoned | v: output can be a project-local OutputSplitter or a Python stdout buffer |
| allnews_am/wikiextractor/WikiExtractor.py:3103:8 | `output.close()` | unknown / unknown | local / local | branch_dependent_io_receiver | manual_reasoned | v: output can be a project-local OutputSplitter or a Python stdout buffer |
| allnews_am/wikiextractor/cirrus-extract.py:99:11 | `self.file.tell()` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: self.file can be bz2 or a Python file object |
| allnews_am/wikiextractor/cirrus-extract.py:105:8 | `self.file.write(data)` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: self.file can be bz2 or a Python file object |
| allnews_am/wikiextractor/cirrus-extract.py:108:8 | `self.file.close()` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: self.file can be bz2 or a Python file object |
| allnews_am/wikiextractor/cirrus-extract.py:126:14 | `get_url(self.id)` | unknown / unknown | unknown / unknown | undefined_callable | manual_reasoned | v: callable has no import or definition in cirrus-extract.py |
| allnews_am/wikiextractor/cirrus-extract.py:132:8 | `out.write(header)` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: file-like receiver depends on the runtime output branch |
| allnews_am/wikiextractor/cirrus-extract.py:133:15 | `clean(self, text)` | unknown / unknown | unknown / unknown | undefined_callable | manual_reasoned | v: callable has no import or definition in cirrus-extract.py |
| allnews_am/wikiextractor/cirrus-extract.py:134:20 | `compact(text)` | unknown / unknown | unknown / unknown | undefined_callable | manual_reasoned | v: callable has no import or definition in cirrus-extract.py |
| allnews_am/wikiextractor/cirrus-extract.py:135:12 | `out.write(line.encode('utf-8'))` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: file-like receiver depends on the runtime output branch |
| allnews_am/wikiextractor/cirrus-extract.py:136:12 | `out.write('\n')` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: file-like receiver depends on the runtime output branch |
| allnews_am/wikiextractor/cirrus-extract.py:137:8 | `out.write(footer)` | unknown / unknown | unknown / unknown | branch_dependent_io_receiver | manual_reasoned | v: file-like receiver depends on the runtime output branch |
| allnews_am/wikiextractor/cirrus-extract.py:165:15 | `input.readline()` | unknown / unknown | library / gzip | branch_dependent_io_receiver | manual_reasoned | v: input can be sys.stdin or gzip.open output |
| allnews_am/wikiextractor/cirrus-extract.py:169:29 | `input.readline()` | unknown / unknown | library / gzip | branch_dependent_io_receiver | manual_reasoned | v: input can be sys.stdin or gzip.open output |
| allnews_am/wikiextractor/cirrus-extract.py:183:12 | `output.write(page.encode('utf-8'))` | unknown / unknown | local / local | branch_dependent_io_receiver | manual_reasoned | v: file-like receiver depends on the runtime output branch |
