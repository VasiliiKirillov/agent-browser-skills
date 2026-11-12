# Bangkok Airways online check-in (`digital.bangkokair.com/ssci/...`)

Entry: `https://digital.bangkokair.com/ssci/identification?lang=en-GB`. The marketing
`bangkokair.com/pages/online-check-in` page is prose only, no form - don't hunt for a
button there. Check-in opens 24h to 1h before departure; the journey page prints
`Check-in closes in Xh Ym`, so confirm it is open before starting.

## Steps

1. **Identification** - `Booking reference` (6 alphanumeric / PNR) + `Last name` as on the
   ticket, then `I agree and start check-in`. -> `ssci/journey-selection`.
2. **Journey selection** - each pending journey has its own `Check in` button. It is a
   plain `<button>` whose only text lives in a `<span class="mdc-button__label">`, so match
   the button by trimmed `textContent`, never by class or by a leaf-text search.
3. **Passenger + contact** - passenger checkbox (pre-ticked) plus `Email`
   (example placeholder shown as `example@test.com`), `Country calling code`, `Phone number`. The country code is a
   typeahead: type the country name (e.g. `Russia`), then click the matching option (e.g. `Russia (+7)`). `Continue`.
4. **Dangerous goods** - long static list; the only action is `I agree and continue`,
   far below the fold.
5. **Required information** - `Nationality` typeahead per passenger (type, then click the
   option) plus the same email/phone block; each section flips to
   `Section correctly filled` when done. `Continue`.
6. **Seat map** (`ssci/services/seatmap/<flight>-<date>/N`) - see below.
7. **Extra services** - paid lounge etc.; skip and `Continue`.
8. **Checked in** - shows `Boarding <time> Gate <n>` plus
   `View boarding passes or confirmation documents`.

## Seat map

- Every seat is `button.seat-button` carrying a `.seat-number` span. Availability is
  class-based, never text: `seat-characteristic-available` = selectable,
  `seat-characteristic-unavailable` = taken, `selected selected-active` = currently
  assigned. Enumerate the available ones, sort by row, and take the lowest row whose
  column is the aisle.
- ATR42/72 (HKT-USM) is 2+2: A,B | aisle | C,D. A/D are window, **B/C are the aisle**.
- Price/position text exists only on free seats (`free-seat` class) and reads
  `Free of charge. Aisle seat.`; taken seats carry no such text.
- Selecting takes THREE clicks: (1) the seat button - only OPENS a details popup
  (`Seat 12C / Free of charge / <passenger> / Aisle seat`); (2) the popup's `Select seat`;
  (3) `Confirm seat selection and continue`. The pre-assigned seat stays `selected` until
  step 2 lands, so verify by re-reading which seat carries `selected`, not by the popup.

## Boarding pass delivery

`View boarding passes or confirmation documents` -> `Send boarding passes or confirmation
documents` -> tick the `Send by email in PDF format` checkbox (a `mat-checkbox` that
EXPANDS the section - it is not a submit) -> type the address -> `Add Email` ->
`Send boarding passes or confirmation documents`.

Confirmation mail: `Your Check-in Information` from
`noreply_onlinecheckin@bangkokair.com`, attachment
`Your flight information - BANGKOK AIRWAYS.pdf` - titled `Boarding Pass`, carries
SEQ / PNR / ETKT. A separate `Notify Seats Change of Booking <PNR>` mail arrives when you
change a seat; ignore it.

## Pitfalls

- **Scroll container is `.app-layout-container`, not `window`.** Controls below the fold
  report `getBoundingClientRect().y` in the thousands and `window.scrollTo` does not move
  them. Set that container's `scrollTop`, or just call `element.click()` directly.
- **E-mail field autofill** - Chrome can pre-fill an uppercase address and real keystrokes
  then append to it, producing a mangled combined string. Ctrl+A + Delete first, verify
  `.value`, then type. `Add Email` on a dirty field appends a blank extra row; drop it with
  `Remove Email`.
- Fields here are Material/Angular: `mat-select` opens on a JS click of the host and the
  option is a `mat-option` click; `mat-radio-button` needs a real mouse click on the
  button's rect (a JS click on the inner `input[type=radio]` does not register and can flip
  the selection to the wrong option).
