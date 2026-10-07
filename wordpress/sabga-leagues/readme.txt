=== SABGA League Standings ===
Contributors: sabga
Requires at least: 6.0
Requires PHP: 7.4
Stable tag: 0.1.1
License: GPLv2 or later

Read-only proof of concept for the SABGA league website.

== Installation ==
Upload the ZIP in Plugins > Add New > Upload Plugin and activate it.
Add [sabga_leagues] to a private test page. Defaults to clearly labelled fictional demo data.
See IMPLEMENTATION.md for connecting SQL and validating real standings.

== Scope ==
2026 Series 4 standings only. All 11 groups supported. Fixtures, results, player
profiles and historical series will follow after this test passes.
Settings > SABGA Leagues controls demo/live mode, connection test and cache clearing.
No league database writes, no migrations, no changes to result processing.
