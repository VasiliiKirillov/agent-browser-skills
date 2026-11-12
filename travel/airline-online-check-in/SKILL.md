---
name: airline-online-check-in
description: "Online check-in for a flight: seat choice, boarding pass."
tags: [browser, flights, checkin, boarding-pass, travel]
related_skills: [web-checkout, browser-data-extraction]
---

# Airline online check-in

## When to use

The user asks to check in for a flight they already booked ("check me in for the
flight", "online check-in", "boarding pass", "is check-in open yet"). This is a DIFFERENT task from
buying a ticket (`web-checkout` + the per-carrier booking skills): no payment step, a seat
map to pick from, and a boarding pass to deliver at the end. Seat/baggage/meal upsells are
the only money involved and are always declined unless they asked for them.

Carrier-specific flows live in `references/`; read the matching one before starting:

- `references/bangkok-airways.md` - HKT/USM etc., `digital.bangkokair.com/ssci/...`
- `references/aeroflot.md` - aeroflot.ru, PNR + surname entry

Start your browser session first. The PNR/booking code and the surname come from wherever
you track the user's bookings (a travel log, a previous message, etc.) - never make them
repeat a booking they already told you about.

## Procedure

1. Pull up the flight details: carrier, route, date, departure time, PNR/booking code,
   and the surname to use on the check-in form.
2. Say whether check-in is open yet (most carriers: 24h to 1h before departure; the
   carrier's page states it - e.g. Bangkok Airways prints `Check-in closes in Xh Ym`).
   Don't start before the window opens, it just fails.
3. Walk the flow (identification -> passenger/contact -> declarations -> seat ->
   boarding pass) per the carrier's reference file.
4. Pick the seat per the standing preference below before finishing.
5. Deliver the boarding pass (see standing rules) and report flight, seat, gate, boarding
   time.
6. Log the completed check-in (if you keep a travel/purchase log for the user) BEFORE the
   reply: route, flight number, date, departure/arrival time, SEAT, boarding time, gate, PNR,
   e-ticket number, sequence number. They will later ask for these expecting them to be on
   record somewhere.

## Standing rules

- **Seat preference:** ask the user once and remember it (a common one: aisle, in a side
  block, as far forward as possible, free/standard tier - never pay for a premium or
  "first rows" seat). On a 2+2 regional layout (ATR42/72) the aisle seats are B and C, not A
  and D: do not read "aisle" off the A/D columns. When a seat is already pre-assigned, check
  whether a free aisle seat exists further forward and change to it if that's their
  preference - a pre-assigned window seat is not automatically an answer to "aisle, please".
- **Boarding pass delivery:** prefer the carrier's "send by e-mail" option over a
  download button (`web-checkout`'s artifact rule). Send the PDF to the user in chat as well
  when they ask for it - but never as a screenshot, see pitfalls.
- **No paid extras.** Lounge, extra baggage, seat upgrades: decline/skip unless they asked.
- Any irreversible change beyond the check-in they requested (paying, cancelling,
  re-booking) needs their explicit yes first.

## Pitfalls

- **All steps of a stepper live in the DOM at once.** Hidden steps sit off to the side or
  at 0x0 and report nonsense geometry (large negative x, `y` past the viewport). Select
  controls by geometry - only those with a sane on-screen rect - not by raw
  `querySelectorAll(...)[N]` index.
- **Focusing or scrolling a hidden field re-lays out the page and silently invalidates
  every rect and index you read before.** Re-read position and index immediately before
  each action. Skipping this is how you click the wrong control: a different checkbox in
  the same row, a gender flip, or the *Departure* column of a form when you meant
  *Arrival*.
- **Reactive forms ignore programmatic value assignment.** Setting `.value` with the
  native setter + `input`/`change` events can show the text while the framework still
  treats the control as empty (`ng-pristine`, "This field is required" on submit). Type
  with real key events (CDP `Input.dispatchKeyEvent` per character) and verify via the
  framework's own state classes (`ng-pristine` -> `ng-dirty`/`ng-valid`) or the field's
  `.value` re-read - never by what the field looks like.
- **Seat maps encode availability in CSS classes, not text.** Match the class
  (`seat-characteristic-available` / `unavailable` / `selected`) and read the seat number
  from its own span. Clicking a seat usually only OPENS a details popup - the popup's own
  confirm button is what commits, and a separate "confirm selection and continue" button
  after that. A three-click dance where the first click "does nothing" is the normal shape.
- **The scroll container is often a `<div>`, not `window`.** `window.scrollTo` leaves
  below-the-fold buttons at `y` in the thousands. Scroll that container, or skip it and
  call `element.click()` directly - buttons fire from any scroll position.
- **E-mail input fields autofill and then concatenate your typing**
  (e.g. `USER@EXAMPLE.COM` + `user@example.com` glued together). Focus, Ctrl+A, Delete, verify `.value` is exactly
  the intended address, then type, then re-read before submitting.
- **An e-mailed "ticket-looking" PDF attachment may be an itinerary receipt, not a
  boarding pass.** Check the document title: a real boarding pass is titled `Boarding
  Pass` and carries SEQ / gate / boarding time. The carrier's explicit "download boarding
  pass" action is authoritative; the attachment that happens to arrive with a check-in
  notification is not.
- **Never deliver a screenshot of the boarding pass.** Airport security rejects
  screenshots (Bangkok Airways says so on the page itself). Send the PDF file.
- **Anti-bot walls** (Cloudflare Turnstile or a carrier's own challenge) render in a
  cross-origin OOPIF that is not in the light DOM: resolve it with
  `DOM.getFrameOwner` + `DOM.getBoxModel`, click the box centre with CDP mouse events,
  and verify via the challenge token input rather than a screenshot - `capture_screenshot`
  reliably times out while the challenge is mid-flight.
