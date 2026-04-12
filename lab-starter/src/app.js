const express = require('express');
const {
  NotFoundError,
  ValidationError,
  createTicket,
  listTickets,
  updateTicketStatus
} = require('./ticketStore');

function sendKnownError(res, error) {
  if (error instanceof ValidationError) {
    res.status(400).json({ error: error.message });
    return true;
  }

  if (error instanceof NotFoundError) {
    res.status(404).json({ error: error.message });
    return true;
  }

  return false;
}

function buildApp() {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok' });
  });

  app.get('/tickets', (req, res) => {
    const items = listTickets({
      status: req.query.status,
      priority: req.query.priority
    });

    res.json({ count: items.length, items });
  });

  app.post('/tickets', (req, res, next) => {
    try {
      const ticket = createTicket(req.body ?? {});
      res.status(201).json(ticket);
    } catch (error) {
      if (!sendKnownError(res, error)) {
        next(error);
      }
    }
  });

  app.patch('/tickets/:id/status', (req, res, next) => {
    try {
      const ticket = updateTicketStatus(req.params.id, req.body?.status);
      res.json(ticket);
    } catch (error) {
      if (!sendKnownError(res, error)) {
        next(error);
      }
    }
  });

  return app;
}

module.exports = {
  buildApp
};
