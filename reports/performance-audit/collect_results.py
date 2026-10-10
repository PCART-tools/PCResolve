## @package reports.performance_audit.collect_results
#  Gather compact, reproducible measurements; large output JSON stays in the audit directory.
import json
import os
from pathlib import Path
import pstats

HERE = Path(__file__).resolve().parent
RAW = Path(os.environ['TEMP']) / 'pcresolve-performance-audit'
result = {'commit': '25e58e21df14c24a2ade5646cdffdd90c13abfa7', 'raw_directory': str(RAW),
          'ownership': {}, 'flow': {}, 'manifests': {}, 'profiles': {}}
for group in ('batches', 'controlled', 'profiles', 'scope', 'small-probes'):
    for path in (RAW / group).glob('*/metrics.json'):
        item = json.loads(path.read_text(encoding='utf-8'))
        item.setdefault('python_hash_seed', 'random')
        item.pop('events', None)
        item['metrics_path'] = str(path)
        result['ownership'][group + '/' + path.parent.name] = item
    manifest = RAW / group / 'manifest.json'
    if manifest.exists():
        entries = json.loads(manifest.read_text(encoding='utf-8'))
        for record in entries:
            if record['status'] == 'timeout':
                events_path = Path(record['directory']) / 'events.jsonl'
                events = [json.loads(line) for line in events_path.read_text().splitlines()]
                pending = {}
                for event in events:
                    if event['kind'] == 'begin':
                        pending[event['phase']] = event
                    else:
                        pending.pop(event['phase'], None)
                record['unfinished_phases'] = pending
                record['last_completed_event'] = next((event for event in reversed(events)
                                                        if event['kind'] == 'end'), None)
        result['manifests'][group] = entries
for path in (RAW / 'flow').glob('*.json'):
    if path.name.startswith('manifest'):
        continue
    item = json.loads(path.read_text(encoding='utf-8'))
    if item['runs']:
        item['source_file_count'] = len(item.pop('source_files'))
        item['metrics_path'] = str(path)
        result['flow'][path.stem] = item
profiles = list(RAW.glob('profiles/*/analysis.pstats'))
profiles += list(RAW.glob('small-probes/*/analysis.pstats'))
profiles += list((RAW / 'flow').glob('*.analyze-1.prof'))
old = RAW.parent / 'pcresolve-perf-followup/after-profile/step2-2-normal.pstats'
if old.exists():
    profiles.append(old)
for path in profiles:
    stats = pstats.Stats(str(path))
    entries = []
    for (file, line, function), (primitive, calls, own, total, callers) in stats.stats.items():
        entries.append({'file': file, 'line': line, 'function': function,
                        'primitive_calls': primitive, 'calls': calls,
                        'self_seconds': own, 'cumulative_seconds': total})
    result['profiles'][str(path)] = {'total_calls': stats.total_calls, 'total_seconds': stats.total_tt,
        'by_cumulative': sorted(entries, key=lambda x: x['cumulative_seconds'], reverse=True)[:60],
        'by_self': sorted(entries, key=lambda x: x['self_seconds'], reverse=True)[:35]}
(HERE / 'results.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')

rows = ['数据方法及限制见 [README.md](README.md)。计时存在明显环境波动；消融中的差值不代表稳定优化收益，命中 0 次的对照也有大幅差异。峰值内存包括探针构造和写出完整 JSON。', '',
        '| 样本 | 文件 | 调用点 | 分析 wall / CPU 秒 | visit CPU | get_calls CPU | provenance CPU | 输出 CPU | JSON MiB | 峰值 RSS MiB |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for key, item in result['ownership'].items():
    if not key.startswith('batches/'):
        continue
    run = item['runs'][0]
    p = run['phases']
    output = sum(p[x]['cpu'] for x in ('full_view', 'json_encode', 'json_write'))
    rows.append('| %s | %s | %s | %.3f / %.3f | %.3f | %.3f | %.3f | %.3f | %.2f | %.1f |' % (
        key.split('/')[1].rsplit('-', 1)[0], run['modules'], run['calls'],
        p['analysis']['wall'], p['analysis']['cpu'], p['single_file_visit']['cpu'],
        p['get_calls']['cpu'], p['_build_symbol_provenance']['cpu'], output,
        run['output_bytes'] / 2**20, run['memory']['peak_rss'] / 2**20))
rows += ['', '| Flow 样本 | 源文件 | 首次 analyze / index wall 秒 | 同实例再次 analyze / index wall 秒 | functions / calls（首次） |',
         '|---|---:|---:|---:|---:|']
for name, item in result['flow'].items():
    if len(item['runs']) < 2 or item['profile_enabled']:
        continue
    a, b = item['runs'][:2]
    rows.append('| %s | %s | %.4f / %.4f | %.4f / %.4f | %s / %s |' % (
        name, item['source_file_count'], a['analyze']['wall_seconds'], a['index']['wall_seconds'],
        b['analyze']['wall_seconds'], b['index']['wall_seconds'], a['function_count'], a['call_count']))
rows += ['', '| 额外范围测试 | 状态 | 分析 wall / CPU 秒 | 最后所在阶段 |',
         '|---|---|---:|---|']
for record in result['manifests'].get('scope', []):
    item = result['ownership'].get('scope/' + record['name'])
    if item:
        phase = item['runs'][0]['phases']['analysis']
        times = '%.3f / %.3f' % (phase['wall'], phase['cpu'])
    else:
        times = '进程在 %ss 截止' % record.get('limit_seconds', '?')
    pending = ', '.join(key for key in record.get('unfinished_phases', {}) if key != 'analysis')
    rows.append('| %s | %s | %s | %s |' % (record['name'], record['status'], times, pending or '完成'))
rows += ['', '| 空实参短路实验 | 首次 CPU：原版 → 实验 | 再次 CPU：原版 → 实验 | 首次计时差（非稳定收益） | 跳过逃逸扫描次数（两次合计） | JSON 指纹均相同 |',
         '|---|---:|---:|---:|---:|---|']
for key, item in result['ownership'].items():
    if not key.startswith('controlled/') or not key.endswith('-baseline'):
        continue
    other = result['ownership'].get(key[:-len('baseline')] + 'empty-arguments')
    if not other:
        continue
    before = [r['phases']['analysis']['cpu'] for r in item['runs']]
    after = [r['phases']['analysis']['cpu'] for r in other['runs']]
    hashes = {r['sha256'] for r in item['runs'] + other['runs']}
    rows.append('| %s | %.3f → %.3f | %.3f → %.3f | %.1f%% | %s | %s |' % (
        key.split('/')[1].removesuffix('-baseline').rsplit('-', 1)[0], before[0], after[0], before[1], after[1],
        (1 - after[0]/before[0])*100, other['skipped_escape_queries'], len(hashes) == 1))
(HERE / 'tables.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
print(json.dumps({'ownership_runs': len(result['ownership']), 'flow_cases': len(result['flow']),
                  'profiles': len(result['profiles'])}))
