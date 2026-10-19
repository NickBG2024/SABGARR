"""Fixture/result SQL tests using synthetic data only."""
import json,os,sqlite3,subprocess
from pathlib import Path
queries=json.loads(subprocess.check_output([os.environ.get('SABGA_TEST_PHP','php'),str(Path(__file__).with_name('test-plugin.php')),'--matches-sql'],text=True))
db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
db.executescript('''
CREATE TABLE Players(PlayerID INT,Name TEXT,Nickname TEXT);
CREATE TABLE Fixtures(FixtureID INT,MatchTypeID INT,Player1ID INT,Player2ID INT,Completed INT);
CREATE TABLE MatchResults(MatchResultID INT,FixtureID INT,MatchTypeID INT,Date TEXT,Player1ID INT,Player2ID INT,Player1Points INT,Player2Points INT,Player1PR REAL,Player2PR REAL);
INSERT INTO Players VALUES(1,'Alpha','one'),(2,'Beta','two'),(3,'Gamma','three');
INSERT INTO Fixtures VALUES(1,91,1,2,0),(2,91,1,3,1),(3,92,1,2,1),(4,91,2,3,1),(5,91,1,2,0),(6,91,1,2,0);
INSERT INTO MatchResults VALUES
(10,2,91,'2026-10-01',3,1,8,11,NULL,4.5),
(11,3,92,'2026-10-02',1,2,11,4,5,6),
(12,5,91,'2026-10-03',1,2,11,4,3,4),
(13,6,92,'2026-10-04',1,2,11,4,3,4),
(14,2,91,'2026-10-01',3,1,11,8,8,9),
(15,999,91,'2026-10-05',1,2,11,4,3,4);
''')
fixtures=[dict(r) for r in db.execute(queries['fixtures'],(91,))]
assert len(fixtures)==5 and {r['fixture_id'] for r in fixtures}=={1,2,4,5,6}
assert next(r for r in fixtures if r['fixture_id']==5)['has_result']==1
assert next(r for r in fixtures if r['fixture_id']==6)['has_result']==0,'Mismatched result group does not mark fixture'
assert next(r for r in fixtures if r['fixture_id']==4)['has_result']==0,'Completed without result detectable'
results=[dict(r) for r in db.execute(queries['results'],(91,))]
assert [r['result_id'] for r in results]==[14,10],'Date and ID ordering; linked completed matches only'
r=results[1]
assert r['p1_id']==3 and r['p1_name']=='Gamma' and r['p1_score']==8 and r['p1_pr'] is None
assert r['p2_id']==1 and r['p2_name']=='Alpha' and r['p2_score']==11 and r['p2_pr']==4.5
assert not list(db.execute(queries['results'],(999,)))
assert all(q.upper().lstrip().startswith('SELECT') for q in queries.values())
print('PASS: fixtures/results group isolation, completion flags, anomalies, reversed result order, NULL PR, date/ID ordering, orphan exclusion and SELECT-only queries')
