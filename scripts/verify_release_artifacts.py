#!/usr/bin/env python3
## @package scripts.verify_release_artifacts
#  Build, inspect and install the wheel and source archive for this checkout.

import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='pcresolve-release-') as directory:
        work = Path(directory)
        dist = work / 'dist'
        dist.mkdir()
        subprocess.run([sys.executable, '-m', 'build', '--wheel', '--sdist',
                        '--outdir', str(dist), str(root)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        wheels = list(dist.glob('*.whl'))
        sdists = list(dist.glob('*.tar.gz'))
        assert len(wheels) == len(sdists) == 1, (wheels, sdists)
        with zipfile.ZipFile(wheels[0]) as archive:
            names = archive.namelist()
            top_level = next(name for name in names if name.endswith('.dist-info/top_level.txt'))
            assert archive.read(top_level).decode().splitlines() == ['pcresolve']
            assert 'pcresolve/py.typed' in names
            assert 'pcresolve/flow/transfer/call_expression.py' in names
            assert 'pcresolve/flow/proofs/classes/_class_creation_calls.py' in names
            assert not any(name.startswith(('cross_file_analyzer/', 'path_scanner/',
                                            'single_file_analyzer/')) for name in names)
        with tarfile.open(sdists[0], 'r:gz') as archive:
            names = archive.getnames()
            assert any(name.endswith('/src/pcresolve/py.typed') for name in names)
            assert any(name.endswith('/src/pcresolve/flow/transfer/call_expression.py')
                       for name in names)
        environment = work / 'venv'
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ('Scripts/python.exe' if sys.platform == 'win32'
                                else 'bin/python')
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-deps', str(wheels[0])],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        code = (
            'import importlib, json, pcresolve; '
            'assert pcresolve.ProjectAnalyzer is importlib.import_module('
            '"pcresolve.ownership.analyzer").ProjectAnalyzer; '
            'assert importlib.import_module("pcresolve.single_file") is '
            'importlib.import_module("pcresolve.ownership.collect.single_file"); '
            'assert pcresolve.FlowAnalyzer'
        )
        subprocess.run([str(python), '-c', code], check=True)
        project = work / 'sample'
        project.mkdir()
        (project / 'main.py').write_text(
            'import json\ndef entry(value): return json.loads(value)\n', encoding='utf-8')
        ownership = subprocess.run([str(python), '-m', 'pcresolve', str(project), '--json'],
                                   check=True, capture_output=True, text=True)
        ownership_data = json.loads(ownership.stdout)
        assert ownership_data['schema_version'] == '1.0'
        flow = subprocess.run([str(python), '-m', 'pcresolve', str(project), '--value-flow',
                               '--entry', 'main:entry', '--depth', '2', '--json'],
                              check=True, capture_output=True, text=True)
        flow_data = json.loads(flow.stdout)
        assert flow_data['schema_version'] == 'flow-0.2'
        print('wheel, sdist, lazy imports, compatibility import and both installed CLIs passed')


if __name__ == '__main__':
    main()
