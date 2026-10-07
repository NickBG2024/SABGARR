# SABGA league plugin: first test

Version 0.1.0 · Prepared 6 October 2026

This is an installable proof of concept for your existing WordPress website.
It shows standings for 2026 Series 4 (A–G and Guppy Yellow, Blue, Red and Green).
It reads your league database without altering players, fixtures, results or
statistics. The Streamlit service and result-processing scripts stay in place.

## 1. Try the display first — no database details needed

1. Download `sabga-leagues-0.1.0.zip`. Leave it zipped.
2. Sign into the WordPress dashboard for sabga.co.za.
3. Open **Plugins → Add New Plugin → Upload Plugin**, choose the ZIP, click
   **Install Now**, then **Activate Plugin**. If WordPress denies uploads, your
   site administrator can install the `sabga-leagues` folder into
   `wp-content/plugins/` using SFTP and activate it in the dashboard.
4. Create a page called **League test**. Make it **Private**, or use staging.
5. Insert a **Shortcode** block and paste:

   ```text
   [sabga_leagues]
   ```

6. Save and view the page while signed in. It will clearly say **Demo** and show
   fictional players. Switch between groups; all 11 intentionally use the same
   fictional example. This checks the display and navigation, not real results.
7. Check it on a phone. Swipe the table horizontally to see all columns.

No credentials are needed for this stage. The plugin defaults to demo mode.
Do not place the demo on your main public league page.

## 2. Prepare access to the real league database

Ask your Xneelo administrator to create a separate database user with **SELECT
permission only** on these existing league tables:

- `Players`: `PlayerID`, `Name`, `Nickname`
- `Fixtures`: `Player1ID`, `Player2ID`, `MatchTypeID`
- `MatchTypePlayerStats`: `MatchTypeID`, `PlayerID`, `GamesPlayed`, `Wins`,
  `Losses`, `Points`, `WinPercentage`, `PRWins`, `AveragePR`, `AverageLuck`,
  `HeadToHeadScore`

Use the **league database**, which may be separate from the WordPress database.
Use the hostname supplied by Xneelo for that database; do not assume localhost
just because both services are at Xneelo. The WordPress server must be allowed
to connect. If Xneelo's control panel does not offer a SELECT-only user, ask
support to arrange that permission. Do not reuse or change the account used by
the current result-processing scripts.

The WordPress server needs PHP 7.4 or later with **PDO MySQL** enabled. A current
supported PHP version is preferable. The settings page reports whether the
extension is available. Ask hosting support if it is missing.

## 3. Add credentials on the server

Have your site administrator back up `wp-config.php` and add the following
above its “That's all, stop editing” line. Replace the placeholders with the
new read-only user's details. These are **additional** constants; leave the
existing WordPress `DB_HOST`, `DB_NAME`, `DB_USER` and `DB_PASSWORD` unchanged.

```php
define('SABGA_LEAGUES_DB_HOST', 'YOUR_LEAGUE_DATABASE_HOST');
define('SABGA_LEAGUES_DB_NAME', 'YOUR_LEAGUE_DATABASE_NAME');
define('SABGA_LEAGUES_DB_USER', 'YOUR_READ_ONLY_USER');
define('SABGA_LEAGUES_DB_PASSWORD', 'YOUR_READ_ONLY_PASSWORD');
define('SABGA_LEAGUES_DB_PORT', 3306);
```

The host constant is a hostname or IP address, without `https://` or a port.
The database name is the database, not a table prefix. Preserve letter case
for table names. A password containing a single quote or backslash must be
properly escaped in a PHP string; have the administrator handle this.

For a remote database that requires encrypted connections, ask Xneelo for the
CA certificate and add its absolute server path:

```php
define('SABGA_LEAGUES_DB_SSL_CA', '/absolute/server/path/mysql-ca.pem');
```

The plugin verifies the server certificate when a CA is configured. Do not
disable verification to solve a certificate problem. Use hosting's advised
secure connection configuration.

Keep these values out of GitHub, the page editor and emails. You do not need to
send them to ChatGPT. If editing `wp-config.php` causes a site error, restore
the backed-up file immediately.

## 4. Switch the private page to live data

1. Open **Settings → SABGA Leagues**.
2. Confirm credentials are shown as **Configured** and PDO MySQL as **Available**.
3. Select **Live — league SQL database**, then **Save mode**.
4. Click **Test live A-League connection**. A success message reports the number
   of players read and elapsed connection/query time. This test bypasses the
   cache. It is not an end-to-end page speed measurement.
5. Reload your private test page. The demo banner should disappear and real
   names should appear. Changing a group loads just that group's standings.

Live/demo mode applies to every instance of this plugin on the website. The
default shortcode opens A-League. To start with B-League, use:

```text
[sabga_leagues group="92"]
```

Current IDs: A 91; B 92; C 93; D 94; E 95; F 96; G 97; Yellow 98;
Blue 100; Red 99; Green 101. Selecting a group also updates the page URL with
`?sabga_group=...` so you can share a group link.

## 5. Compare with Streamlit before making it public

Open https://sabgalive.streamlit.app and select **2026 — Series 4**.
For each of the 11 groups, compare:

- Names and number of players, including players with zero games.
- Positions, points, matches played, wins, PR wins, head-to-head scores and losses.
- Average PR, average luck, win percentage and points percentage.
- Tied players and any players with walkovers.

The query deliberately preserves the current Streamlit sort order:
**Points DESC → Wins DESC → PR wins DESC → H2H DESC → Average PR ASC →
Games played DESC**. Completely equal rows have no final deterministic
tiebreaker in the existing SQL; their relative order may vary in both displays.
Missing PR/luck values appear as a dash, rather than zero. The row number is
sequential, matching the current app; it is not a shared rank.

