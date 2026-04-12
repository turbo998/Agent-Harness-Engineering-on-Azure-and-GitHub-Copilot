const test = require('node:test');
const assert = require('node:assert/strict');

const {
  ValidationError,
  createTicket,
  listTickets,
  resetTickets,
  updateTicketStatus
} = require('../src/ticketStore');

test.beforeEach(() => {
  resetTickets();
});

test('listTickets filters by status', () => {
  const openTickets = listTickets({ status: 'open' });

  assert.equal(openTickets.length, 1);
  assert.equal(openTickets[0].id, 'T-1001');
});

test('createTicket applies default owner and open status', () => {
  const created = createTicket({
    title: 'Warehouse dashboard flickers',
    customer: 'Litware',
    priority: 'high'
  });

  assert.equal(created.status, 'open');
  assert.equal(created.owner, 'unassigned');
  assert.equal(created.id, 'T-1004');
});

test('updateTicketStatus updates an existing ticket', () => {
  const updated = updateTicketStatus('T-1001', 'resolved');

  assert.equal(updated.status, 'resolved');
});

test('updateTicketStatus rejects unsupported status values', () => {
  assert.throws(
    () => updateTicketStatus('T-1001', 'done'),
    ValidationError
  );
});
