from fastapi.responses import HTMLResponse

# ruff: noqa: E501

ADMIN_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Secret Vault</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #17202a; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px; }
    section { background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px; margin: 14px 0; }
    label { display: block; font-weight: 650; margin: 10px 0 5px; }
    input, textarea { box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid #b9c1ce; border-radius: 6px; }
    button { margin-top: 12px; padding: 10px 14px; border: 0; border-radius: 6px; background: #1459b8; color: white; cursor: pointer; }
    button.secondary { background: #58616f; }
    pre { white-space: pre-wrap; background: #111827; color: #e5e7eb; border-radius: 6px; padding: 12px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
  </style>
</head>
<body>
<main>
  <h1>Secret Vault Admin</h1>
  <section>
    <label>Admin token</label>
    <input id="adminToken" type="password" autocomplete="off">
    <button onclick="status()">Status</button>
    <button class="secondary" onclick="seal()">Seal</button>
    <pre id="output"></pre>
  </section>
  <div class="grid">
    <section>
      <h2>Unseal</h2>
      <label>Key parts, one per line</label>
      <textarea id="parts" rows="5"></textarea>
      <button onclick="unseal()">Unseal</button>
    </section>
    <section>
      <h2>Save Secret</h2>
      <label>Name</label><input id="secretName">
      <label>Value</label><textarea id="secretValue" rows="5"></textarea>
      <button onclick="saveSecret()">Save</button>
    </section>
    <section>
      <h2>Create Wrap Token</h2>
      <label>Secret name</label><input id="wrapName">
      <label>TTL seconds</label><input id="ttl" type="number" value="60">
      <button onclick="wrapSecret()">Wrap</button>
    </section>
  </div>
</main>
<script>
const out = document.getElementById("output");
function headers() {
  return {"Content-Type": "application/json", "Authorization": `Bearer ${document.getElementById("adminToken").value}`};
}
function show(data) { out.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2); }
async function call(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  show(data);
}
function status() { call("/status"); }
function seal() { call("/seal", {method: "POST", headers: headers()}); }
function unseal() {
  const parts = document.getElementById("parts").value.split("\\n").map(x => x.trim()).filter(Boolean);
  call("/unseal", {method: "POST", headers: headers(), body: JSON.stringify({parts})});
}
function saveSecret() {
  call("/secrets", {method: "POST", headers: headers(), body: JSON.stringify({
    name: document.getElementById("secretName").value,
    value: document.getElementById("secretValue").value
  })});
  document.getElementById("secretValue").value = "";
}
function wrapSecret() {
  call(`/secrets/${encodeURIComponent(document.getElementById("wrapName").value)}/wrap`, {
    method: "POST", headers: headers(), body: JSON.stringify({ttl_seconds: Number(document.getElementById("ttl").value)})
  });
}
</script>
</body>
</html>"""


UNWRAP_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Unwrap Secret</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #17202a; }
    main { max-width: 680px; margin: 0 auto; padding: 32px 20px; }
    section { background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px; }
    label { display: block; font-weight: 650; margin: 10px 0 5px; }
    textarea { box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid #b9c1ce; border-radius: 6px; }
    button { margin-top: 12px; padding: 10px 14px; border: 0; border-radius: 6px; background: #1459b8; color: white; cursor: pointer; }
    pre { white-space: pre-wrap; background: #111827; color: #e5e7eb; border-radius: 6px; padding: 12px; }
  </style>
</head>
<body>
<main>
  <h1>Unwrap Secret</h1>
  <section>
    <label>Wrap token</label>
    <textarea id="token" rows="4" autocomplete="off"></textarea>
    <button onclick="unwrapSecret()">Unwrap once</button>
    <pre id="output"></pre>
  </section>
</main>
<script>
const out = document.getElementById("output");
async function unwrapSecret() {
  const tokenBox = document.getElementById("token");
  const res = await fetch("/unwrap", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({token: tokenBox.value.trim()})
  });
  tokenBox.value = "";
  const data = await res.json().catch(() => ({}));
  out.textContent = JSON.stringify(data, null, 2);
  if (res.ok) setTimeout(() => { out.textContent = ""; }, 30000);
}
</script>
</body>
</html>"""


def admin_ui() -> HTMLResponse:
    return HTMLResponse(ADMIN_UI_HTML)


def unwrap_ui() -> HTMLResponse:
    return HTMLResponse(UNWRAP_UI_HTML)
