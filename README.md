# agent-browser-skills

Battle-tested Agent Skills for browser automation with Claude / [Hermes](https://github.com/NousResearch/hermes-agent) and other agent frameworks that support the [Agent Skills](https://www.anthropic.com/news/skills) format (a `SKILL.md` with YAML frontmatter, picked up automatically by name/description).

These were written and refined while actually driving real websites - flight search aggregators, airline booking funnels, online check-in - through a Chrome instance controlled over the DevTools Protocol (CDP). Every pitfall documented here was hit for real: a click that silently failed, a shadow-DOM button `querySelector` couldn't see, a seat map with no text in it at all.

## What's in here

### `browser/` - general browser automation, any site

- **`browser-data-extraction`** - the core technique: dump every DOM leaf-text node instead of fighting selectors or screenshots. Covers reading JS-heavy pages (prices, filters, table rows), driving React/Angular apps with real input events instead of DOM mutation, and iterating over many URL variants reliably.
- **`web-checkout`** - the general shape of any online purchase flow: multi-step forms, payment pages, declining upsells, verifying that a click actually did something (this is the hard part, not clicking itself). Includes the full pitfalls list: shadow-DOM walking, Angular/Zone.js click escalation, cross-origin payment iframes (PCI hosted fields), anti-bot challenge walls, social-login popups blocked by default, download-button interception via CDP.

### `travel/` - airline-specific, built on top of `browser/`

- **`aeroflot-booking`** - buying a ticket on aeroflot.ru end to end: fare selection, passenger form quirks, the seat map (decoded purely from CSS classes, no text anywhere), payment. Comes with a ready-made `scripts/aeroflot_helpers.py` click/find/verify library you can drop into a session.
- **`airline-online-check-in`** - checking in on an already-bought ticket (different flow from buying: no payment, a seat map, a boarding pass at the end). Carrier-specific notes live under `references/` (Aeroflot, Bangkok Airways) so the main skill stays carrier-agnostic.

## Why publish this

Most of the value in an Agent Skill isn't the happy path - it's the list of things that looked like a bug but weren't (a verification check watching the wrong signal, not a broken click), and the two or three things that actually need an escalation (CDP mouse events, shadow-DOM traversal, attaching to a cross-origin iframe target directly). That knowledge is expensive to rediscover and cheap to hand over, so here it is.

## How to use

Drop a skill's folder into wherever your agent loads skills from (for Hermes: a `skills/` directory inside a profile, picked up automatically by its `name`/`description` frontmatter; for Claude Code / other Agent-Skills-compatible tools: wherever that tool looks for `SKILL.md` files). Each skill's `When to use` section explains when it should fire.

These assume a CDP-driven Chrome (`cdp(...)` calls, `js(...)` for evaluating JavaScript in-page) and a vault-style mechanism for payment data - adapt the exact tool calls to whatever your harness exposes, the techniques and pitfalls transfer regardless of the specific API shape.

## A note on what's NOT here

Some things were deliberately left out of this repo: anything tied to one person's accounts, personal data, or private infrastructure. What's published is the general technique - site navigation patterns, DOM/CDP quirks, verification strategies - stripped of any of that.

## License

MIT - see [LICENSE](LICENSE).
