---
name: browser-data-extraction
description: "Extract page data via DOM leaf-text dump, not screenshots."
tags: [browser, scraping, extraction]
---

# Reading structured data off a loaded page

Use when a page is already open via `browser_exec` (desktop Chrome or headless) and you need prices, filter labels, table rows, or any text data rendered by JS (price aggregators, booking sites, dashboards with a sidebar of filters).

## The reliable technique: dump every leaf text node

Don't hunt for a specific element by exact text match and read `parentElement.textContent` - JS-heavy sites render a label and its value as separate sibling nodes, so matching one node and climbing to a parent often returns empty string or the wrong subtree. Don't reach for `vision_analyze` with cropped screenshot regions either as the first move - guessing the crop coordinates burns multiple round-trips when the content is plain text that already exists in the DOM.

Instead, in one `js()` call, collect every element with no children and non-empty text, in DOM order:

```python
txt = js("""(() => {
  const all = document.querySelectorAll('body *');
  let result = [];
  for (const el of all) {
    if (el.children.length === 0 && el.textContent.trim().length>0) {
      result.push(el.textContent.trim());
    }
  }
  return result.join(' | ');
})()""")
print(txt)
```

This returns labels and values interleaved in the order they appear visually (e.g. `Oct 3, Sat | $420 | Direct flights only | No tickets`), which you then parse in Python with string splits or regex. It is cheap, works across re-layouts (no fixed coordinates), and gives you the actual text content rather than a guess from pixels.

For airline/price-aggregator style pages specifically, also pull `img[alt]` to resolve carrier/brand logos to names when the visible label is icon-only:

```python
logos = js("""(() => Array.from(document.querySelectorAll('img')).map(i => i.alt).filter(a=>a).join(' | '))()""")
```

## When to fall back to vision

Only use `capture_screenshot()` + `vision_analyze` when the information is genuinely graphical and has no text form in the DOM - a chart, a photo, a QR code, or layout/visual confirmation ("does this look right"). If the data you need is a number, label, or status string, it is almost always present as DOM text even when the on-screen rendering looks like an icon or badge - try the leaf-dump first.

## Driving a JS app when there is no URL to jump to - real events, not DOM calls

Driving the UI is the last resort (auth wizards, modals, editors); when the app does have addressable state, navigate by URL and read the DOM instead. When you must drive it:

- Clicking: `element.click()` and plain synthetic clicks are often swallowed - the app's own handlers never see a pointer. Dispatch mouse events at the element's viewport centre from `getBoundingClientRect()`: `cdp('Input.dispatchMouseEvent', type='mouseMoved'|'mousePressed'|'mouseReleased', x=..., y=..., button='left', clickCount=1)`, roughly 100 ms between press and release.
- Coordinate system pitfall: `cdp('DOM.getBoxModel', backendNodeId=...)` and `cdp('Input.dispatchMouseEvent', ...)` both use real viewport pixels - the same scale as the page's own CSS pixels - never the downscaled image `capture_screenshot()` hands you for vision (that image is frequently halved, e.g. a 1920px-wide viewport renders as a 960px image). Find the target with `cdp('Accessibility.getFullAXTree')` (match by name/role) -> take its `backendDOMNodeId` -> `cdp('DOM.getBoxModel', backendNodeId=...)` -> dispatch at the center of the returned `content` quad directly. Never eyeball a coordinate off the screenshot and multiply by a guessed scale factor - that reliably lands the click on the wrong element (often a sidebar link instead of the intended button) and burns a retry loop before the real cause (wrong coordinate space, not a bad selector) becomes obvious.
- Typing into React-controlled inputs: setting `.value` plus an `input` event (or `fill_input`) updates the DOM but NOT the app's state - the submit button stays disabled or never renders. Type character by character with `cdp('Input.dispatchKeyEvent', type='char', text=ch)`. Clear a field with a triple click (`clickCount=3`) then `Backspace` via `rawKeyDown`/`keyUp` (key and code `Backspace`, windowsVirtualKeyCode 8).
- A search-as-you-type field often doubles as a picker (a phone country field accepts "russia" and fills +7): type the name and read the label it resolves to instead of fighting a dropdown.
- Read the page back after each step - `document.body.innerText`, current input values, and which buttons exist now (a Next/submit button that appears only once the form is valid is your progress signal). A page that renders its chrome while `innerText` stays empty is a failed render, not an empty app.

## Iterating over multiple pages/dates/variants

When checking the same data point across several URLs (e.g. ticket prices for a range of dates), loop `goto_url(url)` -> `wait_for_load()` -> fixed `time.sleep(10-15)` for client-side rendering -> leaf-dump, rather than re-navigating with `new_tab` each time (which reloads the whole page chrome) or trying to click date-pickers in a SPA (fragile selectors, extra round-trips). Direct URL navigation per date/variant is slower per-call but far more reliable than driving the UI.

### Example: comparing round-trip flight options across a date range (aviasales.ru)

To compare a route across several departure dates without touching the UI, build the search URL directly: `https://www.aviasales.ru/search/{FROM}{DDMM}{TO}{N}{DDMM_return}{N}` - e.g. `LED1503MOW1903001` means city-A->city-B out 15.03, back 19.03, 1 passenger both legs (one-way is just `{FROM}{DDMM}{TO}{N}` with no return date/count). Loop this per candidate departure date, leaf-dump each page, and slice the text between the literal tokens `'Сортировка'` and `'Авиакомпании | Победа'` - that span holds only the actual flight offers (times, duration, direct/transfer, price); everything before is UI chrome/date-tabs and everything after is sidebar filter facets, both of which pollute a naive leaf-dump with noise if you don't trim to this window. Each offer entry in that window contains BOTH legs back to back (outbound then return), so parse it as paired blocks, not one price per line.

The sidebar "direct flights only" filter facet price is satisfied if EITHER leg is nonstop - it does not mean both legs are direct. Never quote a "round-trip, both legs direct" price from that facet number alone: open the actual offer line and check both legs' own tag (direct vs. N stops) before claiming both directions are nonstop. If a date combination truly has no fully-direct round trip, the filtered result set typically still renders offers (each with one direct + one connecting leg) rather than an empty state - the presence of a price under that filter is not proof a nonstop-both-ways itinerary exists.

The site intermittently fails a fresh page load with an on-page "search did not start" error even for a URL pattern that worked moments earlier, especially on back-to-back `goto_url` calls reusing the same tab. Check the leaf-dump for that phrase (or confirm the sort-control text is present) before trusting a result; on failure, retry the same URL once or twice with a longer `sleep` rather than concluding the route has no results. If several retries in the foreground session still return the error page or a stale/empty result, delegate the same lookup to a background subagent task with explicit retry instructions instead of burning foreground turns on it; it can spend the many attempts needed without blocking the user-facing session, and report back only once it has a real, verified number.

Prices on this kind of aggregator drift between separate loads of the EXACT SAME search URL/parameters, not just over hours but within the same session a few minutes apart - this is not just inventory selling out, the quoted minimum can go up or down noticeably on an identical re-fetch. Never present a single fetch's price as a firm, final number: tell the user it is a snapshot that may shift by purchase time, and if the user needs a number for a multi-passenger total, prefer re-fetching once more and giving a range (or the most recent fetch) over multiplying a single possibly-stale per-passenger price by the passenger count and presenting it as exact.
