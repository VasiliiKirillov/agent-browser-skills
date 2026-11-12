"""Click/find/fill helpers for aeroflot.ru + pay.aeroflot.ru (React, Ant Design,
styled-components, and shadow-DOM custom elements on the payment host).

Usage: copy this file to $BH_AGENT_WORKSPACE/agent_helpers.py at the start of a
booking run - browser_exec auto-imports every function in that file into each
call, and the browser session survives between calls while Python variables do
not, so all state lives in the page (window.__hb) rather than in Python.

Exposes: hb(), find(), sel(), state(), changed(), smart_click(), click_text(),
inputs(), set_input(), body_text(), shot(), jj().

NOTE: inside this module the browser helpers are reached as _js()/_cdp()
(resolved from browser_harness.run). Defining module-level functions named
js()/cdp() here would shadow the injected globals and recurse infinitely.
"""

import importlib
import json
import time


def _h(name):
    mod = importlib.import_module('browser_harness.run')
    fn = getattr(mod, name, None)
    if fn is None:
        raise RuntimeError('browser helper %r not found' % name)
    return fn


def _js(expr):
    return _h('js')(expr)


def _cdp(method, **kw):
    return _h('cdp')(method, **kw)


_HB_JS = r"""(() => {
  const H = {};
  H.walk = function*(root){
    const nodes = root.querySelectorAll('*');
    for (const el of nodes){ yield el; if (el.shadowRoot) yield* H.walk(el.shadowRoot); }
  };
  H.all = () => Array.from(H.walk(document));
  H.vis = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || parseFloat(s.opacity) === 0) return false;
    return true;
  };
  H.clickable = (el) => {
    const t = el.tagName;
    if (t === 'BUTTON' || t === 'A' || t === 'INPUT' || t === 'LABEL') return true;
    if (el.getAttribute && (el.getAttribute('role') === 'button' || el.getAttribute('role') === 'link')) return true;
    if (el.onclick) return true;
    try { if (getComputedStyle(el).cursor === 'pointer') return true; } catch (e) {}
    return false;
  };
  H.cn = (el) => (el && el.className && el.className.toString ? el.className.toString() : '');
  H.desc = (el, i) => {
    const r = el.getBoundingClientRect();
    return {
      i: i, tag: el.tagName, cls: H.cn(el).slice(0, 80),
      txt: (el.textContent || '').trim().slice(0, 60),
      x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2),
      w: Math.round(r.width), h: Math.round(r.height),
      kids: el.children.length, clk: H.clickable(el),
      dis: !!el.disabled, vis: H.vis(el)
    };
  };
  H.find = (opts) => {
    opts = opts || {};
    const rx = opts.re ? new RegExp(opts.re) : null;
    const out = [];
    H._last = [];
    for (const el of H.all()) {
      const tc = (el.textContent || '').trim();
      let ok;
      if (rx) ok = rx.test(tc);
      else if (opts.contains) ok = tc.indexOf(opts.text) >= 0;
      else ok = tc === opts.text;
      if (!ok) continue;
      if (opts.tag && el.tagName !== opts.tag) continue;
      if (opts.leaf && el.children.length > 0) continue;
      if (opts.vis !== false && !H.vis(el)) continue;
      H._last.push(el);
      out.push(H.desc(el, H._last.length - 1));
    }
    return out;
  };
  H.sel = (css) => {
    H._last = Array.from(document.querySelectorAll(css));
    return H._last.map((e, i) => H.desc(e, i));
  };
  H.put = (els) => { H._last = els; return els.map((e, i) => H.desc(e, i)); };
  H.pick = (i) => H._last[i];
  H.up = (i, lvl) => { let el = H._last[i]; for (let k = 0; k < (lvl || 0); k++) if (el && el.parentElement) el = el.parentElement; return el; };
  H.rect = (i, lvl) => {
    const el = H.up(i, lvl);
    el.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});
    const r = el.getBoundingClientRect();
    const cx = r.x + r.width / 2, cy = r.y + r.height / 2;
    const hit = document.elementFromPoint(cx, cy);
    return {x: cx, y: cy, w: r.width, h: r.height, tag: el.tagName,
            cls: H.cn(el).slice(0, 60),
            hit: hit ? (hit.tagName + '.' + H.cn(hit).slice(0, 30)) : null,
            same: !!hit && (hit === el || el.contains(hit) || hit.contains(el))};
  };
  H.nclick = (i, lvl, full) => {
    const el = H.up(i, lvl);
    el.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});
    const inner = (el.shadowRoot && el.shadowRoot.querySelector('button,input,a')) || null;
    const tgt = inner || el;
    if (full) {
      const r = tgt.getBoundingClientRect();
      const cx = r.x + r.width / 2, cy = r.y + r.height / 2;
      const o = {bubbles: true, cancelable: true, composed: true, clientX: cx, clientY: cy,
                 button: 0, buttons: 1, isPrimary: true, pointerId: 1, pointerType: 'mouse'};
      try { tgt.dispatchEvent(new PointerEvent('pointerover', o)); } catch (e) {}
      try { tgt.dispatchEvent(new MouseEvent('mouseover', o)); } catch (e) {}
      try { tgt.dispatchEvent(new PointerEvent('pointerdown', o)); } catch (e) {}
      try { tgt.dispatchEvent(new MouseEvent('mousedown', o)); } catch (e) {}
      try { tgt.dispatchEvent(new PointerEvent('pointerup', Object.assign({}, o, {buttons: 0}))); } catch (e) {}
      try { tgt.dispatchEvent(new MouseEvent('mouseup', Object.assign({}, o, {buttons: 0}))); } catch (e) {}
    }
    tgt.click();
    return {tag: tgt.tagName, cls: H.cn(tgt).slice(0, 60), shadow: !!inner, dis: !!tgt.disabled};
  };
  H.upclk = (i, max) => {
    let el = H._last[i];
    for (let k = 0; k <= (max || 8); k++) {
      if (!el) break;
      if (H.clickable(el)) return {lvl: k, tag: el.tagName, cls: H.cn(el).slice(0, 60), dis: !!el.disabled};
      el = el.parentElement;
    }
    return null;
  };
  H.hash = (s) => { let h = 0; for (let k = 0; k < s.length; k++) { h = (h * 31 + s.charCodeAt(k)) | 0; } return h; };
  H.state = () => {
    const t = (document.body ? document.body.innerText : '') || '';
    // checkbox/radio checked state and button classNames do NOT show up in
    // innerText - fold them in, or a successful toggle looks like "no change"
    // and the caller escalates into extra clicks that undo it.
    const chk = Array.from(document.querySelectorAll('input')).map(e => (e.checked ? '1' : '0') + (e.value || '')).join('|');
    const cls = Array.from(document.querySelectorAll('button,[role="button"]')).map(e => H.cn(e)).join('|');
    return {href: location.href, title: document.title, len: t.length,
            hash: H.hash(t), chash: H.hash(chk), bhash: H.hash(cls)};
  };
  H.setv = (el, val) => {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    el.focus();
    setter.call(el, val);
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
    el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
    return el.value;
  };
  // carry _last over on re-injection: a fresh __hb would drop the element array
  // the index-based click API points into, and every later call would throw.
  window.__hb = (() => { const prev = window.__hb; if (prev && prev._last) H._last = prev._last; return H; })();
  return 'hb-ok';
})()"""


