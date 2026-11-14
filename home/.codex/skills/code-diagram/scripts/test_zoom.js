// Test the generated viewer's zoom controller with deterministic DOM geometry, without a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const code = html.match(/<script id="diagram-zoom">([\s\S]*?)<\/script>/)[1];
// Check syntax of the complete emitted viewer too, without running Mermaid or UI automation.
for (const [, attrs, body] of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
  if (!attrs.includes('application/json') && !attrs.includes('src=')) new vm.Script(body);
}

function events(target = {}) {
  const listeners = new Map();
  target.addEventListener = (type, handler, options) => {
    if (!listeners.has(type)) listeners.set(type, []);
    listeners.get(type).push({handler, options});
  };
  target.emit = (type, fields = {}) => {
    const event = {cancelable: true, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, ...fields};
    for (const {handler, options} of listeners.get(type) || []) {
      handler(event);
      if (event.defaultPrevented) assert.equal(options?.passive, false);
    }
    return event;
  };
  return target;
}

function fixture() {
  const win = events({innerWidth: 1200, innerHeight: 900, scrollX: 0, scrollY: 0});
  win.scrollBy = ({left, top}) => {
    win.scrollX = Math.max(0, win.scrollX + left);
    win.scrollY = Math.max(0, win.scrollY + top);
  };
  const viewport = events({clientWidth: 900, style: {}});
  const diagram = {style: {}};
  const svg = {viewBox: {baseVal: {width: 1200, height: 800}}, style: {}};
  svg.getBoundingClientRect = () => {
    const width = parseFloat(svg.style.width) || 1200;
    const height = parseFloat(svg.style.height) || 800;
    const left = 32 + (diagram.style.justifyContent === 'center' ? Math.max(0, (viewport.clientWidth - width) / 2) : 0) - win.scrollX;
    const top = 200 - win.scrollY;
    return {left, top, width, height, right: left + width, bottom: top + height};
  };
  const plus = {}, minus = {}, fitButton = {}, resetButton = {};
  let displayedScale;
  vm.runInNewContext(code, {window: win});
  const control = win.createDiagramZoom({svg, viewport, diagram, plus, minus, fitButton, resetButton,
    onChange(scale) { displayedScale = scale; }});
  control.fit();
  return {win, viewport, svg, plus, minus, fitButton, resetButton, control,
    get displayedScale() { return displayedScale; }};
}
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} != ${expected}`);
const wheel = (f, ratio, fields = {}) => f.viewport.emit('wheel', {
  ctrlKey: true, deltaY: -Math.log(ratio) / .01, deltaMode: 0, clientX: 500, clientY: 400, ...fields,
});

// Alternate trackpad and buttons: each continues from the scale displayed by the other.
{
  const f = fixture();
  const initial = f.control.scale;
  assert.ok(wheel(f, 1.2).defaultPrevented);
  near(f.control.scale, initial * 1.2);
  f.plus.onclick(); near(f.control.scale, initial * 1.2 * 1.25);
  wheel(f, 1 / 1.2); f.minus.onclick(); near(f.control.scale, initial);
  near(f.displayedScale, f.control.scale);
  near(parseFloat(f.svg.style.width), 1200 * f.control.scale);
  assert.equal(wheel(f, 1.2, {ctrlKey: false}).defaultPrevented, false);
  assert.equal(wheel(f, 1.2, {cancelable: false}).defaultPrevented, false);
  near(f.control.scale, initial);
  f.win.emit('wheel', {ctrlKey: true, deltaY: -100}); // Outside the diagram is untouched.
  near(f.control.scale, initial);
}

// The same SVG coordinate stays under the pointer as a centered diagram becomes wider than its container.
{
  const f = fixture();
  const point = {clientX: 500, clientY: 400};
  const before = f.svg.getBoundingClientRect();
  const x = (point.clientX - before.left) / before.width;
  const y = (point.clientY - before.top) / before.height;
  wheel(f, 1.5, point);
  const after = f.svg.getBoundingClientRect();
  near(after.left + after.width * x, point.clientX);
  near(after.top + after.height * y, point.clientY);
  wheel(f, 1 / 1.5, point);
  near(f.control.scale, .73);
}

// Safari's cumulative scale must not be compounded; overlapping wheel events must not apply it twice.
{
  const f = fixture();
  f.resetButton.onclick();
  f.viewport.emit('pointermove', {clientX: 500, clientY: 400});
  assert.ok(f.viewport.emit('gesturestart', {scale: 1}).defaultPrevented);
  assert.ok(f.win.emit('gesturechange', {scale: 1.2}).defaultPrevented);
  near(f.control.scale, 1.2);
  assert.ok(wheel(f, 1.2).defaultPrevented); near(f.control.scale, 1.2);
  f.plus.onclick(); near(f.control.scale, 1.5);
  f.win.emit('gesturechange', {scale: 1.4}); near(f.control.scale, 1.75);
  f.win.emit('gestureend');
  wheel(f, 1.2); near(f.control.scale, 2.1);
  assert.equal(f.win.emit('gesturechange', {scale: 2}).defaultPrevented, false);
  f.viewport.emit('gesturestart', {scale: 1}); f.win.emit('blur');
  wheel(f, 1.2); near(f.control.scale, 2.52);
}

// Bounds, immediate gesture reversal at a bound, and Fit/manual zoom after resize.
{
  const f = fixture();
  f.control.setZoom(3);
  f.viewport.emit('gesturestart', {scale: 1});
  f.win.emit('gesturechange', {scale: 2}); near(f.control.scale, 4);
  assert.equal(f.plus.disabled, true);
  f.win.emit('gesturechange', {scale: 1.8}); near(f.control.scale, 3.6);
  assert.equal(f.plus.disabled, false);
  f.win.emit('gestureend');
  f.control.setZoom(.001); near(f.control.scale, .025); assert.equal(f.minus.disabled, true);
  f.plus.onclick(); near(f.control.scale, .03125); assert.equal(f.minus.disabled, false);
  f.control.setZoom(NaN); f.control.setZoom(Infinity); near(f.control.scale, .03125);
  f.fitButton.onclick(); near(f.control.scale, .73);
  f.viewport.clientWidth = 600; f.win.emit('resize'); near(f.control.scale, .48);
  f.plus.onclick(); f.viewport.clientWidth = 900; f.win.emit('resize'); near(f.control.scale, .6);
  f.control.relayout(); near(f.control.scale, .6);
  f.fitButton.onclick(); near(f.control.scale, .73);
}

// Wheel line/page units produce the same change as equivalent pixel deltas.
{
  const pixel = fixture(), line = fixture(), page = fixture();
  wheel(pixel, 1, {deltaY: -16});
  wheel(line, 1, {deltaY: -1, deltaMode: 1});
  wheel(page, 1, {deltaY: -16 / 900, deltaMode: 2});
  near(pixel.control.scale, line.control.scale);
  near(pixel.control.scale, page.control.scale);
}
