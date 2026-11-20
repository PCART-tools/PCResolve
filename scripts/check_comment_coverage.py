#!/usr/bin/env python3
## @package check_comment_coverage
#  Report mechanically detectable gaps in source Doxygen comments.
#  报告源码 Doxygen 注释中可机械检测的缺口。
#
#  A frozen baseline keeps existing gaps visible while failing only on new ones.
#  冻结基线保留已有缺口，仅对新增缺口返回失败。

import argparse
import ast
from collections import Counter, namedtuple
import json
from pathlib import Path
import re
import sys
import tokenize


## One mechanical comment gap located in a source file.
## 一处可机械检测的源码注释缺口。
#
#  @param path Source file, relative to the working directory when possible.
#  @param line One-based line number reported for the gap.
#  @param code Stable gap category used by counts and baselines.
#  @param detail Extra identity such as the undocumented parameter name.
Finding = namedtuple('Finding', ('path', 'line', 'code', 'detail'))


## Convert a discovered path into its stable report and baseline form.
## 将发现的路径转换为报告和基线使用的稳定形式。
#
#  @param path Source file path as discovered.
#  @return Path relative to the working directory, or absolute when outside it.
def display_path(path):
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        return resolved


## Find the contiguous comment block immediately before a definition or decorator.
## 查找定义或装饰器前紧邻的注释块。
#
#  @param lines Source lines without line endings.
#  @param node Class or function AST node.
#  @return Comment lines in source order.
def comment_block(lines, node):
    start = min([node.lineno] + [item.lineno for item in node.decorator_list]) - 1
    block = []
    while start and lines[start - 1].lstrip().startswith('#'):
        start -= 1
        block.append(lines[start])
    return list(reversed(block))


## Inspect one file and collect module, summary, parameter and return gaps.
## 检查单个文件并收集模块、摘要、参数和返回值缺口。
#
#  @param path Python source file to inspect.
#  @return Findings ordered by line and category.
def collect_findings(path):
    path = display_path(path)
    with tokenize.open(path) as stream:
        source = stream.read()
    lines = source.splitlines()
    tree = ast.parse(source, filename=str(path))
    findings = []
    start = 0
    if lines and lines[0].startswith('#!'):
        start = 1
    if start < len(lines) and start < 2 and re.match(
            r'^[ \t]*#.*?coding[:=][ \t]*[-\w.]+', lines[start]):
        start += 1
    package_pattern = r'^##\s+@package\s+[^\W\d]\w*(?:\.[^\W\d]\w*)*\s*$'
    if start >= len(lines) or not re.fullmatch(package_pattern, lines[start]):
        findings.append(Finding(
            path, start + 1, 'missing or invalid @package header', ''))
    else:
        header = []
        end = start + 1
        # A new Doxygen block starts a separate declaration comment.
        # 新的 Doxygen 注释块属于后续声明，而不是模块文件头。
        for line in lines[end:]:
            if not line.lstrip().startswith('#') or line.startswith('##'):
                break
            header.append(line)
            end += 1
        # Description must start in English, followed by a separate Chinese line.
        # 说明先以英文开始，再以独立的中文行说明。
        descriptions = [re.sub(r'^\s*#+\s*', '', line) for line in header]
        descriptions = [line for line in descriptions if line.strip()]
        first = descriptions[0] if descriptions else ''
        if not re.search(r'[A-Za-z]', first) or re.search(r'[\u4e00-\u9fff]', first):
            findings.append(Finding(
                path, start + 1, 'module description must start in English', ''))
        if not any(re.search(r'[\u4e00-\u9fff]', line) for line in descriptions[1:]):
            findings.append(Finding(
                path, start + 1, 'missing separate Chinese module description', ''))
        if end < len(lines) and lines[end].strip():
            findings.append(Finding(
                path, end + 1, 'missing blank line after module header', ''))
    if ast.get_docstring(tree, clean=False) is not None:
        findings.append(Finding(path, 1, 'module docstring is not a Doxygen comment', ''))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        block = comment_block(lines, node)
        summaries = [line.strip()[2:].strip() for line in block
                     if line.strip().startswith('##')]
        if not summaries or not re.search(r'[A-Za-z]', summaries[0]):
            findings.append(Finding(
                path, node.lineno, 'missing English Doxygen summary', ''))
        if len(summaries) < 2 or not re.search(r'[\u4e00-\u9fff]', summaries[1]):
            findings.append(Finding(
                path, node.lineno, 'missing Chinese Doxygen summary', ''))
        if isinstance(node, ast.ClassDef):
            continue

        # A standalone comment line separates the description from Doxygen tags.
        # 功能说明与 Doxygen 标签之间使用单独的注释空行。
        first_tag = next((index for index, line in enumerate(block)
                          if re.match(r'\s*#\s+@(param|return)\b', line)), None)
        if first_tag is not None and (first_tag == 0 or block[first_tag - 1].strip() != '#'):
            findings.append(Finding(
                path, node.lineno, 'missing comment separator before tags', ''))

        # Receivers are implicit; every other declared parameter needs a tag.
        # 接收者是隐式参数，其余声明参数均需标签。
        args = node.args
        parameters = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
        parameters += [arg for arg in (args.vararg, args.kwarg) if arg is not None]
        tags = set(re.findall(r'@param\s+(?:\*{0,2})(\w+)', '\n'.join(block)))
        for arg in parameters:
            if arg.arg not in ('self', 'cls') and arg.arg not in tags:
                findings.append(Finding(path, node.lineno, 'missing @param', arg.arg))
        if not any(re.search(r'@return\b', line) for line in block):
            findings.append(Finding(path, node.lineno, 'missing @return', ''))
    return sorted(findings, key=lambda finding: (finding.line, finding.code, finding.detail))


