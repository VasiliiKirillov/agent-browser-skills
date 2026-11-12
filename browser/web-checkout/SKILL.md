---
name: web-checkout
description: "Book/buy online: fill checkout forms, stop at payment step."
tags: [browser, checkout, purchase, booking]
---

# Web checkout / purchase flows

## When to use

Booking flights/hotels/tickets/goods through a merchant site in a browser automation session on the user's behalf (e.g. "go to the airline's site and start buying a ticket"). Start your browser session first.

## Standing rules (every checkout, no need to ask each time)

- Fill buyer/passenger personal data (name, DOB, passport, phone, email) once the user gives it - this is not a password, fine to type directly with `fill_input`/`js`.
- Default to UNCHECKING any marketing/promotional-consent checkbox ("sign me up for offers", "receive marketing emails", etc.) on any step, unless the user says otherwise - most users want this off on purchases by default; confirm their preference once and then apply it consistently.
- Required legal/terms-of-service checkboxes needed to actually proceed are fine to check.
- Decline optional paid add-ons (insurance, extended protection, etc.) by default when the user didn't ask for them - pick the explicit "I decline" option if the page forces a choice before continuing.
- At the payment step: list the available payment methods and the amount. Card entry and completing the purchase (clicking "pay now") should ONLY go through a saved vault payment handle (`browser_vault_fill`) if your harness supports one - the real card number/CVC must never be typed as plaintext by the model (not via `fill_input`, not via raw JS/CDP `Input.insertText`, nothing that puts the digits in a tool call, a log line, or the session transcript/backups). If the user pastes a card number/expiry/CVC straight into chat, do not type any of it into the page and do not repeat the digits back - tell them to save the card in their own vault so `browser_vault_fill` can fill it with their confirmation. Note: on sites whose card form is a hosted-fields widget (see Pitfalls below), `browser_vault_fill` only reaches name/expiry/postcode in the parent frame - it cannot reach the number/CVV inside a cross-origin iframe. On those sites the number/CVV CANNOT be filled by the model at all right now (no safe path exists) - stop there, tell the user the form is ready except those two fields, and they type them themselves. Do not fall back to typing the raw digits yourself just because vault_fill can't reach the iframe - that reintroduces the exact leak this rule exists to prevent.
- After the user says they paid, reload/re-check the booking page for a confirmation state (URL usually moves to a `.../confirmation`, `.../welcome`, or similar path, or the page shows an order/ticket number) instead of asking them to prove it.
- The moment that confirmation state is observed, write the purchase down somewhere durable (a note, a journal, a tracking sheet - whatever your setup uses) BEFORE replying with "done/payment went through". This is the step that is easiest to forget because the natural flow ends at "report the booking reference to the user" - build the logging step into the checkout procedure itself, not into a separate "remember to log purchases" habit, or a real paid ticket will go unlogged because the two skills never fired together.
- If the chosen payment method produces an artifact (QR code, confirmation code) rather than a direct redirect, screenshot it and deliver the image to the user over whatever channel they name rather than just describing it in chat.
- When a site offers both a "download PDF/file" button and a "send to my e-mail" option for the same document (boarding pass, invoice, ticket, confirmation), **prefer the e-mail option**. A click on a download button in a headless/remote browser harness drops the file into Chrome's internal download dir, which is not reliably findable afterward - the e-mail delivers straight into an inbox you can verify and the user can open it themselves from their phone. Report back which mailbox received it, not a file path.

- Seat preference on flights: ask the user once and remember it (e.g. "aisle seat, side block not the middle, as far forward as possible, but never pay extra for a premium/first-row fare tier"). Apply whatever they tell you to every airline's seat map, not just one carrier.

## Finding flight options before opening the airline's own site

For "find tickets to X on the nearest dates" with no site specified: `web_search` first for schedule/price overview (aggregator result snippets often already list exact flight days and direct-only schedule in the description text, no browsing needed). To get an exact price+schedule for ONE candidate date without a full search form, open an aggregator's own direct search URL (e.g. aviasales.ru's `/search/{IATA_FROM}{DDMM}{IATA_TO}1` pattern - see `browser-data-extraction`) - it renders a results list with prices per fare and, once a flight is open, a day-by-day price calendar strip (click through adjacent dates to compare without re-running search). Only move to the specific airline's own site once the user picks a date/flight, since airline sites charge seat/baggage markups the aggregator just quotes the base fare for.

