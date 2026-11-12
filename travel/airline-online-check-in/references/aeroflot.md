# Aeroflot online check-in (aeroflot.ru)

Companion to `aeroflot-booking`, which covers BUYING. Check-in is a separate funnel.

## Path

`aeroflot.ru` homepage -> `Онлайн-регистрация` ("Online check-in") tab -> `/info/checkin/` ->
`Зарегистрироваться онлайн` ("Check in online", an `<a href="/pnr/search">`) -> PNR search form ->
`/pnr/?pnrKey=...&pnrLocator=XXXXXX` -> `Онлайн-регистрация` button ->
`checkin/search_pnrs?pnr_locator=...` -> `checkin/registration?paxKey=...` ->
`Зарегистрироваться` ("Check in") -> baggage-rules page (`Продолжить` / "Continue") ->
`checkin/registration-data` = `Регистрация пройдена` ("Check-in complete").

- Cold-navigating straight to a deep path meets the anti-bot challenge page; go to the
  bare domain first and wait for it to clear, then move deeper via the site's own links
  (see `web-checkout`'s challenge-wall pitfall).
- The `Онлайн-регистрация` tab strip contains several duplicate nodes (hidden slides report
  zero-size rects, so a leaf-text search hits the wrong one). Click the visible one by
  screen coordinates, or skip the tab entirely and use the `Зарегистрироваться онлайн`
  anchor's `/pnr/search` href.
- PNR search form: `input[name='code']` (booking code) + `input[name='lastName']`
  (surname, Latin). React inputs - native setter + `input`/`change` works here.
- The passenger row already shows the pre-assigned seat; the button that completes
  check-in is `Зарегистрироваться`, followed by a baggage-rules page whose commit is
  `Продолжить`. Success is the text `Регистрация пройдена` plus
  `Скачать посадочный / Отправить на эл. почту / Распечатать` (download / send by email / print).

## Boarding pass

- `Скачать посадочный` ("Download boarding pass") is a pure JS blob download - no `href`, no navigation, so it looks
  like a dead button. Arm the download first:
  `cdp('Page.setDownloadBehavior', behavior='allow', downloadPath='/path/to/downloads')`,
  then click, then find the file by mtime. It lands as
  `BoardPass_<SURNAME>_<YYYY-MMM-DD>_<IATA>.pdf`.
- `Отправить на эл. почту` ("Send by email") is the e-mail alternative and is preferable per `web-checkout` -
  verify the mailbox afterwards rather than trusting the click.
- The PDF Aeroflot attaches to the "Открыта регистрация" ("Check-in is open") notification is the itinerary /
  receipt, NOT the boarding pass, despite a plausible `SURNAME_GIVENNAME.pdf` filename.
  The authoritative boarding pass is the one from `Скачать посадочный` (title
  `Boarding Pass`).
