## @package scripts.capture_platform_baseline
# Capture the fixed reference analysis on the current platform.

import argparse
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = 'b79a58fead5790aed50d01119e108cfff8bdae3f'
CORPUS = {
    'ground_truth/projects.json': '9c81fcd0f2faaa1d3b9513d5a7e63220ce34c981',
    'tests/fixtures/value_flow_matrix': '48d2eb5b2170f80fd3971d8e9d041c8cb5a7fbdb',
    'tests/fixtures/tested_projects': '9c17e82a30f427c51ef7b5c206abf66ace49af40',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for revision in (REFERENCE, 'HEAD'):
        for path, expected in CORPUS.items():
            actual = subprocess.check_output(
                ['git', 'rev-parse', revision + ':' + path], cwd=ROOT, text=True).strip()
            if actual != expected:
                raise ValueError('Corpus differs from frozen reference: %s:%s' % (revision, path))
    archive = subprocess.check_output(['git', 'archive', '--format=tar', REFERENCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='pcresolve-platform-baseline-') as directory:
        reference_root = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as bundle:
            if sys.version_info >= (3, 12):
                bundle.extractall(reference_root, filter='data')
            else:
                bundle.extractall(reference_root)
        # Use the same current fingerprint and path normalization on both revisions.
        comparator = (ROOT / 'scripts/compare_analysis_baseline.py').read_text(encoding='utf-8')
        old_import = 'from pcresolve.ownership.views import build_full_view'
        if comparator.count(old_import) != 1:
            raise ValueError('Unexpected comparator import')
        comparator = comparator.replace(old_import, 'from pcresolve.views import build_full_view')
        (reference_root / 'scripts/compare_analysis_baseline.py').write_text(comparator, encoding='utf-8')
        shutil.copy2(ROOT / 'scripts/evaluate_value_flow_matrix.py', reference_root / 'scripts')
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        environment = dict(os.environ, PYTHONPATH=str(reference_root / 'src'), PYTHONHASHSEED='0')
        subprocess.run([sys.executable, str(reference_root / 'scripts/compare_analysis_baseline.py'),
                        '--output', str(output)], cwd=reference_root, env=environment, check=True)
    report = json.loads(output.read_text(encoding='utf-8'))
    report['revision'] = REFERENCE
    report['corpus_git_objects'] = CORPUS
    report['reference_kind'] = 'fixed_git_reference_same_platform'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Captured platform baseline from fixed reference ' + REFERENCE)


if __name__ == '__main__':
    main()
