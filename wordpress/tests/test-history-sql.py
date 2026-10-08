"""Synthetic SQL checks for archive queries. No production connection."""
import json, os, sqlite3, subprocess
from pathlib import Path
php=os.environ.get('SABGA_TEST_PHP','php')
queries=json.loads(subprocess.check_output([php,str(Path(__file__).with_name('test-plugin.php')),'--history-sql'],text=True))
db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
db.executescript('''
CREATE TABLE Players(PlayerID INT,Name TEXT,Nickname TEXT);
CREATE TABLE Series(SeriesID INT,SeriesTitle TEXT);
CREATE TABLE SeasonSeries(SeasonID INT,SeriesID INT);
CREATE TABLE SeriesMatchTypes(SeriesID INT,MatchTypeID INT);
CREATE TABLE MatchType(MatchTypeID INT,MatchTypeTitle TEXT);
CREATE TABLE Fixtures(FixtureID INT,MatchTypeID INT);
CREATE TABLE MatchResults(MatchResultID INT,FixtureID INT,MatchTypeID INT,Player1ID INT,Player2ID INT,Player1Points INT,Player2Points INT,Player1PR REAL,Player2PR REAL);
INSERT INTO Players VALUES(1,'Same Name','one'),(2,'Same Name','two'),(3,'Other','other');
INSERT INTO Series VALUES(5,'2025 S1'),(8,'2025 S4'),(12,'2026 S3'),(13,'2026 S4');
INSERT INTO SeasonSeries VALUES(1,5),(1,8),(2,12),(2,13),(1,5);
INSERT INTO SeriesMatchTypes VALUES(5,51),(5,51),(8,81),(12,121),(13,131);
INSERT INTO MatchType VALUES(51,'A-League'),(81,'B-League'),(121,'A-League'),(131,'A-League');
INSERT INTO Fixtures VALUES(1,51),(2,51),(3,81),(4,121),(5,131);
INSERT INTO MatchResults VALUES(1,1,51,1,2,11,8,2,4),(2,2,51,1,2,8,11,NULL,8),(3,3,81,1,3,9,5,6,10),(4,4,121,1,2,8,11,100,200),(5,5,131,1,2,11,8,150,250);
''')
cat=list(db.execute(queries['catalog']));assert len(cat)==4, 'Duplicate catalog relationships removed'
annual=[dict(r) for r in db.execute(queries['annual'],(1,))]
p1=[r for r in annual if r['player_id']==1];assert sum(r['matches'] for r in p1)==2
assert sum(r['matches']*r['average_pr'] for r in p1)/sum(r['matches'] for r in p1)==4
assert len({r['player_id'] for r in annual})==3,'Same names stay separate'
pr=[dict(r) for r in db.execute(queries['pr'],(1,))]
assert len(pr)==2 and pr[0]['average_pr']==3 and pr[1]['average_pr']==8,'NULL pair excluded; correct averages'
player=[dict(r) for r in db.execute(queries['player'],(1,1))]
assert len(player)==2 and player[0]['played']==2 and player[0]['wins']==1 and player[0]['losses']==1
assert player[0]['pr_wins']==1 and player[0]['average_pr']==2
assert [r['league'] for r in player]==['A-League','B-League'],'Past groups from results, not current membership'
assert not list(db.execute(queries['player'],(999,1)))
assert not list(db.execute(queries['annual'],(999,)))
assert all(q.strip().upper().startswith('SELECT') for q in queries.values())
print('PASS: archive catalog, season isolation, NULL PR, weighted averages, distinct player identities, historical groups and SELECT-only queries')
