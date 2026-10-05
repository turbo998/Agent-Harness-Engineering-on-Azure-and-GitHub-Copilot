"""Offline built-in receipt checks only; never imports or executes ADK.
Requires already-installed jsonschema. No installs or network.
Default output: schema-validation.json next to this script (overwritten on success).
Use --output PATH for a writable destination, or --output - for stdout only.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from importlib.metadata import version


class CheckFailure(Exception):
    """A mechanical check failed; never includes fixture contents."""


def require(condition, message):
    if not condition:
        raise CheckFailure(message)


def paths(value, path=()):
    if isinstance(value, dict):
        yield path
        for k, x in value.items():
            yield from paths(x, path + (k,))
    elif isinstance(value, list):
        for k, x in enumerate(value):
            yield from paths(x, path + (k,))


def at(obj, path):
    for key in path:
        obj = obj[key]
    return obj


def reject_external_refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ('$ref', '$dynamicRef'):
                require(isinstance(item, str) and item.startswith('#'),
                        'external schema references are not allowed')
            reject_external_refs(item)
    elif isinstance(value, list):
        for item in value:
            reject_external_refs(item)


def validate_bundle(base):
    # All checks below remain real business checks even if this entry guard changes.
    require(sys.flags.optimize == 0, 'optimized Python is unsupported; unset PYTHONOPTIMIZE and omit -O/-OO')
    from jsonschema import Draft202012Validator

    names = ('receipt.schema.json', 'receipt.example.json', 'fixtures.json', 'validate_receipt.py')
    raw = {name: (base / name).read_bytes() for name in names}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()}
    schema = json.loads(raw['receipt.schema.json'])
    receipt = json.loads(raw['receipt.example.json'])
    fixtures = json.loads(raw['fixtures.json'])
    reject_external_refs(schema)
    Draft202012Validator.check_schema(schema)
    v = Draft202012Validator(schema)
    example_valid = v.is_valid(receipt)
    require(example_valid, 'built-in receipt failed schema validation')
    fixtures_hash_matches = hashes['fixtures.json'] == receipt['fixtures_sha256']
    require(fixtures_hash_matches, 'fixtures SHA-256 mismatch')
    fixture_ids_match = set(fixtures) == {c['case_id'] for c in receipt['cases']}
    require(fixture_ids_match, 'fixture case IDs mismatch')
    fixture_refs_match = all(c['fixture_ref'] == 'fixtures.json#/' + c['case_id'] for c in receipt['cases'])
    require(fixture_refs_match, 'fixture references mismatch')

    checks = []

    def rejected(bad, detail):
        actually_rejected = not v.is_valid(bad)
        require(actually_rejected, 'negative example was accepted: ' + detail['kind'])
        checks.append(dict(detail, rejected=actually_rejected))

    for path in paths(receipt):
        bad = copy.deepcopy(receipt)
        at(bad, path)['unapproved_extra'] = 'SYNTHETIC_NO_REAL_SECRET'
        rejected(bad, {'kind': 'reject_unknown_property', 'path': list(path)})
        for key in at(receipt, path):
            bad = copy.deepcopy(receipt)
            del at(bad, path)[key]
            rejected(bad, {'kind': 'reject_missing_required', 'path': list(path) + [key]})
    for index in range(len(receipt['cases'])):
        for value in [False, True, 1, -1, 0.5, '0', None]:
            bad = copy.deepcopy(receipt)
            bad['cases'][index]['attempts'] = value
            rejected(bad, {'kind': 'reject_invalid_attempts', 'case': index, 'value': value})
    for label, mutate in [
        ('runtime_claim', lambda x: x.update(execution_status='PASS')),
        ('gate_override', lambda x: x.update(execution_gate='GO')),
        ('numeric_boolean', lambda x: x.update(external_code_executed=0)),
        ('extra_case', lambda x: x['cases'].append(copy.deepcopy(x['cases'][0]))),
        ('missing_case', lambda x: x['cases'].pop()),
        ('duplicate_case', lambda x: x['cases'].__setitem__(1, copy.deepcopy(x['cases'][0]))),
        ('invented_observation', lambda x: x['cases'][0].update(observed={'result': 'PASS'})),
        ('changed_oracle', lambda x: x['cases'][0]['expected'].update(positive='changed')),
        ('wire_claim', lambda x: x['transport_observations'].update(ws_close='PASS')),
    ]:
        bad = copy.deepcopy(receipt)
        mutate(bad)
        rejected(bad, {'kind': label})
    return {
        'check_scope': 'LOCAL_RECEIPT_SCHEMA_ONLY',
        'validator': 'jsonschema',
        'validator_version': version('jsonschema'),
        'python_optimize': sys.flags.optimize,
        'example_valid': example_valid,
        'fixtures_hash_matches': fixtures_hash_matches,
        'fixture_ids_match': fixture_ids_match,
        'fixture_refs_match': fixture_refs_match,
        'negative_examples_rejected': sum(c['rejected'] for c in checks),
        'input_sha256': hashes,
        'upstream_executed': False,
        'adk_case_status': receipt['execution_status'],
        'checks': checks,
    }


def main():
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(base / 'schema-validation.json'))
    args = parser.parse_args()
    temp_path = None
    try:
        output = None if args.output == '-' else Path(args.output).resolve()
        require(output is None or output not in {p.resolve() for p in base.iterdir() if p.name != 'schema-validation.json'},
                'output must not overwrite bundle inputs')
        result = validate_bundle(base)
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if output is not None:
            # A failure preserves any prior result; it does not certify that old result.
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=output.parent,
                                             prefix='.schema-validation-', delete=False) as f:
                temp_path = Path(f.name)
                f.write(text)
            os.replace(temp_path, output)
            temp_path = None
            print(json.dumps({k: x for k, x in result.items() if k != 'checks'}, ensure_ascii=False))
        else:
            print(text, end='')
        return 0
    except Exception as exc:
        # Do not echo arbitrary model/fixture/error input or host paths.
        message = str(exc) if isinstance(exc, CheckFailure) else 'validation or output failed (' + type(exc).__name__ + ')'
        print(json.dumps({'check_scope': 'LOCAL_RECEIPT_SCHEMA_ONLY', 'validation_succeeded': False,
                          'error': message}), file=sys.stderr)
        return 1
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


if __name__ == '__main__':
    sys.exit(main())