For a ROUND TRIP on one candidate date pair, extend the same URL pattern with a second date segment before the trailing passenger-count digit. The results page groups outbound+return combos and shows a blended price per combo.

The results page occasionally fails to render on first load even for a route/date that does have flights - this is page-level flakiness, not a wrong URL: reload the exact same URL once or twice before concluding the route/date is unavailable.

To check whether a nonstop/direct combo exists for a route+date pair WITHOUT fighting a "direct flights only" filter checkbox's unreliable click/checked-state handling, just read the filter PANEL label itself: the sidebar row is usually immediately followed by either a price (a direct fare exists, that is its cheapest value) or a "no tickets"/"no direct flights" message (no direct option at all) - read that text and don't click the checkbox at all when the only question is availability.

## Airline booking sites: search, passenger form, seat map

Class-level patterns for any carrier's own site - carrier-specific skills carry each site's exact selectors.

- **Drive the results URL directly, not the search form.** Carriers encode the query in the results URL, so navigating to it (rather than filling the "from"/"to" autocompletes and the date calendar) lands on the fare list with the form already filled. The autocomplete options are often not leaf text nodes and calendar day cells are hit-and-miss by coordinate click, so the form path burns many rounds; open the results URL first and only fall back to the form if the URL is not enumerable.
- **Fare cards expand from the class NAME, not the price block.** Clicking the card's price area or its rect centre typically does nothing; the leaf text element for the fare class name ("Economy", etc.) is the click target that reveals the per-tariff sub-options, each with its own "Select" button. There are usually several identical-text "Select" buttons side by side - pick by x-coordinate/column, not by first match. List all tariff prices and their baggage/refund terms before asking the user to pick - most users want the terms spelled out, not just the price.
- **Passenger forms use example placeholders, not labels.** Fields are found by placeholders like `IVANOV` (surname) / `IVAN` (given name) or similar transliterated examples; a translated guess at a label rarely matches anything and makes `fill_input` raise. Date-of-birth and document number/expiry inputs often have EMPTY placeholders - locate them by `document.querySelectorAll('input')` index order and set via native-setter + `input`/`change` dispatch (plain `.value=` is ignored by React forms).
- **Seat maps may expose no per-seat identity.** When nothing matches `[class*="seat"]`, `[data-seat]` or an aria-label, legend-swatch colour-matching has nothing to hook onto. Anchor on the row-number element instead: find the leaf text equal to the row (`27`), then the sibling cells that follow it in document order are that row's seats in column order. Click a cell to open its floating price box - that box is the only reliable read of the seat's type and cost - and verify a committed choice by watching the summary flip from "not selected" to the chosen seat. If the map is ambiguous, deliver a screenshot to the user and ask rather than guessing which tier a colour means.
- **Click the passenger avatar/chip BEFORE any seat cell, on any carrier's seat map.** Clicking a seat before the passenger is "active" for seat-picking does nothing visible - no error, no popup, the summary keeps showing "no seat selected" - and looks exactly like a failed click. Click the passenger's name/avatar near the top of the seatmap page first (this arms seat-pick mode for them), then click the seat cell; only then does it open its confirm popup, and only that popup's own "Select seat"/confirm button actually commits the choice (the summary flipping from its placeholder to the seat number is the verification signal, same pattern as the running-total check above).
- **2+2 narrowbody/regional layout (e.g. ATR42/72) has no center block** - columns B and C sit on the aisle, A and D on the window; apply the standing aisle-seat preference to B/C, not to A/D. Seats already taken by someone else render with no price text at all (not "free of charge", not a currency figure) and their cell does not open a confirm popup on click - treat the absence of any price text as "unavailable", don't keep retrying the click.

## Finding accommodation options (Booking / Airbnb / Agoda)

