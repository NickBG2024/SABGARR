"""Compare plugin SELECT with the actual Streamlit query using synthetic SQLite rows.
No production connection. SQLite supports this query's SQL constructs/NULL ordering.
"""
import pathlib, re, sqlite3
root = pathlib.Path(__file__).resolve().parents[2]
plugin = (root / 'wordpress/sabga-leagues/includes/class-sabga-leagues.php').read_text()
source = (root / 'database.py').read_text()
block = source.split('def display_cached_matchtype_standings(match_type_id):', 1)[1].split('\ndef ',1)[0]
streamlit_sql = re.search(r'query = """(.*?)"""', block, re.S).group(1).replace('%s','?')
plugin_sql = re.search(r"return '(SELECT .*?)';", plugin, re.S).group(1)
db = sqlite3.connect(':memory:')
db.executescript('''
CREATE TABLE Players(PlayerID INTEGER, Name TEXT, Nickname TEXT);
CREATE TABLE Fixtures(Player1ID INTEGER, Player2ID INTEGER, MatchTypeID INTEGER);
CREATE TABLE MatchTypePlayerStats(PlayerID INTEGER, MatchTypeID INTEGER, GamesPlayed INTEGER,
Wins INTEGER, Losses INTEGER, Points INTEGER, WinPercentage REAL, PRWins INTEGER,
AveragePR REAL, AverageLuck REAL, HeadToHeadScore INTEGER);
''')
for pid in range(1,12):
    db.execute('INSERT INTO Players VALUES(?,?,?)',(pid,f'Player {pid}',f'nick{pid}'))
    if pid < 11: db.execute('INSERT INTO Fixtures VALUES(?,?,91)', (pid,10))
db.execute('INSERT INTO Fixtures VALUES(11,10,92)')
# Cover points, wins, PR wins, H2H, PR and GamesPlayed tie steps, NULLs,
# a fixture-only player, a player belonging only to another league, duplicates.
stats = [
 (1,91,8,6,2,18,75,6,5.0,0.1,0),
 (2,91,8,5,3,17,62.5,7,6.0,0.1,0),
 (3,91,8,6,2,17,75,5,7.0,0.1,0),
 (4,91,8,6,2,17,75,6,8.0,0.1,0),
 (5,91,8,6,2,17,75,6,9.0,0.1,1),
 (6,91,8,6,2,17,75,6,6.0,0.1,0),
 (7,91,9,6,3,17,66.67,6,6.0,0.1,0),
 (8,91,8,6,2,17,75,6,None,None,0),
 (9,91,0,0,0,0,0,0,None,None,0),
 (11,92,1,1,0,3,100,1,4.0,0,0),
]
db.executemany('INSERT INTO MatchTypePlayerStats VALUES(?,?,?,?,?,?,?,?,?,?,?)', stats)
db.execute('INSERT INTO Fixtures VALUES(1,2,91)')
live = db.execute(streamlit_sql,(91,91)).fetchall()
cursor = db.execute(plugin_sql,(91,91))
new = [dict(zip([col[0] for col in cursor.description],r)) for r in cursor.fetchall()]
assert len(live) == len(new) == 10
assert [row[0] for row in live] == [row['name'] for row in new]
assert [r['player_id'] for r in new][:8] == [1,5,8,7,6,4,3,2]
for old,row in zip(live,new):
    vals = [row[k] for k in ('name','nickname','played','wins','losses','points','win_percentage','pr_wins','average_pr','average_luck','h2h')]
    assert tuple(vals) == old
assert next(row for row in new if row['player_id']==10)['stats_player_id'] is None
assert len(db.execute(plugin_sql,(92,92)).fetchall()) == 2
assert not db.execute(plugin_sql,(101,101)).fetchall()
assert plugin_sql.count('?') == 2
assert not re.search(r'\b(INSERT|UPDATE|DELETE|ALTER|CREATE|DROP)\b',plugin_sql,re.I)
print('PASS: SQL parity, all tie steps, NULL PR, zero games, fixture-only players, group isolation and SELECT-only query')
