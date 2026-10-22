=== SABGA League Standings ===
Contributors: sabga
Requires at least: 6.0
Requires PHP: 7.4
Stable tag: 0.3.1
License: GPLv2 or later

Read-only proof of concept for the SABGA league website.

== Installation ==
Upload the ZIP in Plugins > Add New > Upload Plugin and activate it.
Add [sabga_leagues] to a private test page. Defaults to clearly labelled fictional demo data.
See IMPLEMENTATION.md for connecting SQL and validating real standings.

== Scope ==
2026 Series 4 standings only. All 11 groups supported. Standings, outstanding fixtures and results are available for the current
groups. Historical series, annual PR tables and player records use [sabga_history].
Settings > SABGA Leagues controls demo/live mode, connection test and cache clearing.
No league database writes, no migrations, no changes to result processing.

== Historical records ==
Add [sabga_history] to a separate full-width page. Includes previous standings, annual PR rankings, league PR matrix and selected-season player records. Draft release for testing.

== Fixtures and Results ==
Version 0.3.1 adds Standings / Remaining Fixtures / Results navigation to both
current leagues and each previous historical series/group, with player filters.
