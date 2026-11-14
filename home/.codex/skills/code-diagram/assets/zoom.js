/* Shared diagram scale for buttons, trackpad pinch and Safari gestures. */
window.createDiagramZoom = function ({svg, viewport, diagram, plus, minus, fitButton,
  resetButton, onChange, minZoom = 0.025, maxZoom = 4, fitPadding = 32}) {
  let zoom = 1;
  let fitted = true;
  let gestureActive = false;
  let lastGestureScale = 1;
  let pointer;
  const box = svg.viewBox.baseVal;
  const clamp = value => Math.min(maxZoom, Math.max(minZoom, value));
  viewport.style.overflowAnchor = 'none';

  function refresh() {
    svg.style.width = box.width * zoom + 'px';
    svg.style.height = box.height * zoom + 'px';
    diagram.style.justifyContent = box.width * zoom > viewport.clientWidth ? 'flex-start' : 'center';
    plus.disabled = zoom >= maxZoom;
    minus.disabled = zoom <= minZoom;
    onChange(zoom);
  }

  function visibleCenter(rect) {
    const frame = viewport.getBoundingClientRect();
    const left = Math.max(0, frame.left + viewport.clientLeft, rect.left);
    const right = Math.min(window.innerWidth, frame.left + viewport.clientLeft + viewport.clientWidth, rect.right);
    const top = Math.max(0, frame.top + viewport.clientTop, rect.top);
    const bottom = Math.min(window.innerHeight, frame.top + viewport.clientTop + viewport.clientHeight, rect.bottom);
    return {clientX: right > left ? (left + right) / 2 : rect.left,
      clientY: bottom > top ? (top + bottom) / 2 : rect.top};
  }

  function setZoom(value, point) {
    if (!Number.isFinite(value) || value <= 0) return;
    fitted = false;
    const next = clamp(value);
    if (next === zoom) return;
    const before = svg.getBoundingClientRect();
    if (!point || !Number.isFinite(point.clientX) || !Number.isFinite(point.clientY)) {
      point = visibleCenter(before);
    }
    const x = (point.clientX - before.left) / before.width;
    const y = (point.clientY - before.top) / before.height;
    zoom = next;
    refresh();
    const after = svg.getBoundingClientRect();
    // Only pan the canvas; the toolbar and details panel stay outside its scroll container.
    viewport.scrollBy({left: after.left + x * after.width - point.clientX,
      top: after.top + y * after.height - point.clientY, behavior: 'instant'});
  }

  function fit() {
    fitted = true;
    zoom = clamp(Math.min(1, Math.max(1, viewport.clientWidth - fitPadding) / box.width,
      Math.max(1, viewport.clientHeight - fitPadding) / box.height));
    refresh();
    viewport.scrollTo({left: 0, top: 0, behavior: 'instant'});
  }

  function relayout() {
    if (fitted) fit(); else refresh();
  }

  plus.onclick = () => setZoom(zoom * 1.25);
  minus.onclick = () => setZoom(zoom / 1.25);
  fitButton.onclick = fit;
  fitButton.disabled = false;
  if (resetButton) {
    resetButton.onclick = () => setZoom(1);
    resetButton.disabled = false;
  }

  // Chromium/Firefox emit Ctrl+wheel for a trackpad pinch. Leave ordinary scrolling alone.
  viewport.addEventListener('wheel', event => {
    if (!event.ctrlKey || !event.cancelable) return;
    event.preventDefault();
    if (gestureActive || !Number.isFinite(event.deltaY)) return;
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? viewport.clientHeight : 1;
    const exponent = Math.max(-1, Math.min(1, -event.deltaY * unit * 0.01));
    setZoom(zoom * Math.exp(exponent), event);
  }, {passive: false});

  // Safari uses cumulative GestureEvent.scale. Incremental ratios keep buttons and limits in sync.
  viewport.addEventListener('pointermove', event => {
    pointer = {clientX: event.clientX, clientY: event.clientY};
  }, {passive: true});
  viewport.addEventListener('gesturestart', event => {
    if (!event.cancelable) return;
    event.preventDefault();
    gestureActive = true;
    lastGestureScale = Number.isFinite(event.scale) && event.scale > 0 ? event.scale : 1;
  }, {passive: false});
  window.addEventListener('gesturechange', event => {
    if (!gestureActive) return;
    event.preventDefault();
    if (!Number.isFinite(event.scale) || event.scale <= 0) return;
    const point = Number.isFinite(event.clientX) && Number.isFinite(event.clientY) &&
      (event.clientX !== 0 || event.clientY !== 0) ? event : pointer;
    setZoom(zoom * event.scale / lastGestureScale, point);
    lastGestureScale = event.scale;
  }, {passive: false});
  window.addEventListener('gestureend', event => {
    if (!gestureActive) return;
    event.preventDefault();
    gestureActive = false;
  }, {passive: false});
  window.addEventListener('blur', () => { gestureActive = false; });
  window.addEventListener('resize', relayout);

  return {fit, setZoom, refresh, relayout, get scale() { return zoom; }};
};
