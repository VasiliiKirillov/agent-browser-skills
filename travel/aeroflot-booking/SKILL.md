---
name: aeroflot-booking
description: "Buy a ticket on aeroflot.ru: page flow, form quirks, bugs."
tags: [browser, aeroflot, flights, booking]
related_skills: [web-checkout, browser-data-extraction]
---

# Aeroflot.ru booking flow

## When to use

The user asks to search or buy flight tickets on aeroflot.ru specifically. For
other airlines' sites or the general purchase-flow rules, see `web-checkout`.

Site-specific companion to `web-checkout` (general purchase-flow rules: decline
marketing checkboxes, stop at payment, etc. - read that skill first, this one
only adds aeroflot.ru's own quirks). Start your browser session first.

Ready-made click/find/fill library for this site: `scripts/aeroflot_helpers.py`
in this skill. Copy it into your workspace as `agent_helpers.py` at the start
of a run so it auto-imports `find()`, `smart_click()`, `set_input()`, `state()`,
`body_text()`, `shot()` - or adapt it to however your harness loads helpers.

## Click reliability: the clicks were never the problem, the VERIFICATION was

A full round-trip booking run (search city A -> city B) lands every single click - fare
class, "Select", every "Continue", gender, checkboxes, seat cell, seat price, "Pay",
shadow-DOM "Show" - with plain `el.click()` on the leaf element that carries
the text. No CDP mouse events, no parentElement walking, no
TreeWalker is needed anywhere on aeroflot.ru. Earlier runs that reported
"clicks silently fail" were misdiagnosed: the click worked, the success check
did not see it, the code escalated, and the EXTRA clicks toggled state back off
(a second click on a checkbox or a gender button undoes the first). Escalation
itself was the bug.

So: pick a verification signal that actually moves for the control you clicked,
and only escalate when that signal stays put.

- navigation/step change -> `location.href` (this site changes the URL on every
  real step transition, including the payment subdomain's `#/checkout/` -> `#/payment/`)
- checkbox / radio -> `input.checked`, NEVER innerText (consent boxes change no
  visible text at all - that is exactly what produced the phantom "no-change")
- gender / any two-`<button>` binary -> `className` diff between the two buttons
- seat commit -> the summary text flips from "not selected" to `<price> · <seat>`
- modal open/close -> presence of a field only that modal has, e.g.
  a surname input with an example-name placeholder

Fold checkbox state and button classNames into the page-state hash used for
"did anything change" (`scripts/aeroflot_helpers.py` `H.state()` does this);
an innerText-only hash reports false negatives on half this site's controls.

Keep the escalation ladder (native l0 -> native nearest clickable ancestor ->
synthetic pointerdown/up sequence -> CDP `Input.dispatchMouseEvent` at a
FRESHLY re-read `getBoundingClientRect()` -> CDP at each ancestor level) as a
fallback only, and log which rung won. If a run ever reports a rung other than
`native-l0` on aeroflot.ru, suspect the verification predicate before believing
the DOM changed behaviour.

When re-injecting the helper JS mid-run, carry `window.__hb._last` over to the
new object. A fresh `__hb` drops the element array the index-based click API
points into, and every later attempt dies on `Cannot read properties of
undefined` - which then looks like yet another "failed click".

aeroflot.ru itself is Ant Design + styled-components in the LIGHT DOM: shadow
DOM only starts at the payment subdomain. Prefer `tag='BUTTON'` and the generated
`ant-btn-primary` class to disambiguate; do not reach for shadow-DOM walking
before the payment host.

## Page sequence (URLs to recognize where you are)

1. `aeroflot.ru/` - search form (skip it entirely, enter via the results URL below)
2. `aeroflot.ru/sb/search?routes=<FROM>.<YYYYMMDD>.<TO>&...` - flight list + fares
3. `aeroflot.ru/sb/passengers?segments=...` - passenger data modal, then contacts form
4. `aeroflot.ru/sb/passengers/seats?pnrKey=...&pnrLocator=XXXXXX` - seat map (PNR already created here, note the locator)
5. `aeroflot.ru/sb/passengers/ancillary?...` - paid add-ons (baggage, insurance; no food options observed on long-haul economy)
6. `pay.aeroflot.ru/aeropayment/payment3/#/checkout/<uuid>` - order review, "Pay"
7. `pay.aeroflot.ru/aeropayment/payment3/#/payment/<uuid>` - payment method picker
8. after the user pays -> redirects to `aeroflot.ru/sb/upsale-welcome/?pnrLocator=XXXXXX` - this IS the success signal, no separate "confirmed" page to find

## Step 1-2: search - drive the results URL, never the home form

Open the results URL directly and skip the home page entirely (its origin/destination
autocompletes and the date calendar cost many rounds for nothing):

    https://www.aeroflot.ru/sb/search?routes=<FROM>.<YYYYMMDD>.<TO>&ADT=1&CHD=0&INF=0&INS=0&tripType=OW&selectedCurrency=RUB&market=ru&lang=ru

e.g. `routes=LED.20270115.AER`. The page redirects itself to the same URL plus
`&cabin=economy&adults=1&...` and renders the fare list with the right cities
and date. No cookie banner appears on this entry path.

## Step 2: fare selection

- Fare sub-options are collapsed. Click the class-name leaf (the `<P>` whose text is
  exactly the economy-class label) of the flight row you want - one such element exists per
  flight, in document order, so index 1 of a text-match search (the `<P>`, not the
  wrapper `<DIV>` at index 0) belongs to the first flight.
- That reveals three fare sub-tiers (basic/standard/flexible), each with its own "Select". Do NOT
  pick a "Select" button by x-coordinate guesswork - map each one to its fare by walking
  up to 12 ancestors until one's `innerText` matches the tier name pattern
  (the match sits 2-4 levels up). Click the `<BUTTON>` of the chosen column.
- List all three prices and their baggage/refund terms before asking the user to
  pick - most users want the terms spelled out, not just the price.
- Then click the page-level "Continue" (`<BUTTON>`, outside the fare box) ->
  lands on `/sb/passengers`.

## Step 3: passenger data modal

`/sb/passengers` first shows only contact fields and consent boxes. Click the
passenger card to open the passenger modal; verify it opened by the appearance
of a surname input carrying an example-name placeholder.

**Never hardcode input indexes.** The modal's DOB / passport-number / expiry
inputs all have `placeholder=''` and are only reachable positionally, but their
absolute index depends on how many contact inputs and checkboxes precede them
(this shifted between runs). Anchor on the one field that IS identifiable and count forward:

    base = index of the surname input (example placeholder, e.g. 'IVANOV')
    base+0 surname      base+1 given name (example placeholder, e.g. 'IVAN')
    base+2 date of birth    base+3 document type (read-only, e.g. 'domestic passport')
    base+4 series+number    base+5 expiry date

Assert `base+3`'s value really is the document-type string before writing to
`base+4`/`base+5`; if it is not, the layout moved and the offsets are stale.

All values go in via the native-setter + `input`/`change` dispatch (plain
`.value=` is ignored by the React form):

```js
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
setter.call(el, '01.01.1990');
el.dispatchEvent(new Event('input', {bubbles:true}));
el.dispatchEvent(new Event('change', {bubbles:true}));
```

Dates go in as `DD.MM.YYYY`, passport numbers stick verbatim including any space the format
expects - no masking surprises.

### Gender: one click, verified by className diff

The gender choice is two plain `<button>`s with no `checked`/`aria-pressed`. Unselected
both carry the same generated class; the selected one swaps its second class
(a styled-components hash, different hash on select). Snapshot both classNames,
click ONCE with `el.click()`, re-read: a successful click shows the two buttons
no longer sharing a className. Do not re-click on a "no change" verdict derived
from innerText - a second click can flip the selection back and that is the
real cause of the old "gender never registers" bug.

The modal's own "Continue" (the primary-styled one; a second,
default-styled "Continue" belongs to the page behind it) saves and closes
the modal. Confirm by the passenger summary line appearing in the page text
(name, DOB, passport) - then click the PAGE's "Continue" too.

## Step 3: contact fields (email/phone)

With the modal closed the page has exactly three text inputs:

- `[0]` email, has an example-mail placeholder - native-setter fill.
- `[1]` narrow (~78px) country-code box - NOT the phone field. Click it to open
  the country list, then click the appropriate entry in
  `document.querySelectorAll('.dropdown-item')` (index 0 is usually an empty header row,
  the real country entries start after it). Verify by `[1]`'s value
  becoming the country name and the `.dropdown-item` list emptying.
- `[2]` the real phone input - fill with bare national digits,
  no country code and no formatting. The field self-formats on its own.

## Step 3: consent checkboxes - exact click sequence

Five checkbox inputs in document order:

    0 master "I have read and agree to the terms and conditions"
    1 contract terms / carriage rules      (required)
    2 fare rules / cancellation policy     (required)
    3 transit passenger notice             (required)
    4 "I agree to receive marketing/promotional messages"  MARKETING

Exactly two clicks, in this order: click `0` (ticks all five), then click `4`
(unticks marketing). Final state is `1,2,3 = true`, `0,4 = false`, which is the
correct, submittable state - the master going false is cosmetic (it only
reflects "all children ticked") and "Continue" accepts it. Do not try to
"repair" the master afterwards: re-ticking it re-enables marketing.

Verify these by `.checked`, never by innerText - this is where a text-only
change detector reports a phantom failure and triggers destructive re-clicks.

## Step 4: seat map

Clicking the page "Continue" on `/sb/passengers` CREATES THE PNR and lands on
`/sb/passengers/seats?pnrKey=...&pnrLocator=XXXXXX`. Note the locator; a payment
countdown (~55 min) starts here and is shown on every later page.

### Decoding the map

Seat cells are empty `<div>`s whose only class is a styled-components hash -
no seat id, no aria-label, no title. Classify by
background colour against the legend, re-read every run (both the hashes and
the prices change between runs):

1. Legend swatches are the same-class divs with a large `x` offset (right-hand panel); the
   map's own cells are all further left.
2. For each swatch walk up to 6 ancestors until one has short `innerText` -
   that text is the tier label plus its price. Do NOT try to pair swatches
   to labels by y-coordinate: labels and swatches
   live in different stacking contexts and the y values do not line up.
3. Build `backgroundColor -> tier`, then classify every map cell by its own
   `getComputedStyle().backgroundColor`. Observed tiers (illustrative, re-read them
   each run): premium-forward, extra-legroom, standard economy, occupied.
4. Row numbers are the same divs whose text matches `^\d{1,2}$`
   (printed on both sides of the cabin); column letters are leaf elements whose
   text matches `^[A-K]$`. Assign each cell its row by nearest row-label
   y-centre (tolerance ~12px) and its column by nearest column-letter x-centre
   (~16px). Add `window.scrollY`/`scrollX` to every rect before matching, or
   rows scrolled out of view mis-bind.

Apply the user's standing seat preference (see `web-checkout`): aisle seat in a side block,
as far forward as possible, standard tier (never pay the first-rows or
premium-tier markup). On a 3-4-3 wide-body economy layout that typically means a specific
aisle column letter per side; sort the standard-tier candidates for that column by row number
and take the lowest.

### Two clicks, and the second one is a real button

The first click on a seat cell only opens a confirmation panel in the right
column (seat number, "aisle seat" label, a photo, and a big price button). It
does not select anything. The commit control is a real
primary button whose label IS the price - find it with a currency-amount
regex and click the `<BUTTON>` match, not the `<SPAN>` or
the wrapper `<DIV>`s that share the same text (the price may use a narrow
no-break space, so a plain `\d \d` pattern can miss it).

Verify the commit by the left summary flipping from "not selected" to
`<price> · <seat>` and by the order total rising by the seat price.

Then "Continue" TWICE: the map is a modal with its own primary-styled
"Continue" that only closes it (URL unchanged - this is NOT a failed click),
and the page beneath has its own default-styled "Continue" that actually
navigates to `/sb/passengers/ancillary`.

## Step 5: ancillary (add-ons)

- Cards offered typically include: extra baggage, flight insurance, medical
  insurance, sports equipment, pet transport. Only the flight
  insurance forces a choice; everything else can simply be left alone.
- No per-passenger meal selection exists for economy on long-haul here - don't
  look for a meal-selection card, tell the user food isn't sold separately.
- Decline insurance by clicking the text option that declines flight
  insurance (per `web-checkout`'s add-on rule). It is backed by a real
  `input[type=radio]` - index 1 of the two on the page - so verify with
  `.checked`, not by looks.
- "Continue" here leaves aeroflot.ru entirely for
  `pay.aeroflot.ru/aeropayment/payment3/#/checkout/<uuid>`. The JS context is
  destroyed mid-navigation, so any injected helper object vanishes and the next
  `js()` call throws an undefined-property error - that exception is
  the SUCCESS signal here, not a failure. Re-inject and re-read the URL.

## Steps 6-7: payment - shadow DOM everywhere

The whole checkout+payment UI is built on custom elements - use a recursive
shadow-DOM walk for every lookup here; `document.querySelectorAll('button')` returns
almost nothing useful on these two pages. `scripts/aeroflot_helpers.py`'s `find()` already
walks shadow roots, and its `nclick()` auto-prefers `el.shadowRoot.querySelector('button')`
when the host is a custom element.

- The review page shows the PNR (booking code), the countdown
  (time remaining to pay) and the total. Clicking "Pay"
  (a custom button element) moves the hash route to `#/payment/<uuid>` - that hash
  change is the verification signal.
- The payment page initially lists only a few methods (installment plans,
  QR-code payment, co-brand card promo). An "other payment methods"
  accordion is collapsed - click it to reveal the rest. Enumerate
  the full list for the user only after expanding it.
- Method tiles are div elements with an outer class naming the method - match
  that outer class, not the visible text that sits several levels deeper.
- A QR-code method's QR is behind a "Show" button; other methods may have an
  identical one further down, so take the first in document order for the one
  you want. Revealing the QR is read-only and safe; screenshot and deliver it
  per `web-checkout`'s artifact rule.

## Testing the flow without paying

The whole flow can be exercised end-to-end for free: everything up to and
including the payment-method list creates only an unpaid PNR, which expires by
itself in ~50 minutes with no charge, no email obligation and no need to cancel
anything. Stop at the method list (revealing a QR code is fine), never scan or
confirm. Keep the run tight anyway - once the countdown lapses the order flips
to an "order cannot be paid" state and the whole flow must restart from search.

## Confirming payment succeeded

After the user says they paid, re-check the current page/URL instead of asking for proof - a successful payment auto-redirects from `pay.aeroflot.ru/.../payment/...` to `aeroflot.ru/sb/upsale-welcome/?pnrLocator=XXXXXX` (an upsell/cross-sell page, safe to ignore its offers) - that redirect itself IS the confirmation, no separate "success" banner to find.

The `upsale-welcome` redirect is the trigger for `web-checkout`'s mandatory logging step, and it comes before the chat reply:

1. Read `pnrLocator` off the URL.
2. Log the purchase - route, flight number, date, departure/arrival time, seat, PNR, price paid (exact approach in `web-checkout`, section "Logging the purchase").
3. Only then report the PNR locator back to the user as the booking reference.
4. Shut down your browser session after logging, not before - a completed booking has been lost this way when the flow went confirmation -> reply -> browser shutdown and the turn simply ended with nothing logged.
