#!/usr/bin/env python3
## @package scripts.verify_release_artifacts
#  Build, inspect and install the wheel and source archive for this checkout.

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


_PYTHON_PATH_VARS = ('PYTHONPATH', 'PYTHONHOME', 'PYTHONUSERBASE', 'VIRTUAL_ENV')


def _clean_environment():
    environment = dict(os.environ)
    for name in _PYTHON_PATH_VARS:
        environment.pop(name, None)
    environment['PYTHONNOUSERSITE'] = '1'
    return environment


def _run(command, *, cwd=None, capture_output=True):
    try:
        return subprocess.run(command, cwd=cwd, env=_clean_environment(), check=True,
                              stdout=subprocess.PIPE if capture_output else None,
                              stderr=subprocess.STDOUT if capture_output else None,
                              text=True)
    except subprocess.CalledProcessError as error:
        output = error.stdout or error.stderr or ''
        raise RuntimeError('command failed (%s):\n%s' %
                           (' '.join(command), output[-12000:])) from error


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _preserve_artifact(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = _sha256(source)
    if destination.exists():
        if _sha256(destination) != digest:
            raise FileExistsError('Refusing to replace different artifact: %s' % destination)
    else:
        shutil.copy2(source, destination)
    return digest


def _inspect_wheel(wheel):
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        top_level = next(name for name in names if name.endswith('.dist-info/top_level.txt'))
        assert archive.read(top_level).decode().splitlines() == ['pcresolve']
        assert 'pcresolve/py.typed' in names
        assert 'pcresolve/flow/transfer/call_expression.py' in names
        assert 'pcresolve/flow/proofs/classes/_class_creation_calls.py' in names
        assert not any(name.startswith(('cross_file_analyzer/', 'path_scanner/',
                                        'single_file_analyzer/')) for name in names)


def _install_and_verify(wheel, environment, work):
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / ('Scripts/python.exe' if sys.platform == 'win32'
                            else 'bin/python')
    _run([str(python), '-m', 'pip', 'install', '--no-deps', '--no-index', str(wheel)])
    probe = (
        'import importlib, json, pathlib, sys, pcresolve; '
        'p=pathlib.Path(pcresolve.__file__).resolve(); '
        'assert pathlib.Path(sys.prefix).resolve() in p.parents, p; '
        'assert "pcresolve.flow" not in sys.modules; '
        'assert pcresolve.ProjectAnalyzer is importlib.import_module('
        '"pcresolve.ownership.analyzer").ProjectAnalyzer; '
        'assert importlib.import_module("pcresolve.single_file") is '
        'importlib.import_module("pcresolve.ownership.collect.single_file"); '
        'assert pcresolve.FlowAnalyzer; print(p)'
    )
    imported = _run([str(python), '-c', probe], cwd=work).stdout.strip().splitlines()[-1]
    project = work / ('sample-' + environment.name)
    project.mkdir()
    (project / 'main.py').write_text(
        'import json\ndef entry(value): return json.loads(value)\n', encoding='utf-8')
    ownership = _run([str(python), '-m', 'pcresolve', str(project), '--json'], cwd=work)
    ownership_data = json.loads(ownership.stdout)
    assert ownership_data['schema_version'] == '1.0'
    flow = _run([str(python), '-m', 'pcresolve', str(project), '--value-flow',
                 '--entry', 'main:entry', '--depth', '2', '--json'], cwd=work)
    flow_data = json.loads(flow.stdout)
    assert flow_data['schema_version'] == 'flow-0.2'
    return dict(python=str(python.resolve()), import_path=imported,
                ownership_cli='passed', flow_cli='passed')


def main():
    parser = argparse.ArgumentParser(description='Verify built PCResolve release artifacts')
    parser.add_argument('--report', type=Path, help='Write artifact hashes and verification metadata')
    parser.add_argument('--dist-dir', type=Path, required=True,
                        help='Directory that retains the exact artifacts verified here')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='pcresolve-release-') as directory:
        work = Path(directory)
        dist = work / 'dist'
        dist.mkdir()
        _run([sys.executable, '-m', 'build', '--wheel', '--sdist',
              '--outdir', str(dist), str(root)], cwd=work)
        wheels = list(dist.glob('*.whl'))
        sdists = list(dist.glob('*.tar.gz'))
        assert len(wheels) == len(sdists) == 1, (wheels, sdists)
        _inspect_wheel(wheels[0])
        with tarfile.open(sdists[0], 'r:gz') as archive:
            names = archive.getnames()
            assert any(name.endswith('/src/pcresolve/py.typed') for name in names)
            assert any(name.endswith('/src/pcresolve/flow/transfer/call_expression.py')
                       for name in names)
        extracted = work / 'sdist-source'
        extracted.mkdir()
        with tarfile.open(sdists[0], 'r:gz') as archive:
            if sys.version_info >= (3, 12):
                archive.extractall(extracted, filter='data')
            else:
                archive.extractall(extracted)
        sdist_roots = list(extracted.iterdir())
        assert len(sdist_roots) == 1 and sdist_roots[0].is_dir()
        sdist_dist = work / 'sdist-dist'
        sdist_dist.mkdir()
        _run([sys.executable, '-m', 'build', '--wheel',
              '--outdir', str(sdist_dist), str(sdist_roots[0])], cwd=work)
        sdist_wheels = list(sdist_dist.glob('*.whl'))
        assert len(sdist_wheels) == 1
        _inspect_wheel(sdist_wheels[0])
        wheel_install = _install_and_verify(wheels[0], work / 'wheel-venv', work)
        sdist_install = _install_and_verify(sdist_wheels[0], work / 'sdist-venv', work)
        destination = args.dist_dir.resolve()
        retained = [destination / 'checkout-wheel' / wheels[0].name,
                    destination / sdists[0].name,
                    destination / 'sdist-built-wheel' / sdist_wheels[0].name]
        hashes = [_preserve_artifact(source, target) for source, target in zip(
            (wheels[0], sdists[0], sdist_wheels[0]), retained)]
        if args.report:
            revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            source_status = subprocess.check_output(
                ['git', 'status', '--porcelain', '--untracked-files=all', '--',
                 'src/pcresolve', 'pyproject.toml', 'README.md'], cwd=root, text=True).strip()
            artifact_hashes = {
                str(path.relative_to(destination)): digest
                for path, digest in zip(retained, hashes)}
            report = dict(revision=revision, source_clean=not source_status,
                          source_status=source_status.splitlines(),
                          python=sys.version, platform=platform.platform(),
                          artifacts=artifact_hashes, dist_dir=str(destination),
                          installations={'wheel': wheel_install, 'sdist_built_wheel': sdist_install},
                          inherited_python_path_variables_removed=list(_PYTHON_PATH_VARS),
                          verified=True,
                          checks=['wheel build and retained hash',
                                  'sdist extraction and wheel rebuild',
                                  'wheel installation outside checkout',
                                  'sdist-built wheel installation outside checkout',
                                  'legacy import identity', 'lazy imports',
                                  'installed ownership CLI', 'installed value-flow CLI'])
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print('retained wheel and sdist-built wheel passed isolated import and CLI checks')


if __name__ == '__main__':
    main()
