import test from 'node:test';
import assert from 'node:assert/strict';
import { execute } from '../source/src/controller.mjs';
import { exampleConfig, createSyntheticApi, MemoryStore } from '../source/src/synthetic.mjs';
import { captureEnrollment, approveEnrollment } from '../source/src/enrollment.mjs';

// Original extension, not copied upstream tests. All controls use independent fixtures.
const START = '2030-01-02T00:00:00.000Z';
const USER = 'synthetic-user-a';
const KEY = `synthetic-workspace:${USER}`;
function barrier() {
  let signal, release;
  const reached = new Promise(resolve => { signal = resolve; });
  const released = new Promise(resolve => { release = resolve; });
  return { reached, release, async pause() { signal(); await released; } };
}
async function fixture(pattern = 'fixed_release') {
  let now = START;
  const config = exampleConfig({ now, pattern });
  config.cohort.userIds = [USER];
  Object.assign(config.policy, { startCap: '20', increment: '20', ceiling: '200' });
  const api = createSyntheticApi({ config, clock: () => now, initialCap: '10' });
  const captured = await captureEnrollment({ config, api, now });
  const enrollment = approveEnrollment(captured.enrollment, captured.hash, now);
  const store = new MemoryStore();
  let attempts = 0;
  const set = api.setCap.bind(api), restore = api.restore.bind(api);
  api.setCap = async (...args) => { attempts++; return set(...args); };
  api.restore = async (...args) => { attempts++; return restore(...args); };
  return { config, api, store, enrollment, attempts: () => attempts,
    setTime(value) { now = value; },
    run(options = {}) { return execute({ config, enrollment, api, store, clock: () => now, apply: true, ...options }); } };
}
const row = result => { assert.equal(result.results.length, 1); return result.results[0]; };
const ledger = s => structuredClone([...s.store.states]);
function manualOverride(s, value) {
  const rule = { type: 'limited', limit_amount: { amount: value, unit: 'credit' }, limit_expires_at: s.config.period.end };
  s.api.users[USER] = { ...s.api.users[USER],
    cap: { type: 'limited', amount: value, unit: 'credit', source: 'individual_override', expiresAt: s.config.period.end },
    settings: { ...s.api.users[USER].settings, override: [rule], effective: { limit: rule, source: { kind: 'individual_override' } } } };
}
async function committedButUnrecorded() {
  const s = await fixture();
  const save = s.store.putState.bind(s.store);
  let injected = false;
  s.store.putState = async (key, value) => {
    if (!injected && value.pending === null && value.last) {
      injected = true;
      throw Object.assign(new Error('POST_WRITE_SAVE_FAILED'), { code: 'POST_WRITE_SAVE_FAILED' });
    }
    return save(key, value);
  };
  const first = row(await s.run());
  assert.equal(first.code, 'POST_WRITE_SAVE_FAILED', 'fault must occur after external commit');
  assert.equal(s.api.writes.length, 1);
  assert.equal(s.api.users[USER].cap.amount, '20');
  assert.equal((await s.store.getState(KEY)).pending.amount, '20', 'durable intent survives failed completion save');
  return s;
}

test('C1 post-write save failure reconciles persisted intent without another PATCH', async () => {
  const s = await committedButUnrecorded();
  const attempts = s.attempts();
  const result = row(await s.run());
  assert.equal(result.status, 'reconciled', 'C1_BUSINESS_RECONCILE');
  assert.equal(s.attempts(), attempts, 'C1_BUSINESS_NO_REPATCH');
  assert.equal(s.api.writes.length, 1);
  const saved = await s.store.getState(KEY);
  assert.equal(saved.pending, null);
  assert.equal(saved.last.cap.amount, '20');
  assert.equal(saved.lastSlot, 0);
  // NC1: genuinely uncommitted intent must retry, not falsely reconcile.
  const control = await fixture();
  control.api.injectFault({ userId: USER, type: 'before' });
  assert.equal(row(await control.run()).code, 'SIMULATED_WRITE_FAILURE');
  const before = control.attempts();
  assert.equal(row(await control.run()).status, 'applied');
  assert.equal(control.attempts(), before + 1);
  assert.equal(control.api.writes.length, 1);
});

test('C2 pending preview leaves live settings and ledger unchanged (receipts permitted)', async () => {
  for (const fault of ['before', 'after']) {
    const s = await fixture();
    s.api.injectFault({ userId: USER, type: fault });
    assert.equal(row(await s.run()).status, 'attention');
    const states = ledger(s), live = structuredClone(s.api.users), attempts = s.attempts();
    const receipts = s.store.receipts.length;
    const result = row(await s.run({ apply: false }));
    assert.deepEqual(ledger(s), states, 'C2_BUSINESS_PREVIEW_LEDGER_IMMUTABLE');
    assert.deepEqual(s.api.users, live);
    assert.equal(s.attempts(), attempts);
    assert.equal(result.status, fault === 'after' ? 'pending_already_applied' : 'pending_retry_preview');
    assert.equal(s.store.receipts.length, receipts + 1, 'preview is not globally side-effect-free');
  }
  // NC2: independent apply=true counterpart is allowed to reconcile the ledger.
  const control = await fixture();
  control.api.injectFault({ userId: USER, type: 'after' });
  await control.run();
  const prior = ledger(control), attempts = control.attempts();
  assert.equal(row(await control.run()).status, 'reconciled');
  assert.notDeepEqual(ledger(control), prior);
  assert.equal(control.attempts(), attempts);
});

