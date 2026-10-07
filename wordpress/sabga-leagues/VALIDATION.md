# Validation for version 0.1.1

Completed 6 October 2026 against source commit
`94a163f8bd968583c1f71a2e636b5b86e9530e04`.

## Diagnostic update — 7 October 2026

85 PHP harness checks and PHP syntax validation passed, including fixed guidance
for authentication, access, missing tables/columns, networking and TLS errors;
untrusted driver messages and codes are excluded; public errors retain only
HTTP status data; private diagnostics reset on every payload call. A real
local connection refusal was recorded privately. SQL parity was rerun and passed.
The browser assets are unchanged; the browser results below were obtained for
0.1.0. No live Xneelo connection has been tested from this workspace.

## Original display checks completed

- PHP 8.3.6 syntax checks passed for the entrypoint, plugin class and test harness.
- 57 isolated PHP harness checks passed: shortcode registration, all 11 groups,
  invalid/array/SQL-like inputs, points percentage, NULL vs zero PR, missing
  precomputed rows, demo labels, accessible headings, group links, default
  numeric permalink fallback, REST validation and GET-only registration,
  cache hit/bypass, admin capability guard, missing credentials, connection
  failure and no credential/hostname leakage in returned errors.
- SQL parity passed using SQLite with synthetic data. The actual query from
  `database.py:display_cached_matchtype_standings` and this plugin's query
  produced the same ordered rows and all 11 displayed data fields. Fixtures
  included duplicate appearances, a player with no statistics row, zero-game
  players, NULL PR/luck and an unrelated league. Every tiebreak step was covered.
- JavaScript syntax check passed.
- Chromium 153 through Playwright passed 17 simulated API requests: all 11 group
  selectors, table rows, missing PR, shareable URL changes, rapid-selection race,
  player-name HTML injection rendered as plain text, failed request clearing
  old rows, retry recovery, and mobile scrolling without page-wide overflow.
  Viewports: 1280×900 and 390×844. No browser JavaScript errors were recorded.
- ZIP builder checks archive integrity and the expected top-level plugin folder.

## What these checks do not prove

The PHP harness substitutes WordPress functions; it is not a full WordPress
installation. The browser uses actual PHP-rendered markup, CSS and JavaScript,
with generated demo payloads replacing network responses. The SQL comparison
uses SQLite, not Xneelo's MySQL. No production credentials were used.

The following still require the private WordPress test described in the guide:

- Installation and activation in your actual WordPress/theme/plugin environment.
- Xneelo connectivity, PDO extension availability, MySQL version and permissions.
- Real standings equality and upstream statistics refresh after a new result.
- End-to-end speed improvement compared with the live Streamlit app.
- Hosting-specific caching, REST restrictions and TLS configuration.

## Reproduce locally

From the repository root, using PHP with PDO MySQL, Python 3 and Node with
Playwright plus an available Chromium installation:

```sh
php -l wordpress/sabga-leagues/sabga-leagues.php
php -l wordpress/sabga-leagues/includes/class-sabga-leagues.php
php wordpress/tests/test-plugin.php
python3 wordpress/tests/test-sql.py
node --check wordpress/sabga-leagues/assets/standings.js
php wordpress/tests/test-plugin.php --render > wordpress/tests/preview.html
for id in 91 92 93 94 95 96 97 98 99 100 101; do
  php wordpress/tests/test-plugin.php --payload "$id" > "wordpress/tests/payload-$id.json"
done
```

In one terminal, serve `wordpress`:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory wordpress
```

In another, run:

```sh
node wordpress/tests/test-browser.cjs
python3 wordpress/build.py --output-dir /absolute/path/to/output
```

If using a separate Chromium binary, set `CHROMIUM_EXECUTABLE_PATH` before the
browser command. The harness's live-connection failure test deliberately uses
local port 1 and fake credentials. It never uses production credentials.
