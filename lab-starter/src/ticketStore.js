class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ValidationError';
  }
}

class NotFoundError extends Error {
  constructor(message) {
    super(message);
    this.name = 'NotFoundError';
  }
}

const VALID_STATUSES = new Set(['open', 'in_progress', 'resolved']);
const VALID_PRIORITIES = new Set(['low', 'medium', 'high']);

const initialTickets = [
  {
    id: 'T-1001',
    title: 'Login error during shift handover',
    customer: 'Fabrikam Retail',
    priority: 'high',
    status: 'open',
    owner: 'Avery',
    createdAt: '2026-02-10T09:00:00.000Z'
  },
  {
    id: 'T-1002',
    title: 'Weekly report export is slow',
    customer: 'Contoso Manufacturing',
    priority: 'medium',
    status: 'in_progress',
    owner: 'Jordan',
    createdAt: '2026-02-11T11:15:00.000Z'
  },
  {
    id: 'T-1003',
    title: 'Password reset email not received',
    customer: 'Northwind Services',
    priority: 'low',
    status: 'resolved',
    owner: 'Kai',
    createdAt: '2026-02-12T14:40:00.000Z'
  }
];

let tickets = [];

function cloneTicket(ticket) {
  return { ...ticket };
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function resetTickets() {
  tickets = initialTickets.map(cloneTicket);
}

function listTickets(filters = {}) {
  let results = tickets;

  if (filters.status) {
    results = results.filter((ticket) => ticket.status === filters.status);
  }

  // TODO(workshop): add priority filtering and tests.

  return results.map(cloneTicket);
}

function createTicket(input) {
  const nextId = `T-${1000 + tickets.length + 1}`;

  // TODO(workshop): validate title, customer, and priority.
  const ticket = {
    id: nextId,
    title: normalizeText(input.title),
    customer: normalizeText(input.customer),
    priority: normalizeText(input.priority) || 'medium',
    status: 'open',
    owner: normalizeText(input.owner) || 'unassigned',
    createdAt: new Date().toISOString()
  };

  tickets.push(ticket);
  return cloneTicket(ticket);
}

function updateTicketStatus(id, status) {
  const normalizedStatus = normalizeText(status);
  if (!VALID_STATUSES.has(normalizedStatus)) {
    throw new ValidationError(
      `Status must be one of: ${Array.from(VALID_STATUSES).join(', ')}`
    );
  }

  const ticket = tickets.find((item) => item.id === id);
  if (!ticket) {
    throw new NotFoundError(`Ticket ${id} was not found.`);
  }

  ticket.status = normalizedStatus;
  return cloneTicket(ticket);
}

resetTickets();

module.exports = {
  NotFoundError,
  ValidationError,
  VALID_PRIORITIES,
  VALID_STATUSES,
  createTicket,
  listTickets,
  resetTickets,
  updateTicketStatus
};
