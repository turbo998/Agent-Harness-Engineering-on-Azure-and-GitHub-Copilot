const { buildApp } = require('./app');

const port = Number(process.env.PORT ?? 3000);
const app = buildApp();

app.listen(port, () => {
  console.log(`Ticket service listening on http://localhost:${port}`);
});