No aggregator exposes a public search API - the practical path is the site's own search URL in a real browser session, then read the result DOM (see `browser-data-extraction`). `web_extract` alone gives only a partial Booking page (filter labels, a few cards) and near-nothing for Airbnb/Agoda. When asked to "compare Booking/Airbnb/Agoda", load all three and pull the cards, rather than trusting one.

- **Booking.com** - easiest and most complete. Direct URL:
  `https://www.booking.com/searchresults.html?ss=<area>&checkin=YYYY-MM-DD&checkout=YYYY-MM-DD&group_adults=1&no_rooms=1&group_children=0&selected_currency=USD`
  Each result is `[data-testid="property-card"]`; inside: name `[data-testid="title"]`, price `[data-testid="price-and-discounted-price"]`, distance `[data-testid="distance"]`, rating `[data-testid="review-score"]` (or `[data-testid="score"]`). Search the *airport/area* name to get the cluster you want - the `distance` shown is from that searched centre, so describe it that way, not as "from the airport".
- **Airbnb** - `https://www.airbnb.com/s/<Place>--Country/homes?checkin=...&checkout=...&adults=1&currency=USD`; each listing is `[data-testid="card-container"]` and its `innerText` carries type / beds / baths plus the price as **"N total"** - the all-fees-included total for the stay, NOT a per-night rate, so normalize before comparing to Booking. Many hosts set a 2-3 night minimum: on a 1-night search a chunk of cards show a different date range in their subtitle and are effectively unavailable - read the subtitle before calling a card bookable.
- **Agoda** - `https://www.agoda.com/search?city=<id>&checkIn=YYYY-MM-DD&los=<nights>&rooms=1&adults=1&children=0`. Pitfall: a **wrong `city=` id silently loads a different city** with no error - confirm the neighbourhood filter list matches the city you asked for. Cards are `[data-selenium="hotel-item"]`; an area filter is usually a `<label>` - click it to narrow to a specific cluster. Agoda lazy-renders prices: only the first few cards get a price in the DOM even after scrolling each into view, so treat its price coverage as partial and cross-check the same property on Booking.

Reality check worth giving the user when comparing: the same property is often listed on all three at slightly different prices; Airbnb adds a guest service fee and often a cleaning fee, so for a single night it is usually equal to or worse than Booking. Present a short grouped list (cheapest-with-rating / closest-to-airport / best value) and let them pick before any booking flow starts.

## Procedure

1. Start your browser session, search/compare offers if asked, present a short summary, get the user's pick BEFORE opening the checkout flow.
2. Walk the multi-step form (passenger/buyer info -> options/seat/add-ons -> review -> payment) one step at a time. After every "Continue" click, re-check the page state (URL + visible heading/toast) before assuming it advanced - see pitfalls below for why a click can look fine and silently fail.
3. At the payment step, enumerate every offered method (cards, bank apps, QR, installment plans, vouchers) so the user can choose, then drive to that method's screen only.
4. Once the purchase is confirmed (success/confirmation URL reached, or an order/booking/PNR number is on screen): log the event somewhere durable, THEN reply to the user. See below.

## Logging the purchase (mandatory final step of every checkout)

A completed purchase is finished only when it is recorded somewhere you (and the user) can look it up later. The order is fixed:

    confirmation observed -> write it down -> reply to the user

Never the reverse, and never "I'll log it if they ask". Do it without asking permission if it's a private note-to-self store the user has already set up for this (not an outgoing message to anyone else).

What to capture - everything the user would later ask you to look up, so they never have to repeat it:

- flights: route (both cities), flight number, date, departure/arrival time, seat, **booking code / PNR**, price paid
- hotels/Airbnb: property name, area, check-in/check-out dates, guests, **confirmation code**, price paid
- goods/other: what was bought, merchant, **order number**, price paid

A flight RESERVATION bought from a visa-reservation service ("flight reservation for visa purposes") is NOT a ticket - it cannot be flown, and the money went to the reservation service, not the airline. Log it as a booking with that service's order number, route and date, and note in the text that it is a reservation, never as a real ticket purchase with the route's notional fare. These reservations are easy to mistake for a purchase: the PDF they email is laid out exactly like an airline itinerary/receipt, with a full fare + taxes breakdown and a "Confirmed" status, and it carries a PNR. Identify it by where the payment actually went (the confirming email and its amount) before logging it as one or the other.

