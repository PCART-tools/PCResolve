## @package pcresolve.flow.transfer.source_evidence
#  Build source evidence for a flow query.
#
#
#  Caches source spans and snippets only for the current summary.
#  为当前摘要构造并缓存源码位置与片段证据。



class SourceEvidenceMixin:

    def evidence(self, node):
        return self.evidence_at(self.ref, node)

    def evidence_at(self, ref, node):
        first = getattr(node, 'lineno')
        start = getattr(node, 'col_offset')
        last = getattr(node, 'end_lineno')
        end = getattr(node, 'end_col_offset')
        key = (ref.file_path, first, start, last, end)
        if key in self.evidence_cache:
            return self.evidence_cache[key]
        source_lines = (self.source_lines if ref.file_path == self.ref.file_path else
                        [line.encode('utf-8') for line in
                         self.analyzer.texts[ref.file_path].split('\n')])
        if first == last:
            snippet = source_lines[first - 1][start:end]
        else:
            if last is None:
                raise TypeError("unsupported operand type(s) for -: 'NoneType' and 'int'")
            snippet = b'\n'.join([source_lines[first - 1][start:]] +
                                  source_lines[first:last - 1] +
                                  [source_lines[last - 1][:end]])
        value = {
            'file_path': ref.file_path, 'lineno': first, 'col_offset': start,
            'end_lineno': last, 'end_col_offset': end, 'source_text': snippet.decode('utf-8'),
        }
        self.evidence_cache[key] = value
        return value
