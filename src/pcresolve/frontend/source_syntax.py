## @package pcresolve.frontend.source_syntax
#  Parse modern and archived sources.
#
#
#  Read-only AST parsing for modern and archived Python source.
#  为现代和历史 Python 源码提供只读语法树解析。



import ast
import io
import tokenize


## Parse source, retaining historical async/await attribute names and spans.
## 解析源码并保留历史 async/await 属性名称及源码位置。
#
#  @param text Original decoded source, never executed or modified on disk.
#  @param filename Diagnostic filename.
#  @return AST; unrelated syntax failures retain the original SyntaxError.
def parse_python_source(text, filename='<unknown>'):
    try:
        return ast.parse(text, filename=filename)
    except SyntaxError as original:
        # Rewrite only keyword attribute tokens, keeping their length and positions.
        # 只临时改写关键字属性 token，保持长度和位置不变。
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

        # Any unrelated failure must remain the original parser diagnostic.
        # 对无关语法错误保留原始解析诊断。
        if not replacements:
            raise original
        try:
            tree = ast.parse(''.join(lines), filename=filename)
        except SyntaxError:
            raise original from None

        # Restore the original attribute spelling using UTF-8 AST offsets.
        # 根据 AST 的 UTF-8 偏移恢复原始属性名。
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                name = replacements.get((node.end_lineno, node.end_col_offset))
                if name is not None:
                    node.attr = name
        return tree
