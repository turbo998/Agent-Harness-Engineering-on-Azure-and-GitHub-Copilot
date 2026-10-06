"""Historical baseline: 42 PASS normal/-O; new revision pairs: NOT_RUN."""
import copy
import hashlib
import json
import pathlib
import tempfile
import unittest
from binding import BODY_LIMIT, check, check_files


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.raw = b'heading\nexact claim\n'
        (self.root / 'body.txt').write_bytes(self.raw)
        self.rev = 'a' * 40
        self.url = 'https://example.org/repo/' + self.rev + '/source.txt'
        self.r = dict(id='r1', capture='body.txt', sha256=hashlib.sha256(self.raw).hexdigest(),
                      method='GET', status=200, transport_exit=0, requested_url=self.url,
                      final_url=self.url, revision=self.rev, kind='main_source', scope='full')
        self.m = dict(version='binding-v1', requested_allowlist=[self.url],
                      final_allowlist=[self.url], receipts=[self.r])
        self.c = dict(version='binding-v1', fact_id='f1', receipt_id='r1',
                      revision=self.rev, kind='main_source', line_start=2, line_end=2,
                      excerpt='exact claim')

    def run_case(self, status, reason):
        out = check(str(self.root), json.dumps(self.m).encode(), json.dumps(self.c).encode())
        self.assertEqual((out['status'], out['reason']), (status, reason))
        self.assertIs(out['fact_authorized'], False)
        self.assertIs(out['fetch_authenticated'], False)
        self.assertIs(out['runtime_verified'], False)
        return out

    def test_control_main_not_release(self):
        self.assertEqual(self.run_case('MATCH', 'local_consistency_only')['evidence_layer'], 'main_source')

    def test_release_stays_declaration(self):
        self.r['kind'] = self.c['kind'] = 'release_body'
        self.assertEqual(self.run_case('MATCH', 'local_consistency_only')['evidence_layer'], 'release_body')

    def test_hash_tamper(self):
        (self.root / 'body.txt').write_bytes(b'heading\nother claim\n')
        self.run_case('REJECT', 'sha256_mismatch')

    def test_head_not_get(self):
        self.r['method'] = 'HEAD'
        self.run_case('REJECT', 'get_unsuccessful')

    def test_http403(self):
        self.r['status'] = 403
        self.run_case('REJECT', 'get_unsuccessful')

    def test_partial206(self):
        self.r['status'] = 206
        self.run_case('REJECT', 'get_unsuccessful')

    def test_transport_failure_with200(self):
        self.r['transport_exit'] = 28
        self.run_case('REJECT', 'get_unsuccessful')

    def test_requested_not_allowed(self):
        self.r['requested_url'] = 'https://other.example/source'
        self.run_case('REJECT', 'requested_denied')

    def test_redirect_escape(self):
        self.r['final_url'] = 'https://evil.example/source'
        self.run_case('REJECT', 'final_denied')

    def test_cross_host_redirect_explicitly_allowed(self):
        self.r['final_url'] = self.url.replace('example.org', 'mirror.example')
        self.m['final_allowlist'].append(self.r['final_url'])
        self.run_case('MATCH', 'local_consistency_only')

    def test_url_credentials(self):
        self.r['final_url'] = 'https://user@example.org/source'
        self.run_case('REJECT', 'url')

    def test_url_percent_ambiguity(self):
        self.r['final_url'] = self.url + '%2f'
        self.run_case('REJECT', 'url')

    def test_exact_whitespace(self):
        self.c['excerpt'] += ' '
        self.run_case('REJECT', 'excerpt_mismatch')

    def test_line_not_substring(self):
        self.c['excerpt'] = 'claim'
        self.run_case('REJECT', 'excerpt_mismatch')

    def test_wrong_line(self):
        self.c['line_start'] = self.c['line_end'] = 1
        self.run_case('REJECT', 'excerpt_mismatch')

    def test_bool_line(self):
        self.c['line_start'] = True
        self.run_case('REJECT', 'line_type')

    def test_status_string(self):
        self.r['status'] = '200'
        self.run_case('REJECT', 'status_type')

    def test_bad_utf8_even_with_matching_hash(self):
        raw = b'heading\n\xff\n'
        (self.root / 'body.txt').write_bytes(raw)
        self.r['sha256'] = hashlib.sha256(raw).hexdigest()
        self.run_case('REJECT', 'input_error')

    def test_revision_mismatch(self):
        self.c['revision'] = 'b' * 40
        self.run_case('REJECT', 'identity_mismatch')

    def test_mutable_url_not_pin(self):
        self.r['final_url'] = self.url.replace(self.rev, 'main')
        self.m['final_allowlist'] = [self.r['final_url']]
        self.run_case('REJECT', 'revision_url_mismatch')

    def revision_segment_pair(self, prefix, suffix):
        # NOT_RUN: isolate each endpoint; both exact allowlists remain valid.
        for endpoint in ('requested_url', 'final_url'):
            with self.subTest(endpoint=endpoint, prefix=prefix, suffix=suffix):
                self.r['requested_url'] = self.r['final_url'] = self.url
                segments = [part for part in (prefix, self.rev, suffix) if part]
                good = 'https://example.org/repo/' + '/'.join(segments) + '/source.txt'
                bad = 'https://example.org/repo/' + prefix + self.rev + suffix + '/source.txt'
                self.assertIn(self.rev, bad)
                self.assertNotIn(self.rev, bad.split('/'))
                for candidate, status, reason in (
                    (good, 'MATCH', 'local_consistency_only'),
                    (bad, 'REJECT', 'revision_url_mismatch'),
                ):
                    with self.subTest(candidate=candidate):
                        self.r[endpoint] = candidate
                        self.m['requested_allowlist'] = [self.r['requested_url']]
                        self.m['final_allowlist'] = [self.r['final_url']]
                        out = self.run_case(status, reason)
                        # Proves the negative reached the revision gate, not an earlier gate.
                        self.assertIs(out['byte_binding'], True)
                        self.assertEqual(out['evidence_layer'], 'main_source')

    def test_revision_segment_prefix_pair(self):
        self.revision_segment_pair('prefix-', '')

    def test_revision_segment_suffix_pair(self):
        self.revision_segment_pair('', '-suffix')

    def test_revision_segment_both_sides_pair(self):
        self.revision_segment_pair('prefix-', '-suffix')

    def test_source_cannot_upgrade_to_release(self):
        self.c['kind'] = 'release_body'
        self.run_case('REJECT', 'identity_mismatch')

    def test_missing_revision(self):
        self.r['revision'] = self.c['revision'] = ''
        self.run_case('UNVERIFIED', 'revision_unpinned')

    def test_excerpt_projection_not_full_capture(self):
        self.r['scope'] = 'excerpt'
        self.assertTrue(self.run_case('UNVERIFIED', 'excerpt_only')['byte_binding'])

    def test_metadata_not_feature(self):
        self.r['kind'] = self.c['kind'] = 'release_metadata'
        self.run_case('UNVERIFIED', 'signal_only')

    def test_duplicate_json_key(self):
        raw = json.dumps(self.c).encode().replace(b'"fact_id": "f1"', b'"fact_id":"f1","fact_id":"f2"')
        out = check(str(self.root), json.dumps(self.m).encode(), raw)
        self.assertEqual(out['reason'], 'duplicate_key')

    def test_duplicate_receipt_id(self):
        self.m['receipts'].append(copy.deepcopy(self.r))
        self.run_case('REJECT', 'receipt_identity')

    def test_unknown_claim_policy(self):
        self.c['final_allowlist'] = ['https://evil.example/']
        self.run_case('REJECT', 'schema')

    def test_traversal(self):
        self.r['capture'] = '../body.txt'
        self.run_case('REJECT', 'path')

    def test_absolute_path(self):
        self.r['capture'] = '/etc/passwd'
        self.run_case('REJECT', 'path')

    def test_leaf_symlink(self):
        (self.root / 'link.txt').symlink_to('body.txt')
        self.r['capture'] = 'link.txt'
        self.run_case('REJECT', 'input_error')

    def test_directory_symlink(self):
        (self.root / 'alias').symlink_to(self.root, target_is_directory=True)
        self.r['capture'] = 'alias/body.txt'
        self.run_case('REJECT', 'input_error')

    def test_body_budget(self):
        (self.root / 'body.txt').write_bytes(b'x' * (BODY_LIMIT + 1))
        self.run_case('REJECT', 'file_budget')

    def test_json_budget(self):
        out = check(str(self.root), b' ' * 65537, b'{}')
        self.assertEqual(out['reason'], 'json_budget')

    def test_file_api_duplicate_manifest(self):
        (self.root / 'm.json').write_bytes(b'{"version":1,"version":2}')
        (self.root / 'c.json').write_text(json.dumps(self.c))
        self.assertEqual(check_files(str(self.root), 'm.json', 'c.json')['reason'], 'duplicate_key')

    def test_root_symlink(self):
        (self.root / 'alias').symlink_to(self.root, target_is_directory=True)
        out = check(str(self.root / 'alias'), json.dumps(self.m).encode(), json.dumps(self.c).encode())
        self.assertEqual((out['status'], out['reason']), ('REJECT', 'input_error'))

    def test_hardlink(self):
        import os
        os.link(self.root / 'body.txt', self.root / 'hard.txt')
        self.run_case('REJECT', 'file_type')

    def test_nan(self):
        out = check(str(self.root), b'{"version":NaN}', b'{}')
        self.assertEqual(out['reason'], 'json_constant')

    def test_missing_capture(self):
        (self.root / 'body.txt').unlink()
        self.run_case('REJECT', 'input_error')

    def test_unused_receipt_path_still_rejected(self):
        other = copy.deepcopy(self.r)
        other.update(id='other', capture='../outside')
        self.m['receipts'].append(other)
        self.run_case('REJECT', 'path')

    def test_nested_duplicate_json_key(self):
        raw = json.dumps(self.m).encode().replace(b'"method": "GET"', b'"method":"GET","method":"HEAD"')
        out = check(str(self.root), raw, json.dumps(self.c).encode())
        self.assertEqual(out['reason'], 'duplicate_key')

    def test_real_derived_public_fixtures_remain_unverified(self):
        root = pathlib.Path(__file__).absolute().parent
        for name in ('codex', 'claude'):
            with self.subTest(name=name):
                out = check_files(str(root), f'fixtures/{name}.manifest.json', f'fixtures/{name}.claim.json')
                self.assertEqual((out['status'], out['reason']), ('UNVERIFIED', 'excerpt_only'))
                self.assertTrue(out['byte_binding'])
                self.assertFalse(out['fetch_authenticated'])

    def test_lf_no_crlf_normalization(self):
        raw = b'heading\r\nexact claim\r\n'
        (self.root / 'body.txt').write_bytes(raw)
        self.r['sha256'] = hashlib.sha256(raw).hexdigest()
        self.run_case('REJECT', 'excerpt_mismatch')


if __name__ == '__main__':
    unittest.main()