The plugin reads `MatchTypePlayerStats`, not newly calculated standings. Your
existing refresh process must keep that table up to date. During a normal new
result submission, check that the statistics update and the page catches up.
The website's own cache lasts up to 60 seconds. You can clear it from settings.
Clearing it **does not recalculate SQL statistics**. A warning appears if a
fixture-listed player has no precomputed stats row; that may be expected for a
new player, but should be checked.

“Standings fetched” tells you when the website read the table, not when the
statistics were last calculated. This proof of concept cannot confirm the
upstream refresh schedule or detect stale precomputed rows automatically.

## 6. Check loading speed

On the same device and network, compare the test page with Streamlit:

1. Open each page three times and note when the standings become usable.
2. Switch between groups and note response time.
3. Repeat on a phone.

The browser developer tools' Network panel will show requests containing
`sabga-leagues/v1/standings`. The first read opens one SQL connection and runs
one SELECT. Reads within 60 seconds can use the WordPress transient cache.
The browser revalidates on page load to avoid stale HTML from a page cache;
when SQL is cached, that does not mean a second SQL query.

Exclude this endpoint from any CDN/plugin REST caching. Browser requests and
successful endpoint responses ask not to be cached. If JavaScript is disabled,
the table and Show standings button still work with a full page reload; exclude
the test page from full-page caching in that case. When using default numeric
WordPress permalinks, the plugin preserves the page ID in the form.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| Shortcode appears as text | Plugin activated; use a Shortcode block, not a Code block |
| Credentials not configured | All four required constants in the site's active `wp-config.php` |
| PDO MySQL missing | Ask Xneelo to enable the extension for this site's PHP version |
| Unable to read standings | Correct host/name/port/user/password; network access; SELECT grants; exact table/column case |
| Empty league | The right database; Series 4 fixture rows for the selected ID |
| Mostly zero statistics | `MatchTypePlayerStats` has been refreshed by your existing process |
| Standings differ | Same series/group; clear website cache; inspect upstream stats; compare tied rows |
| Group switch fails, initial table works | Security/caching plugin allows the public GET REST route; check Network panel |
| Request times out | Hosting database connectivity; the client stops waiting after 12 seconds |
| Site error after editing config | Restore backed-up `wp-config.php` and ask administrator to correct PHP syntax |

Public error messages intentionally do not include database hostnames, SQL,
passwords or raw driver exceptions. This first version reports failures without
displaying old rows as if they belonged to a newly selected group.

## Rollback

Switch back to Demo for a display test, or deactivate **SABGA League Standings**
and remove the shortcode from the page. Your Streamlit app and league database
remain available. The plugin creates no league tables and changes no league
rows. WordPress stores only its display-mode option and temporary caches;
cached standings expire automatically. Remove the added constants if desired.

## What this test includes and what comes next

Included: installable plugin; all 11 current groups; server-rendered standings;
responsive table; shareable group links; public read-only REST display;
60-second caching; admin-only connection test and cache clearing; demo mode.

Next stages: fixtures, match results and grids; player summaries and PR charts;
historical series and annual PR tables. Future series will need a configurable
group catalogue; this version intentionally accepts only the current 11 IDs.
It does not add user accounts, membership payments or league administration.

## Developer notes

Source baseline: `NickBG2024/SABGARR` commit
`94a163f8bd968583c1f71a2e636b5b86e9530e04`, `SABGARRLive.py` and
`database.py:display_cached_matchtype_standings`. Credentials are independent of
Streamlit secrets. Prepared PDO parameters prevent group IDs being interpolated
into SQL. Public callers cannot supply SQL, table names or arbitrary group IDs.
Admin mutations require `manage_options` and a WordPress nonce. Player names
are escaped server-side and inserted as text in JavaScript.

The API returns only publicly displayed standings, not contact information.
On a private test page the route is still public, consistent with the existing
public Streamlit standings. Do not use this plugin for confidential leagues.

WordPress API references:
- https://developer.wordpress.org/reference/functions/add_shortcode/
- https://developer.wordpress.org/rest-api/extending-the-rest-api/adding-custom-endpoints/
- https://developer.wordpress.org/apis/transients/

Tests and their actual results are recorded separately in `VALIDATION.md`.

## Updating to 0.1.1 and diagnosing a failed connection

Upload `sabga-leagues-0.1.1.zip` in **Plugins > Add New > Upload Plugin**.
Choose **Replace current with uploaded** when WordPress finds the existing
plugin. The existing shortcode, display mode and wp-config.php constants remain
in place. Then open **Settings > SABGA Leagues**, save Live mode if necessary,
and click **Test live A-League connection**.

A failed test now adds an administrator-only diagnostic with the operation,
SQLSTATE, MySQL error number and guidance. Copy that diagnostic for support.
Do not send your password or the contents of wp-config.php. Public pages and
the public REST endpoint continue to receive the generic error only.

Use the existing RO account and database hostname shown in your Xneelo panel,
with the reset password for that RO account. There is no need to create an
additional user if the RO account already has SELECT access to the required tables.

## Compact standings — version 0.1.2

Upload `sabga-leagues-0.1.2.zip` and choose **Replace current with uploaded**.
The player column now follows the longest displayed name (including nickname)
in the selected group. Numeric columns use tighter spacing, and the fixed
1030-pixel minimum table width is removed. Smaller screens retain horizontal
scrolling where needed. No database or shortcode changes are required.