def hb():
    """(Re)inject the page-side library. Safe to call repeatedly."""
    return _js(_HB_JS)


def jj(expr):
    """Evaluate a JS expression and JSON round-trip the result."""
    raw = _js("JSON.stringify(%s)" % expr)
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    return json.loads(raw)


def find(text=None, re=None, tag=None, leaf=False, contains=False, vis=True):
    """Find elements by exact text / regex, walking shadow roots too.

    Returns descriptors whose 'i' indexes the page-side array that smart_click
    consumes. Narrow with tag='BUTTON' when several wrappers share the text.
    """
    hb()
    opts = {}
    if text is not None:
        opts['text'] = text
    if re is not None:
        opts['re'] = re
    if tag:
        opts['tag'] = tag
    if leaf:
        opts['leaf'] = True
    if contains:
        opts['contains'] = True
    opts['vis'] = vis
    return jj("window.__hb.find(%s)" % json.dumps(opts))


def sel(css):
    """Same as find() but by CSS selector (light DOM only)."""
    hb()
    return jj("window.__hb.sel(%s)" % json.dumps(css))


def state():
    return jj("window.__hb.state()")


def changed(s0, s1):
    if s0 is None or s1 is None:
        return True
    for k in ('href', 'hash', 'chash', 'bhash'):
        if s0.get(k) != s1.get(k):
            return True
    return False


