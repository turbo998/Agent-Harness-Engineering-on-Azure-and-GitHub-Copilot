#!/usr/bin/env python3
"""Offline, stdlib-only byte validator/copier. Does not run any downloaded code.
Usage: python3 restager.py SNAPSHOT FRESH_DESTINATION
SNAPSHOT contains src/*.mjs and LICENSE.upstream from SOURCE-RETRIEVAL.md.
Extra snapshot files are ignored, never copied. Run only in a trusted local
filesystem without concurrent writers; this is not a hostile-filesystem sandbox.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

COMMIT = '0eac1447d4e24d06e47c459ca5e98f248b9413cf'
MODULES = {'src/' + name + '.mjs' for name in (
    'admin-api', 'controller', 'enrollment', 'policy', 'renewal', 'selection', 'synthetic')}


def checked_bytes(root, relative, record):
    path = root
    for component in Path(relative).parts:
        if component in ('.', '..') or Path(relative).is_absolute():
            raise ValueError('unsafe relative path')
        path = path / component
        if path.is_symlink():
            raise ValueError('symlinks are not accepted: ' + relative)
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('not a regular file: ' + relative)
    data = path.read_bytes()
    if len(data) != record['size_bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
        raise ValueError('size/SHA-256 mismatch: ' + relative)
    if 'git_blob_sha1' in record:
        blob = b'blob ' + str(len(data)).encode('ascii') + b'\0' + data
        if hashlib.sha1(blob).hexdigest() != record['git_blob_sha1']:
            raise ValueError('Git blob mismatch: ' + relative)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parent
    snapshot = args.snapshot.resolve(strict=True)
    if not snapshot.is_dir():
        raise ValueError('snapshot must be a directory')
    # Parent must exist. Never replace, merge with, or remove an existing path.
    destination = args.destination.parent.resolve(strict=True) / args.destination.name
    if os.path.lexists(destination):
        raise ValueError('destination must not exist')
    for protected in (bundle, snapshot):
        if destination == protected or protected in destination.parents:
            raise ValueError('destination must be outside bundle and snapshot')
    lock = json.loads((bundle / 'source-lock.json').read_text(encoding='utf-8'))
    records = lock['source_modules']
    if lock['commit'] != COMMIT or len(records) != 7 or {r['path'] for r in records} != MODULES:
        raise ValueError('unexpected commit/module set')
    if lock['test']['path'] != 'test/controller.extensions.test.mjs':
        raise ValueError('unexpected test path')
    if lock['upstream_license']['path'] != 'LICENSE.upstream':
        raise ValueError('unexpected license path')
    # Verify everything before creating output; copy the same bytes just verified.
    payload = {'source/' + r['path']: checked_bytes(snapshot, r['path'], r) for r in records}
    payload['source/LICENSE'] = checked_bytes(snapshot, 'LICENSE.upstream', lock['upstream_license'])
    payload[lock['test']['path']] = checked_bytes(bundle, lock['test']['path'], lock['test'])
    destination.mkdir(mode=0o755, exist_ok=False)
    destination.chmod(0o755)
    for relative, data in payload.items():
        target = destination / relative
        target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        for parent in target.parents:
            if parent == destination:
                break
            parent.chmod(0o755)
        with target.open('xb') as stream:
            stream.write(data)
        target.chmod(0o644)
        if target.read_bytes() != data:
            raise OSError('post-copy byte mismatch: ' + relative)
    print('STAGED_ONLY: 7 source modules, upstream license, unchanged six-case test; no execution')


if __name__ == '__main__':
    main()
