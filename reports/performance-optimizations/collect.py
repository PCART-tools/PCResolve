## @package reports.performance_optimizations.collect
#  Collect compact measurements and compare complete output fingerprints.

import argparse
import json
from pathlib import Path


## Collect successful runs and retain failed/timeout statuses explicitly.
#  @return None.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'baseline_commit': '25e58e21df14c24a2ade5646cdffdd90c13abfa7',
              'raw_directory': str(args.raw), 'groups': {}}
    for group in ('paired', 'batches', 'scope', 'flow'):
        manifest = args.raw / group / 'results.json'
        if not manifest.exists():
            continue
        records = []
        for row in json.loads(manifest.read_text(encoding='utf-8')):
            record = {key: value for key, value in row.items() if key != 'metrics'}
            metrics = row.get('metrics')
            if metrics:
                record['runs'] = metrics['runs']
                record['python'] = metrics['python']
                record['platform'] = metrics['platform']
                if group == 'batches':
                    prior = args.audit / 'batches' / row['name'] / 'metrics.json'
                    if prior.exists():
                        old = json.loads(prior.read_text(encoding='utf-8'))
                        record['matches_prior_payload_hash'] = (
                            [r['sha256'] for r in metrics['runs']] ==
                            [r['sha256'] for r in old['runs']])
                        record['matches_prior_full_json'] = all(
                            json.loads((Path(row['directory']) / ('output-%s.json' % number)).read_text(
                                encoding='utf-8')) ==
                            json.loads((prior.parent / ('output-%s.json' % number)).read_text(
                                encoding='utf-8'))
                            for number in range(len(metrics['runs'])))
            else:
                events = Path(row['directory']) / 'events.jsonl'
                if events.exists():
                    captured = [json.loads(line) for line in events.read_text(
                        encoding='utf-8').splitlines() if line.strip()]
                    record['last_events'] = captured[-3:]
                    finished = next((event for event in captured
                                     if event['kind'] == 'end' and event['phase'] == 'analysis'), None)
                    record['analysis_completed'] = finished is not None
                    if finished:
                        record['analysis'] = finished
            records.append(record)
        report['groups'][group] = records
    paired = report['groups'].get('paired', [])
    report['paired_fingerprints'] = {
        prefix: {'complete': len(rows) == 4 and all(row['status'] == 'ok' for row in rows),
                 'equal': len({run['sha256'] for row in rows
                               for run in row.get('runs', [])}) == 1}
        for prefix in ('step2-2-longest', 'step2-2-timeout')
        for rows in [[row for row in paired if row['name'].startswith(prefix)]]}
    flow = report['groups'].get('flow', [])
    report['flow_fingerprints_equal'] = (len(flow) == 2
        and all(row['status'] == 'ok' and len(row.get('runs', [])) == 3 for row in flow) and
        len({run['snapshot_sha256'] for row in flow for run in row.get('runs', [])}) == 1)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