def cdp_click(x, y):
    try:
        _cdp('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y)
        _cdp('Input.dispatchMouseEvent', type='mousePressed', x=x, y=y, button='left', clickCount=1)
        _cdp('Input.dispatchMouseEvent', type='mouseReleased', x=x, y=y, button='left', clickCount=1)
        return 'ok'
    except Exception as e:
        return 'cdp-exc:%s' % type(e).__name__


def smart_click(idx, label='', wait=2.5, expect=None, max_lvl=6, verbose=True):
    """Escalating click on element index idx from the last find()/sel().

    Ladder: native l0 -> native nearest-clickable-ancestor -> synthetic pointer
    sequence -> CDP mouse at a freshly re-read rect -> CDP at each ancestor
    level. On aeroflot.ru rung 1 (native-l0) wins everywhere; a different rung
    in the log means the `expect` predicate is wrong, not that the DOM changed.

    ALWAYS pass `expect` for stateful controls (checkbox/radio -> .checked,
    binary buttons -> className diff, navigation -> location.href), because a
    wrong verdict makes the ladder issue extra clicks that toggle state back.
    """
    log = []

    def ok():
        if expect:
            try:
                if _js(expect):
                    return True
            except Exception:
                pass
        return False

    s0 = state()
    up = jj("window.__hb.upclk(%d, %d)" % (idx, max_lvl))
    log.append(('ancestor-clickable', up))
    lvl = up['lvl'] if up else 0

    attempts = [('native-l0', lambda: jj("window.__hb.nclick(%d,0,false)" % idx))]
    if lvl:
        attempts.append(('native-l%d' % lvl, lambda l=lvl: jj("window.__hb.nclick(%d,%d,false)" % (idx, l))))
    attempts.append(('ptrseq-l%d' % lvl, lambda l=lvl: jj("window.__hb.nclick(%d,%d,true)" % (idx, l))))

    def _mk_cdp(l):
        def f():
            # read the rect twice: the first read scrolls, the second gives the
            # post-scroll coordinates (stale coords are the classic CDP misfire)
            jj("window.__hb.rect(%d,%d)" % (idx, l))
            time.sleep(0.3)
            r = jj("window.__hb.rect(%d,%d)" % (idx, l))
            res = cdp_click(r['x'], r['y'])
            return {'rect': r, 'cdp': res}
        return f

    attempts.append(('cdp-l%d' % lvl, _mk_cdp(lvl)))
    for l in range(0, max_lvl + 1):
        if l != lvl:
            attempts.append(('cdp-walk-l%d' % l, _mk_cdp(l)))

    for name, fn in attempts:
        try:
            info = fn()
        except Exception as e:
            info = 'exc:%s' % e
        deadline = time.time() + wait
        won = False
        while time.time() < deadline:
            time.sleep(0.35)
            if ok():
                won = True
                break
            try:
                s1 = state()
            except Exception:
                # JS context destroyed == the page is navigating == success
                won = True
                break
            if changed(s0, s1):
                won = True
                break
        log.append((name, info, 'CHANGED' if won else 'no-change'))
        if won:
            if verbose:
                print('[click] %s OK via %s' % (label, name))
            return {'method': name, 'log': log}
        hb()
    if verbose:
        print('[click] %s ALL FAILED' % label)
        for l in log:
            print('   ', l)
    return {'method': None, 'log': log}


def click_text(text=None, re=None, tag=None, leaf=False, contains=False,
               pick='smallest', label=None, wait=2.5, expect=None, max_lvl=6):
    """find + pick a candidate + smart_click. pick: 'smallest'|'first'|'last'|int"""
    cands = find(text=text, re=re, tag=tag, leaf=leaf, contains=contains)
    if not cands:
        print('[click_text] NOT FOUND:', text or re)
        return {'method': None, 'cands': []}
    if isinstance(pick, int):
        c = cands[pick]
    elif pick == 'first':
        c = cands[0]
    elif pick == 'last':
        c = cands[-1]
    else:
        clk = [x for x in cands if x['clk']] or cands
        c = sorted(clk, key=lambda d: (d['w'] * d['h'], d['kids']))[0]
    print('[click_text] n=%d target=%s' % (len(cands), c))
    r = smart_click(c['i'], label=label or (text or re), wait=wait, expect=expect, max_lvl=max_lvl)
    r['cands'] = cands
    r['chosen'] = c
    return r


def inputs(only_vis=True):
    """Dump every <input> with its index, placeholder, value and type.

    Anchor offsets on a known placeholder (e.g. IVANOV) - absolute indexes shift
    between pages and between modal-open / modal-closed states.
    """
    rows = jj("""(() => Array.from(document.querySelectorAll('input')).map((e,i)=>({
        i:i, ph:e.placeholder, v:e.value, t:e.type, name:e.name||'', id:e.id||'',
        cls:(e.className||'').toString().slice(0,40),
        vis:(e.getBoundingClientRect().width>1)
      })))()""")
    return [r for r in rows if r['vis']] if only_vis else rows


def set_input(idx, val):
    """React-safe fill: native value setter + input/change/keyup dispatch."""
    hb()
    return _js("(() => window.__hb.setv(document.querySelectorAll('input')[%d], %s))()"
               % (idx, json.dumps(val)))


def body_text(n=4000):
    t = _js("document.body.innerText")
    return (t or '')[:n]


def shot():
    return _h('capture_screenshot')()