test('C3 manual edit after last controller read can be overwritten: no CAS claim', async () => {
  const s = await fixture();
  const gate = barrier(), set = s.api.setCap;
  let observedExpected;
  s.api.setCap = async (id, target) => {
    observedExpected = structuredClone(target.expectedSettings);
    await gate.pause(); // controller final read and lock assertion already completed
    return set(id, target); // synthetic adapter models unconditional endpoint write
  };
  const running = s.run();
  await Promise.race([gate.reached, running.then(() => { throw new Error('BARRIER_NOT_REACHED'); })]);
  try {
    assert.deepEqual(observedExpected, s.enrollment.members[0].before.settings);
    manualOverride(s, '77'); // manual administrator is not fenced by MemoryStore lock
    assert.equal(s.api.users[USER].cap.amount, '77');
  } finally { gate.release(); }
  assert.equal(row(await running).status, 'applied');
  assert.equal(s.api.users[USER].cap.amount, '20', 'C3_BUSINESS_MANUAL_EDIT_OVERWRITTEN');
  assert.equal(s.attempts(), 1);
  assert.equal((await s.store.getState(KEY)).last.cap.amount, '20');
  // NC3: move the SAME edit before final read; conflict must prevent any PATCH.
  const control = await fixture(), beforeRead = barrier(), read = control.api.readSnapshot;
  let reads = 0;
  control.api.readSnapshot = async id => { if (++reads === 2) await beforeRead.pause(); return read(id); };
  const pending = control.run();
  await Promise.race([beforeRead.reached, pending.then(() => { throw new Error('CONTROL_BARRIER_NOT_REACHED'); })]);
  try { manualOverride(control, '77'); } finally { beforeRead.release(); }
  assert.equal(row(await pending).code, 'FINAL_READ_CONFLICT');
  assert.equal(control.attempts(), 0);
  assert.equal(control.api.users[USER].cap.amount, '77');
});

test('C4 restore refuses current amount or inherited source conflict without PATCH', async () => {
  for (const conflict of ['current', 'source']) {
    const s = await fixture();
    assert.equal(row(await s.run()).status, 'applied');
    if (conflict === 'current') manualOverride(s, '77');
    else s.api.users[USER].settings.inherited.source = { kind: 'workspace_default', id: 'manual-source-replacement' };
    const live = structuredClone(s.api.users), states = ledger(s), attempts = s.attempts();
    const result = row(await s.run({ restore: true }));
    assert.equal(result.code, 'MANUAL_ADMIN_CHANGE_CONFLICT');
    assert.equal(s.attempts(), attempts, 'C4_BUSINESS_RESTORE_ZERO_PATCH');
    assert.deepEqual(s.api.users, live);
    assert.deepEqual(ledger(s), states);
  }
  // NC4: independent unchanged owned settings restore exactly, with one write.
  const control = await fixture();
  await control.run();
  const attempts = control.attempts();
  assert.equal(row(await control.run({ restore: true })).status, 'restored');
  assert.equal(control.attempts(), attempts + 1);
  assert.deepEqual(control.api.users[USER].settings, control.enrollment.members[0].before.settings);
});

test('C5 review expires during final read: pending intent survives, zero PATCH', async () => {
  const s = await fixture(), gate = barrier(), read = s.api.readSnapshot;
  let reads = 0;
  s.api.readSnapshot = async id => { if (++reads === 2) await gate.pause(); return read(id); };
  const running = s.run();
  await Promise.race([gate.reached, running.then(() => { throw new Error('BARRIER_NOT_REACHED'); })]);
  try { s.setTime('2030-01-02T00:15:00.001Z'); } finally { gate.release(); }
  assert.equal(row(await running).code, 'INITIAL_PREVIEW_EXPIRED_RECAPTURE');
  assert.equal(s.attempts(), 0, 'C5_BUSINESS_EXPIRED_ZERO_PATCH');
  assert.equal(s.api.writes.length, 0);
  assert.equal(s.api.users[USER].cap.amount, '10');
  assert.equal((await s.store.getState(KEY)).pending.amount, '20');
  // NC5: exact inclusive review boundary, independent fixture, remains eligible.
  const control = await fixture();
  control.setTime('2030-01-02T00:15:00.000Z');
  assert.equal(row(await control.run()).status, 'applied');
  assert.equal(control.attempts(), 1);
});

test('C6 duplicate slot cannot re-award changed observed headroom; next slot can', async () => {
  const s = await fixture('observed_headroom');
  assert.equal(row(await s.run()).status, 'applied');
  const originalCap = s.api.users[USER].cap.amount;
  s.api.users[USER].usage = '25';
  const states = ledger(s), attempts = s.attempts();
  const result = row(await s.run());
  assert.equal(s.attempts(), attempts, 'C6_BUSINESS_DUPLICATE_ZERO_PATCH');
  assert.equal(result.status, 'duplicate_slot');
  assert.equal(s.api.users[USER].cap.amount, originalCap);
  assert.deepEqual(ledger(s), states);
  // NC6: independent same usage at next slot must produce a real new award.
  const control = await fixture('observed_headroom');
  await control.run();
  const before = control.attempts();
  control.api.users[USER].usage = '25';
  control.setTime('2030-01-03T00:00:00.000Z');
  assert.equal(row(await control.run()).status, 'applied');
  assert.equal(control.attempts(), before + 1);
  assert.notEqual(control.api.users[USER].cap.amount, originalCap);
});
