CREATE TABLE goose (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  rarity INTEGER NOT NULL CHECK(rarity BETWEEN 0 AND 5),
  color INTEGER NOT NULL,
  accent INTEGER NOT NULL,
  pattern INTEGER NOT NULL,
  temperament INTEGER NOT NULL CHECK(temperament BETWEEN 0 AND 3),
  born INTEGER NOT NULL,
  released INTEGER,
  status TEXT NOT NULL CHECK(status IN ('resident','pending','released')),
  CHECK((status='released')=(released IS NOT NULL))
);
CREATE UNIQUE INDEX one_resident ON goose(status) WHERE status='resident';
CREATE TABLE egg (
  id INTEGER PRIMARY KEY,
  parent INTEGER NOT NULL REFERENCES goose(id),
  kind INTEGER NOT NULL CHECK(kind BETWEEN 0 AND 2),
  laid INTEGER NOT NULL,
  day TEXT NOT NULL UNIQUE,
  progress INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 5000),
  stage TEXT NOT NULL DEFAULT 'STORED'
    CHECK(stage IN ('STORED','INCUBATING','PAUSED','READY','CRACKING','CHOOSE','NAME_NEW','RELEASE','COMPLETED')),
  offspring INTEGER UNIQUE REFERENCES goose(id),
  nest_x REAL NOT NULL DEFAULT 0,
  nest_y REAL NOT NULL DEFAULT 0,
  CHECK(stage NOT IN ('READY','CRACKING','CHOOSE','NAME_NEW','RELEASE','COMPLETED') OR progress=5000)
);
CREATE UNIQUE INDEX one_hatch ON egg((1)) WHERE stage NOT IN ('STORED','COMPLETED');
CREATE TRIGGER lifetime_limit BEFORE INSERT ON egg
  WHEN (SELECT count(*) FROM egg WHERE parent=NEW.parent)>=5
  BEGIN SELECT raise(ABORT,'Lifetime egg limit'); END;
CREATE TABLE production_event (
  egg INTEGER PRIMARY KEY REFERENCES egg(id),
  goose INTEGER NOT NULL REFERENCES goose(id),
  day TEXT NOT NULL UNIQUE,
  occurred INTEGER NOT NULL
);
CREATE TABLE ability (
  goose INTEGER NOT NULL REFERENCES goose(id),
  action INTEGER NOT NULL CHECK(action BETWEEN 0 AND 5),
  source TEXT NOT NULL CHECK(source IN ('inherited','birth','unlocked')),
  acquired INTEGER NOT NULL,
  PRIMARY KEY (goose,action)
);
CREATE TRIGGER ability_limit BEFORE INSERT ON ability
  WHEN (SELECT count(*) FROM ability WHERE goose=NEW.goose)>=3
  BEGIN SELECT raise(ABORT,'Ability limit'); END;
CREATE TABLE hatch_transaction (
  egg INTEGER PRIMARY KEY REFERENCES egg(id),
  offspring INTEGER NOT NULL UNIQUE REFERENCES goose(id),
  keep INTEGER REFERENCES goose(id)
);
CREATE TABLE visit_event (
  day TEXT PRIMARY KEY,
  guest INTEGER REFERENCES goose(id),
  resident INTEGER NOT NULL REFERENCES goose(id),
  due INTEGER,
  started INTEGER,
  finished INTEGER
);
CREATE TABLE achievement_unlock (
  key TEXT PRIMARY KEY,
  goose INTEGER NOT NULL REFERENCES goose(id),
  occurred INTEGER NOT NULL
);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE clock_state (
  id INTEGER PRIMARY KEY CHECK(id=1),
  settled INTEGER NOT NULL,
  timezone TEXT NOT NULL
);
CREATE TABLE backup_manifest (
  filename TEXT PRIMARY KEY,
  created INTEGER NOT NULL,
  sha256 TEXT NOT NULL,
  schema_version INTEGER NOT NULL
);
PRAGMA user_version=1;