Also log a purchase the user completed themselves on a page you prepared (they typed the card number/CVV, or paid a QR you delivered) - the money left their account either way, so it belongs in the log exactly the same.

If anything about the purchase is still unknown when you log it (price not shown, PNR not yet issued), log what you have immediately and update it once the confirmation e-mail arrives - an incomplete entry beats a missing one.

## Pitfalls

### A "Continue"/submit click can silently fail validation - verify, don't assume
Clicking Continue on a multi-field step (e.g. passenger form) can look like it worked (no visible error, same button) while a required field - gender, a toggle-button choice, a checkbox - never actually registered, and the page just re-renders the same step. Confirm the click "took" (the field's CSS class changed to a selected-state class, or its value is no longer empty) before moving on. If a "please fill in..." toast appears after clicking Continue, that names a different required field still empty - go find and fix that field instead of re-clicking the same Continue button.

### Binary choices rendered as two plain `<button>`s have no reliable `checked`/`aria-pressed`
Sites that render gender/yes-no as two styled buttons rather than radio inputs expose neither `checked` nor `aria-pressed`. Detect which one is selected by diffing both elements' `className` before and after a click (the selected one gets a different generated class), rather than trusting that the click landed - a stray click on the wrong coordinates looks identical to success until the submit step rejects the form.

### Picking the wrong verification signal makes a working click look failed - and the "retry" undoes it
A generic "did the page change" check (page text hash, innerText diff) reports a false negative on checkboxes, radios, and two-button toggles, because ticking a consent box or selecting a gender changes no visible text at all. The natural response - click again - then toggles the control back to its original state, which looks like further proof the click "doesn't work". On one real multi-step checkout every single click across the whole flow landed on the first try with plain `el.click()`; the entire string of "silently failing clicks" across two earlier attempts was this exact phantom, not a real DOM/event problem. Before escalating to CDP mouse events, shadow-DOM walking, or parent-element search, match the verification signal to the control that was clicked:

- navigation / step change -> `location.href` or a URL fragment change
- checkbox / radio -> `el.checked`, never innerText
- two-`<button>` binary (gender, yes/no) -> `className` diff, per the pitfall above
- a selection that shows a running total/summary -> that summary's text flipping from its placeholder ("not selected") to the committed value
- a modal opening/closing -> presence/absence of a field unique to that modal

Fold every one of these into whatever "page changed" helper the run uses (checkbox `.checked` states and button `className`s belong in the same hash as the text, or a checkbox toggle registers as "no change"). Only treat a click as genuinely failed, and only then escalate the click method, once the *matching* signal for that control type fails to move.

### Web-component (shadow DOM) sites: the real clickable element is not what `querySelector` finds
Modern checkout UIs built on custom elements (e.g. `<my-button>`, any `<tag-with-a-dash>`) wrap every control in a custom element whose actual `<button>`/`<input>` lives inside its own `shadowRoot`, invisible to `document.querySelectorAll('button')`. Symptoms: that selector returns an empty/tiny list even though buttons are visibly on the page, and `.click()` on the host custom element does nothing. Walk the shadow tree recursively and click the native element inside:
```js
function* walk(root) {
  for (const el of root.querySelectorAll('*')) {
    yield el;
    if (el.shadowRoot) yield* walk(el.shadowRoot);
  }
}
for (const el of walk(document)) {
  if (el.tagName === 'MY-BUTTON' && el.textContent.trim() === 'Show') {
    const inner = el.shadowRoot?.querySelector('button');
    (inner || el).click();
  }
}
```
Reuse this same `walk()` helper to locate ANY element (button, input, label, price text) whenever a direct `document.querySelector` comes back empty on a page you can see contains that text/control.

### Clicking a button on an Angular/Zone.js (or any SPA) page: try native `.click()` first, escalate to CDP, and treat a CDP timeout as UNKNOWN, not failure
Neither method is universally reliable - do not commit to one. Try the cheap one first, escalate, and verify page state after EACH attempt:
0. Re-read the button's `disabled` property BEFORE treating the click as failed. A button that looks enabled and swallows the click (no toast, no URL change, no DOM reaction) is often transiently `disabled` because the page just re-rendered after the previous step or an async call is in flight - in that state neither `.click()` nor a CDP mouse sequence does anything, and escalating through every technique wastes rounds. If `disabled` is true, wait a couple of seconds and re-check; it normally flips back to false on its own and the very next click lands.
1. `js(...)`: `scrollIntoView({block:'center'})` then call `.click()` on the element directly. No coordinates, and it does drive Material/Angular submits (observed working where coordinate clicks did nothing).
2. If the URL/state did not change, escalate to the raw CDP mouse sequence below.
3. After either attempt, re-read state (`window.location.href`, the field/textarea value, a toast or the ticket status) - a click that "did nothing" may actually have submitted; only the next read tells you.

`el.click()` can fire the JS handler yet not advance the app: some Angular (Zone.js-patched) buttons run an attached `addEventListener` counter and even a `fetch`, but the router/state machine never moves, because Zone.js wants a *trusted* event dispatched through the real input pipeline, not a synthetic `el.click()`/`dispatchEvent(new MouseEvent(...))`. That is when you escalate to CDP's input domain:
```python
rect = js("(() => { const b = /* find button */; const r = b.getBoundingClientRect(); return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2}); })()")
import json; c = json.loads(rect)
cdp('Input.dispatchMouseEvent', type='mouseMoved', x=c['x'], y=c['y'])
cdp('Input.dispatchMouseEvent', type='mousePressed', x=c['x'], y=c['y'], button='left', clickCount=1)
cdp('Input.dispatchMouseEvent', type='mouseReleased', x=c['x'], y=c['y'], button='left', clickCount=1)
```
Two ways the coordinate path itself misfires, NEITHER of which means "the click failed":
- Stale coordinates: re-read `getBoundingClientRect()` immediately before dispatching - a scroll or lazy-render between reading and clicking makes the event land on whatever moved underneath.
- `cdp('Input.dispatchMouseEvent', ...)` can raise a timeout error. The harness link stalls while the page is actually navigating/submitting, so do NOT retry or assume failure - issue a fresh read and check state; in practice the click had already landed.

Always `scrollIntoView({block:'center'})` the target first so the
coordinates are on-screen, and re-check `window.location.href` a couple
seconds later rather than assuming the first dispatch worked instantly -
some of these transitions go through an async cart/API call before the
route actually changes.

When a submit click keeps doing nothing and the button is NOT disabled, stop cycling click methods and check what the page is actually waiting on: read the state of any consent/agreement checkboxes and required toggles on the step. A checkout submit can be silently gated on an unticked consent box that gives no error message at all - and a "select all" master checkbox is often coupled to a marketing-consent box, so ticking the master to pass the gate may also opt the user into marketing (untick that afterwards per the standing rule).

### The page may scroll in an inner container, not `window` - and touching a hidden field rewrites every rect you already read

`window.scrollTo(...)` is a no-op on SPAs whose layout puts the scroll on a wrapper div. Symptom: a control reports a rect hundreds of px below the viewport (or a negative `y`), no scroll you attempt moves it, and a CDP mouse event dispatched at those coordinates lands on whatever is really on screen there - which reads as "the button does not work". Find the real scroller and drive that one, then RE-READ the rect immediately before dispatching:

```js
[...document.querySelectorAll('*')].filter(e => e.scrollHeight > e.clientHeight + 20 && e.clientHeight > 300)
// then: el.scrollTop = el.scrollHeight  (or scrollIntoView({block:'center'}) on the target)
```

Related trap on multi-step forms that keep EVERY step in the DOM at once (later steps parked at a large `x` off the right edge, or at 0x0): `focus()` or `scrollIntoView()` on an element belonging to a hidden step scrolls the container to that step and shifts everything else, so every index (`querySelectorAll('input')[N]`) and every rect captured earlier is now stale - after which clicks land a control over (a neighbouring radio, a different step's button) with no error to show for it. Re-read the target's identity and position right before each interaction, and prefer a stable attribute (`formcontrolname`, `placeholder`, an id suffix) over positional indexes for anything you will touch more than once.

### Card number + CVV inside a cross-origin payment iframe: vault_fill can't reach them, but CDP attach-to-target can
Sites using a PCI-compliant hosted-fields payment widget (Stripe Elements, Adyen, Braintree, Amadeus payment SDK, etc.) render the card-number and CVV inputs inside `<iframe>`s served from the payment processor's own origin as out-of-process iframes (OOPIF) - a separate browser target, not a child node of the parent page's DOM. A vault-fill tool, plain `fill_input`, and light-DOM JS injection only ever see the parent frame's own DOM/accessibility tree, so they silently fill cardholder name / expiry / billing postcode but never touch the number/CVV, no matter how many times you retry or refocus.

The fields ARE reachable - attach directly to the iframe's own CDP target instead of going through the parent page:
```python
t = cdp('Target.getTargets')
pan_tid = [x['targetId'] for x in t['targetInfos'] if (x.get('url') or '').endswith('pan.html')][0]
sid = cdp('Target.attachToTarget', targetId=pan_tid, flatten=True)['sessionId']
# the field inside is usually id="value" on these SDKs - confirm via Runtime.evaluate first
cdp('Runtime.evaluate', session_id=sid, expression="(()=>{const v=document.getElementById('value');v.value='';v.focus();})()")
cdp('Input.insertText', session_id=sid, text='4111111111111111')
```
`Input.insertText` goes through the real input pipeline so the SDK's own masking/brand-detection reacts to it (plain `el.value=` assignment can stick but is less reliable and some SDKs ignore it). Do NOT click into the iframe area by coordinate from the parent page first - that routes the click to whatever's rendered behind/around the iframe in the parent frame and collapses/resets the form; attach-and-evaluate inside the iframe's own session avoids touching the parent at all.

This raw-CDP-insertText technique is useful for TESTING/demonstrating that a form can technically accept iframe input (throwaway card, e.g. 4111 1111 1111 1111) when the user explicitly asks for that kind of test. It is NOT a sanctioned way to enter a real card. The standing rule is: real card entry only via a vault-fill mechanism, which cannot reach this iframe at all. So for an ACTUAL purchase on a hosted-fields site: fill everything reachable (name, expiry, billing address), then stop - do not type the real number/CVV here even though you now know it's technically possible, and do not type a throwaway/test number either once money is actually on the line (that would mean submitting a real charge attempt with fake card data under the user's identity). Tell them the total, available methods, and that they have to type the number/CVV themselves on this one.

### Social-login popups ("Continue with Google/Apple") fail silently in a headless/remote Chrome
Any sign-in that uses a popup (`window.open`) - Google/Apple/Facebook SSO, some payment and 3-D Secure redirects - needs `--disable-popup-blocking` on the Chrome instance you automate. Without it the button does nothing visible: the site shows a generic "Something went wrong" and NO new CDP target ever appears. Confirm it is the blocker with `cdp('Target.getTargets')` - if no `accounts.google.com` (or other provider) target shows up after clicking, that is why.

Fix once in whatever launches your Chrome (add the flag to its launch args), then restart that Chrome service - open tabs just reload.

The popup is its own CDP target, and `js()` / `fill_input()` / `goto_url()` keep acting on the OPENER tab - so read and drive the popup through its own session:

```python
t = cdp('Target.getTargets')
tgt = [x for x in t['targetInfos'] if 'accounts.google.com' in (x.get('url') or '')][0]
sid = cdp('Target.attachToTarget', targetId=tgt['targetId'], flatten=True)['sessionId']
cdp('Runtime.evaluate', session_id=sid, returnByValue=True, expression="document.body.innerText")
# click INSIDE the popup with real mouse events at the element's rect centre:
cdp('Input.dispatchMouseEvent', session_id=sid, type='mousePressed', x=x, y=y, button='left', clickCount=1)
cdp('Input.dispatchMouseEvent', session_id=sid, type='mouseReleased', x=x, y=y, button='left', clickCount=1)
```

On the Google account chooser the rows are `div[role="link"][data-identifier="<email>"]` - a plain JS `.click()` on one often does nothing, so use the `Input.dispatchMouseEvent` sequence. When the same Chrome is signed into several Google accounts the chooser offers each one: confirm with the user which to use before picking. After the popup closes, re-check `Target.getTargets` to confirm you are back on the opener tab.

### Angular Material autocomplete (`mat-option`): click the option host, not a matched descendant text node
A `mat-autocomplete`/`mat-select` panel renders each choice as a `<mat-option>`
with the visible label nested in nested `<span>`s. Finding the right choice by
a generic text-walk (`textContent === 'the label'`) and calling `.click()` on
THAT span/div only updates the input's displayed text - Angular's selection
handler is bound to the `mat-option` host element itself, so the framework
never registers that a value was chosen. Symptom: the field visually shows the
correct text and looks filled, but a later validation/submit step rejects it
as wrong or unset, with no dropdown re-opening to blame. Fix: locate and click
the `mat-option` element directly - `document.querySelector('mat-option')`
(filter its list by `.textContent` when there are several) - never a
descendant found via a generic text-walk helper.

### Anti-bot challenge walls: enter via the bare homepage, not a deep link, and don't trust `capture_screenshot` during the wait
Some merchant sites (observed behind at least one common anti-bot vendor) show an "access temporarily restricted"/"checking your browser" challenge page INSTEAD of the real content when the very first navigation in a session goes straight to a deep sub-path URL that wasn't already "warmed up" - the challenge never resolves on that path. Fix: `goto_url` the bare domain root first, wait ~10-15s for it to clear (a text message, then a loading animation, then the real homepage), and only then navigate deeper via the site's own links/clicks rather than another raw URL. A results-page URL pattern you already know is safe (built from documented query params, e.g. a flight-search results URL) is fine to hit directly - it's unfamiliar deep links on a cold session that trigger the wall.

`capture_screenshot()` routinely times out while a page is mid-transition through one of these challenge/loading states - don't loop retrying it. Fall back to `page_info()` and `js("document.body.innerText.slice(0,...)")` to confirm real content has loaded, and only screenshot once the text content looks stable.

### A "download boarding pass/ticket" JS button produces no visible page change - intercept via CDP before clicking
Airline/booking sites that offer a download button for a boarding pass, e-ticket, or similar document often wire it to a pure JS blob download with no `href`/`data-url` on the button or its ancestors - clicking it with plain `el.click()` triggers no navigation, no new tab, and no visible DOM change, so polling `capture_screenshot()`/`page_info()` afterward looks exactly like a failed click. Set up download interception ONCE before clicking:
```python
cdp('Network.enable')
cdp('Page.setDownloadBehavior', behavior='allow', downloadPath='/path/to/downloads')
# then click the download button
```
The file lands in that directory a few seconds later - find it by `ls -t` / mtime, not by watching the page.

### An emailed "ticket-looking" PDF attachment is not necessarily the boarding pass - check what it actually contains
When a carrier emails a check-in/registration notification with a PDF attachment, the attachment is often the route itinerary / payment receipt (passenger name, flight, PNR - everything a boarding pass also shows at a glance), not the actual boarding pass with gate/sequence data the airport scans. The two documents can look identical from the filename and the email's subject line alone. Before handing an emailed attachment to the user as "the boarding pass", open it (render page images if it has no text layer, then run vision on them, or read the text if it does) and confirm it is titled/structured as a boarding pass, not an itinerary/receipt - if the site has a separate, explicit "download boarding pass" action (see above), that is the authoritative source, not whatever PDF happened to arrive by email.

### Visual grids (seat maps, calendars) decode by comparing CSS classes to the legend, not by asking vision to read the picture
A seat map renders every seat as an empty `<div>` whose only state is its CSS class (color = price tier / occupied / available) - there is no per-seat text or title attribute, so `vision_analyze` on a screenshot has to guess tiny colored squares and gives unreliable answers even with zoomed crops. Instead: find the legend rows (elements whose text is e.g. "occupied", "premium", "standard"), read `getComputedStyle()` on their color swatch, then read `getComputedStyle(cell).backgroundColor` for the row/column you care about and match it against the legend's swatch colors. This gives an exact, text-free classification for every cell in one pass instead of eyeballing a screenshot. See the `browser-data-extraction` skill for the general DOM leaf-text-dump technique this complements.
