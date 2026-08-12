// Test cases for rule: express-xss-request-to-response

const express = require("express");
const app = express();

app.get("/search", (req, res) => {
  const term = req.query.term;
  // ruleid: express-xss-request-to-response
  res.send("<p>You searched for: " + term + "</p>");
});

app.get("/greet", (req, res) => {
  // ruleid: express-xss-request-to-response
  res.write(req.params.name);
  res.end();
});

app.get("/safe-json", (req, res) => {
  // ok: express-xss-request-to-response
  res.json({ term: req.query.term });
});

app.get("/safe-escaped", (req, res) => {
  const term = escapeHtml(req.query.term);
  // ok: express-xss-request-to-response
  res.send("<p>You searched for: " + term + "</p>");
});
