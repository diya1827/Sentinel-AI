// Test cases for rule: dom-xss-source-to-sink

function renderFromUrl() {
  const params = new URLSearchParams(location.search);
  const name = params.get("name");

  // ruleid: dom-xss-source-to-sink
  document.getElementById("out").innerHTML = name;

  const hash = location.hash;
  // ruleid: dom-xss-source-to-sink
  document.write(hash);

  // ruleid: dom-xss-source-to-sink
  document.getElementById("box").insertAdjacentHTML("beforeend", location.href);

  // ruleid: dom-xss-source-to-sink
  eval(document.referrer);
}

function safeUsage() {
  const params = new URLSearchParams(location.search);
  const name = params.get("name");

  // ok: dom-xss-source-to-sink
  document.getElementById("out").textContent = name;

  // ok: dom-xss-source-to-sink
  document.getElementById("out").innerHTML = DOMPurify.sanitize(name);

  // ok: dom-xss-source-to-sink
  document.getElementById("out").innerHTML = "<b>static</b>";
}