## Format one finding as a diagnostic line.
## 将一处缺口格式化为诊断行。
#
#  @param finding Finding produced by one inspection.
#  @return Diagnostic string with source location.
def format_finding(finding):
    message = finding.code if not finding.detail else finding.code + ' ' + finding.detail
    return f'{finding.path.as_posix()}:{finding.line}: {message}'


## Collect formatted diagnostics for one file.
## 收集单个文件的格式化诊断。
#
#  @param path Python source file to inspect.
#  @return Diagnostic strings with source locations.
def inspect_file(path):
    return [format_finding(finding) for finding in collect_findings(path)]


## Group findings into the per-file counts stored in a baseline.
## 将缺口按文件归并为基线中存储的计数。
#
#  @param findings Findings collected from one run.
#  @return Mapping of POSIX path to ordered gap-category counts.
def gap_counts(findings):
    grouped = {}
    for finding in findings:
        grouped.setdefault(finding.path.as_posix(), Counter())[finding.code] += 1
    return {path: dict(sorted(counts.items())) for path, counts in sorted(grouped.items())}


## Compare current counts with a frozen baseline.
## 将当前计数与冻结基线比较。
#
#  @param current Counts produced by the current run.
#  @param baseline Counts read from the baseline file.
#  @return New and resolved pairs as (path, code, baseline, current) rows.
def compare_baseline(current, baseline):
    new, resolved = [], []
    for path in sorted(set(current) | set(baseline)):
        now, before = current.get(path, {}), baseline.get(path, {})
        for code in sorted(set(now) | set(before)):
            current_count, baseline_count = now.get(code, 0), before.get(code, 0)
            if current_count > baseline_count:
                new.append((path, code, baseline_count, current_count))
            elif current_count < baseline_count:
                resolved.append((path, code, baseline_count, current_count))
    return new, resolved


## Write the current counts as a frozen baseline.
## 将当前计数写为冻结基线。
#
#  @param path Destination file; missing parent directories are created.
#  @param counts Counts produced by the current run.
#  @return None
def write_baseline(path, counts):
    path.parent.mkdir(parents=True, exist_ok=True)
    document = dict(checker='comment_coverage', files=counts)
    path.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')


## Check selected files or the complete package and print coverage diagnostics.
## 检查指定文件或整个包，并输出覆盖诊断。
#
#  @return Zero when no gap exists or no gap exceeds the baseline, otherwise one.
def main():
    parser = argparse.ArgumentParser(
        description='Report mechanically detectable gaps in source Doxygen comments.')
    parser.add_argument('paths', nargs='*', type=Path,
                        default=[Path('src/pcresolve')])
    parser.add_argument('--baseline', type=Path, metavar='PATH',
                        help='fail when the current gaps exceed this frozen baseline')
    parser.add_argument('--update-baseline', type=Path, metavar='PATH',
                        help='write the current gaps to this file and exit')
    args = parser.parse_args()
    if args.baseline is not None and args.update_baseline is not None:
        parser.error('--baseline and --update-baseline are mutually exclusive')
    absent = [str(path) for path in args.paths if not path.exists()]
    if absent:
        parser.error('no such file or directory: ' + ', '.join(absent))
    paths = sorted({file.resolve() for path in args.paths
                    for file in (path.rglob('*.py') if path.is_dir() else [path])})
    findings = [finding for path in paths for finding in collect_findings(path)]
    summary = f'{len(paths)} files checked; {len(findings)} gaps'
    # Full diagnostics are for local use; a baseline run prints only the diff.
    # 全量诊断供本地使用；基线条目运行时只输出差异。
    if args.baseline is None and args.update_baseline is None:
        for finding in findings:
            print(format_finding(finding))
    print(summary)
    counts = gap_counts(findings)
    if args.update_baseline is not None:
        write_baseline(args.update_baseline, counts)
        print(f'baseline written: {args.update_baseline}')
        return 0
    if args.baseline is None:
        return 1 if findings else 0
    try:
        baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
    except OSError as error:
        parser.error(str(error))
    except ValueError as error:
        parser.error(f'{args.baseline}: {error}')
    new, resolved = compare_baseline(counts, baseline.get('files', {}))
    for path, code, before, after in new:
        print(f'{path}: {code}: {before} -> {after} (new)')
    for path, code, before, after in resolved:
        print(f'{path}: {code}: {before} -> {after} (fixed)')
    if new:
        print(f'{len(new)} gap groups exceed {args.baseline}')
        return 1
    if resolved:
        print(f'{len(resolved)} gap groups improved; refresh {args.baseline} '
              'with --update-baseline')
    else:
        print(f'no new gaps against {args.baseline}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
