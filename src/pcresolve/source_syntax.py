## @package pcresolve.source_syntax
#  Read-only AST parsing for modern and archived Python source.

import ast
import io
import tokenize


## Parse source, retaining historical async/await attribute names and spans.
#  @param text Original decoded source, never executed or modified on disk.
#  @param filename Diagnostic filename.
#  @return AST; unrelated syntax failures retain the original SyntaxError.
def parse_python_source(text, filename='<unknown>'):
    try:
        return ast.parse(text, filename=filename)
    except SyntaxError as original:
        lines = text.splitlines(keepends=True)
        replacements = {}
        previous = None
        try:
            for count, token in enumerate(tokenize.generate_tokens(io.StringIO(text).readline)):
                if count >= 1000000:
                    raise original
                if (token.type == tokenize.NAME and token.string in ('async', 'await')
                        and previous is not None and previous.string == '.'):
                    row, column = token.start
                    end_column = token.end[1]
                    end_byte = len(lines[row - 1][:end_column].encode('utf-8'))
                    replacements[(row, end_byte)] = token.string
                    line = lines[row - 1]
                    lines[row - 1] = line[:column] + token.string[:-1] + 'x' + line[end_column:]
                if token.type not in (tokenize.NL, tokenize.COMMENT):
                    previous = token
        except (tokenize.TokenError, IndentationError):
            raise original from None
        if not replacements:
            raise original
        try:
            tree = ast.parse(''.join(lines), filename=filename)
        except SyntaxError:
            raise original from None
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                name = replacements.get((node.end_lineno, node.end_col_offset))
                if name is not None:
                    node.attr = name
        return tree
