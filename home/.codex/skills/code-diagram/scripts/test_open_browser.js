// Exercise the generated message bridge as plain JS, without browser automation.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const html = fs.readFileSync(process.argv[2], "utf8");
const payloadText = html.match(/<script id="diagram-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const payload = JSON.parse(payloadText);
const script = html.match(/<script id="drawio-bridge">([\s\S]*?)<\/script>/)[1];
const sent = [], downloads = [], blobs = [];
let handler;
const editor = {contentWindow: {postMessage: (data, origin) => sent.push({data: JSON.parse(data), origin})}};
const document = {
  getElementById: id => id === "editor" ? editor : {textContent: payloadText},
  createElement: () => ({click() { downloads.push({name: this.download, href: this.href}); }, remove() {}}),
  body: {appendChild() {}},
};
vm.runInNewContext(script, {
  document, window: {addEventListener(type, callback) { assert.equal(type, "message"); handler = callback; }},
  Blob: class { constructor(parts) { this.text = parts.join(""); } },
  URL: {createObjectURL(blob) { blobs.push(blob); return "blob:test"; }, revokeObjectURL() {}},
  setTimeout() {},
});
const origin = "https://embed.diagrams.net";
const emit = (message, overrides = {}) => handler({data: JSON.stringify(message), origin, source: editor.contentWindow, ...overrides});
assert.equal(document.title, payload.title + " — draw.io");
assert.equal(new URL(editor.src).origin, origin);
assert.ok(!editor.src.includes(payload.xml));
emit({event: "init"}, {origin: "https://unrelated.example"});
emit({event: "init"}, {source: {}});
emit(null);
emit({}, {data: "not JSON"});
assert.equal(sent.length, 0);
emit({event: "init"});
assert.equal(sent.length, 1);
assert.equal(sent[0].origin, origin);
assert.equal(sent[0].data.action, "load");
assert.equal(sent[0].data.title, payload.title);
assert.equal(sent[0].data.xml, payload.xml);
const edited = '<mxfile><diagram id="edited"/></mxfile>';
emit({event: "save", xml: edited}, {origin: "https://unrelated.example"});
emit({event: "autosave", xml: edited});
emit({event: "save", xml: ""});
assert.equal(downloads.length, 0);
emit({event: "save", xml: edited});
assert.equal(downloads.length, 1);
assert.equal(downloads[0].name, payload.title);
assert.equal(blobs[0].text, edited);
assert.equal(sent.at(-1).data.action, "status");
assert.equal(sent.at(-1).data.modified, false);
emit({event: "init"});
assert.equal(sent.at(-1).data.xml, edited);
