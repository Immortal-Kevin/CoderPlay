using System.Security.Cryptography;
using System.Text.Json;

namespace DesktopGoose.Core;

public sealed class GameStore : IDisposable
{
    private const string GooseColumns = "id,name,rarity,color,accent,pattern,temperament,born,released,status";
    private const string EggColumns = "id,parent,kind,laid,day,progress,stage,offspring,nest_x,nest_y";
    private readonly Sqlite db;
    private readonly IClock clock;
    private readonly IRandomSource random;
    private readonly string backups;
    private long Now => clock.Now.ToUnixTimeSeconds();

    public GameStore(string path, IClock clock, IRandomSource random)
    {
        this.clock = clock;
        this.random = random;
        string parent = Path.GetDirectoryName(Path.GetFullPath(path))!;
        Directory.CreateDirectory(parent);
        backups = Path.Combine(parent, "backups");
        db = new Sqlite(path);
        try
        {
            db.Exec("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;");
            Transaction(() =>
            {
                switch (Version(db))
                {
                    case 0:
                        using (var resource = typeof(GameStore).Assembly.GetManifestResourceStream("Core.Schema.sql")!)
                        using (var reader = new StreamReader(resource))
                            db.Exec(reader.ReadToEnd());
                        break;
                    case 1:
                        break;
                    default:
                        throw new InvalidOperationException("此存档需要更新版本的 Desktop Goose。");
                }
            });
        }
        catch
        {
            db.Dispose();
            throw;
        }
    }

    private static int Version(Sqlite db) => db.Query("PRAGMA user_version", row => row.Int(0)).Single();

    private void Transaction(Action action)
    {
        db.Exec("BEGIN IMMEDIATE");
        try
        {
            action();
            db.Exec("COMMIT");
        }
        catch
        {
            db.Exec("ROLLBACK");
            throw;
        }
    }

    private static Goose ReadGoose(Sqlite.Statement r) => new(r.Long(0), r.Text(1),
        new((Rarity)r.Int(2), r.Int(3), r.Int(4), r.Int(5)), (Temperament)r.Int(6), r.Long(7), r.Optional(8), r.Text(9));

    private static Egg ReadEgg(Sqlite.Statement r) => new(r.Long(0), r.Long(1), (EggKind)r.Int(2),
        r.Long(3), r.Text(4), r.Int(5), Enum.Parse<HatchStage>(r.Text(6)), r.Optional(7), r.Double(8), r.Double(9));

    public Goose? Resident => db.Query($"SELECT {GooseColumns} FROM goose WHERE status='resident'", ReadGoose).SingleOrDefault();
    public Goose? FindGoose(long id) => db.Query($"SELECT {GooseColumns} FROM goose WHERE id=?", ReadGoose, id).SingleOrDefault();
    public IReadOnlyList<Goose> Family() => db.Query($"SELECT {GooseColumns} FROM goose WHERE status!='pending' ORDER BY id", ReadGoose);
    public IReadOnlyList<Egg> Eggs() => db.Query($"SELECT {EggColumns} FROM egg ORDER BY laid DESC,id DESC", ReadEgg);
    public Egg? ActiveEgg => db.Query($"SELECT {EggColumns} FROM egg WHERE stage NOT IN ('STORED','COMPLETED')", ReadEgg).SingleOrDefault();
    public IReadOnlyList<Ability> Abilities(long goose) =>
        db.Query("SELECT action FROM ability WHERE goose=? ORDER BY action", r => (Ability)r.Int(0), goose);
    public bool DiamondUnlocked => db.Query("SELECT 1 FROM achievement_unlock WHERE key='diamond_nest'", r => r.Int(0)).Count > 0;

    public void Initialize(string name)
    {
        name = Production.Name(name);
        Transaction(() =>
        {
            if (Resident is not null)
                return;
            InsertGoose(name, new(Rarity.Common, 0, -1, 0), "resident");
            db.Run("INSERT INTO clock_state VALUES(1,?,?)", Now, clock.Zone.Id);
        });
    }

    private long InsertGoose(string name, Plumage look, string status)
    {
        db.Run("INSERT INTO goose(name,rarity,color,accent,pattern,temperament,born,status) VALUES(?,?,?,?,?,?,?,?)",
            name, look.Rarity, look.Color, look.Accent, look.Pattern, random.Next(4), Now, status);
        return db.InsertId;
    }

    public void Rename(string name) => db.Run("UPDATE goose SET name=? WHERE status='resident'", Production.Name(name));

    public Settings LoadSettings() => db.Query("SELECT value FROM settings WHERE key='game'",
        r => JsonSerializer.Deserialize<Settings>(r.Text(0))!).SingleOrDefault() ?? new();

    public void SaveSettings(Settings settings) => db.Run(
        "INSERT INTO settings VALUES('game',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", JsonSerializer.Serialize(settings));

    public int SettleProduction()
    {
        int produced = 0;
        Transaction(() => produced = Settle());
        return produced;
    }

    private int Settle()
    {
        var resident = Resident;
        if (resident is null)
            return 0;
        var (cursor, zoneId) = db.Query("SELECT settled,timezone FROM clock_state WHERE id=1",
            r => (r.Long(0), r.Text(1))).Single();
        long end = Now;
        if (end <= cursor)
            return 0;

        var currentZone = clock.Zone;
        TimeZoneInfo zone;
        try { zone = TimeZoneInfo.FindSystemTimeZoneById(zoneId); }
        catch (TimeZoneNotFoundException) { zone = zoneId == currentZone.Id ? currentZone : TimeZoneInfo.Utc; }

        int lifetime = db.Query("SELECT count(*) FROM egg WHERE parent=?", r => r.Int(0), resident.Id).Single();
        int made = 0;
        // Cursor and egg timestamps describe completed UTC seconds. The second
        // completing exactly at 04:00 belongs to the new production day.
        while (cursor < end && lifetime + made < Production.LifetimeLimit)
        {
            long first = cursor + 1;
            var day = Production.Day(first, zone);
            long nextDay = Production.Boundary(day.AddDays(1), zone);
            long last = Math.Min(end, nextDay - 1);
            if (last < first)
                last = first;

            string key = Production.Key(day);
            bool available = db.Query("SELECT 1 FROM egg WHERE day=?", r => r.Int(0), key).Count == 0;
            if (available)
            {
                long wait = Production.WaitSeconds(random);
                if (wait <= last - cursor)
                {
                    long time = cursor + wait;
                    db.Run("INSERT INTO egg(parent,kind,laid,day) VALUES(?,?,?,?)", resident.Id, resident.Look.EggKind, time, key);
                    db.Run("INSERT INTO production_event VALUES(?,?,?,?)", db.InsertId, resident.Id, key, time);
                    made++;
                }
            }
            cursor = last;
        }
        db.Run("UPDATE clock_state SET settled=?,timezone=? WHERE id=1", end, currentZone.Id);
        return made;
    }

    public void UnlockAbility(long goose)
    {
        Transaction(() =>
        {
            var existing = Abilities(goose);
            if (existing.Count >= 3 || random.Next(200) != 0)
                return;
            var choices = Enum.GetValues<Ability>().Except(existing).ToArray();
            db.Run("INSERT INTO ability VALUES(?,?,'unlocked',?)", goose, choices[random.Next(choices.Length)], Now);
        });
    }

    public bool Start(long id, double x, double y)
    {
        bool started = false;
        Transaction(() =>
        {
            if (ActiveEgg is not null)
                return;
            db.Run("UPDATE egg SET stage='INCUBATING',nest_x=?,nest_y=? WHERE id=? AND stage='STORED'", x, y, id);
            started = db.Changes == 1;
        });
        return started;
    }

    public void MoveNest(long id, double x, double y) =>
        db.Run("UPDATE egg SET nest_x=?,nest_y=? WHERE id=? AND stage IN ('INCUBATING','PAUSED','READY')", x, y, id);

    public void Pause(long id) => ChangeStage(id, HatchStage.INCUBATING, HatchStage.PAUSED);
    public void Resume(long id) => ChangeStage(id, HatchStage.PAUSED, HatchStage.INCUBATING);

    public void Count(long id, int count)
    {
        if (count <= 0)
            return;
        db.Run("""
            UPDATE egg SET progress=min(5000,progress+?),
                stage=CASE WHEN progress+?>=5000 THEN 'READY' ELSE stage END
            WHERE id=? AND stage='INCUBATING'
            """, count, count, id);
    }

    public void Recover() => db.Run("UPDATE egg SET stage='READY' WHERE stage='CRACKING'");

    public Goose? Crack(long id)
    {
        Goose? offspring = null;
        Transaction(() =>
        {
            var egg = ActiveEgg;
            if (egg?.Id != id || egg.Stage != HatchStage.READY)
                return;
            long child = egg.Offspring ?? InsertGoose("", RarityEngine.Offspring(egg.Kind, random), "pending");
            if (egg.Offspring is null)
            {
                db.Run("INSERT INTO hatch_transaction(egg,offspring) VALUES(?,?)", id, child);
                db.Run("UPDATE egg SET offspring=? WHERE id=?", child, id);
                if (Abilities(egg.Parent).Count == 0)
                    db.Run("INSERT INTO ability VALUES(?,?,'birth',?)", child, random.Next(6), Now);
            }
            ChangeStage(id, HatchStage.READY, HatchStage.CRACKING);
            offspring = FindGoose(child);
        });
        return offspring;
    }

    public HatchChoice Choice(long egg) => db.Query("SELECT offspring,keep FROM hatch_transaction WHERE egg=?",
        r => new HatchChoice(r.Long(0), r.Optional(1)), egg).Single();

    public void FinishCrack(long id) => ChangeStage(id, HatchStage.CRACKING, HatchStage.CHOOSE);

    public void Choose(long id, long keep)
    {
        Transaction(() =>
        {
            var egg = ActiveEgg;
            if (egg?.Id != id || egg.Stage != HatchStage.CHOOSE)
                return;
            if (keep != Resident?.Id && keep != egg.Offspring)
                throw new ArgumentException("请选择要留下的鹅。");
            db.Run("UPDATE hatch_transaction SET keep=? WHERE egg=?", keep, id);
            ChangeStage(id, HatchStage.CHOOSE, HatchStage.NAME_NEW);
        });
    }

    public void NameChild(long id, string name, Ability? inheritance)
    {
        name = Production.Name(name);
        Transaction(() =>
        {
            var egg = ActiveEgg;
            if (egg?.Id != id || egg.Stage != HatchStage.NAME_NEW)
                return;
            long child = Choice(id).Offspring;
            var options = Abilities(egg.Parent);
            if (options.Count != 0)
            {
                if (inheritance is not Ability selected || !options.Contains(selected))
                    throw new ArgumentException("请选择一项亲代特殊动作。");
                db.Run("INSERT INTO ability VALUES(?,?,'inherited',?)", child, selected, Now);
            }
            db.Run("UPDATE goose SET name=? WHERE id=?", name, child);
            ChangeStage(id, HatchStage.NAME_NEW, HatchStage.RELEASE);
        });
    }

    public void Release(long id)
    {
        Transaction(() =>
        {
            var egg = ActiveEgg;
            if (egg?.Id != id || egg.Stage != HatchStage.RELEASE)
                return;
            var (offspring, keep) = Choice(id);
            var old = Resident!;
            long leaving = keep == old.Id ? offspring : old.Id;
            Settle();
            db.Run("UPDATE goose SET status='released',released=? WHERE id=?", Now, leaving);
            db.Run("UPDATE goose SET status='resident' WHERE id=?", keep);
            if (FindGoose(leaving)!.Look.Rarity == Rarity.Legendary)
                db.Run("INSERT OR IGNORE INTO achievement_unlock VALUES('diamond_nest',?,?)", leaving, Now);
            ChangeStage(id, HatchStage.RELEASE, HatchStage.COMPLETED);
        });
    }

    private void ChangeStage(long id, HatchStage from, HatchStage to) =>
        db.Run("UPDATE egg SET stage=? WHERE id=? AND stage=?", to.ToString(), id, from.ToString());

    public Visit? PlanVisit(Settings settings)
    {
        if (!settings.Visits || Resident is not Goose resident)
            return null;
        string day = LocalDate;
        Visit? visit = null;
        Transaction(() =>
        {
            var record = db.Query("SELECT guest,resident,due,started FROM visit_event WHERE day=?",
                r => (r.Optional(0), r.Long(1), r.Optional(2), r.Optional(3)), day);
            if (record.Count != 0)
            {
                var (guest, host, due, started) = record[0];
                if (guest is long id && due is long time && started is null && host == resident.Id)
                    visit = new(id, host, time);
                return;
            }
            var eligible = db.Query("SELECT id FROM goose WHERE status='released' ORDER BY id", r => r.Long(0));
            if (eligible.Count == 0)
                return;

            if (random.Next(100) < settings.VisitChance)
                visit = new(eligible[random.Next(eligible.Count)], resident.Id, Now + 30 + random.Next(271));
            db.Run("INSERT INTO visit_event(day,guest,resident,due) VALUES(?,?,?,?)", day, visit?.Guest, resident.Id, visit?.Due);
        });
        return visit;
    }

    public bool BeginVisit(Visit visit)
    {
        db.Run("UPDATE visit_event SET started=? WHERE day=? AND guest=? AND resident=? AND due=? AND started IS NULL",
            Now, LocalDate, visit.Guest, visit.Resident, visit.Due);
        return db.Changes == 1;
    }

    public void FinishVisit(Visit visit) =>
        db.Run("UPDATE visit_event SET finished=? WHERE guest=? AND resident=? AND due=? AND started IS NOT NULL AND finished IS NULL",
            Now, visit.Guest, visit.Resident, visit.Due);

    public string LocalDate => Production.Key(DateOnly.FromDateTime(TimeZoneInfo.ConvertTime(clock.Now, clock.Zone).DateTime));

    public IReadOnlyList<string> Backups() => BackupFiles().Where(IsValidBackup).ToArray();

    private IReadOnlyList<string> BackupFiles() => Directory.Exists(backups)
        ? Directory.GetFiles(backups, "*.sqlite").OrderByDescending(Path.GetFileName).ToArray() : [];

    public string Backup() => Backup(null);

    private string Backup(string? preserve)
    {
        Directory.CreateDirectory(backups);
        string path = Path.Combine(backups, $"{clock.Now.UtcDateTime:yyyyMMdd-HHmmss-fffffff}-{Guid.NewGuid():N}.sqlite");
        string temporary = path + ".pending";
        try
        {
            using (var copy = new Sqlite(temporary))
            {
                db.BackupTo(copy);
                copy.Exec("PRAGMA journal_mode=DELETE;");
            }
            Verify(temporary);
            string hash = Hash(temporary);
            File.Move(temporary, path);
            File.WriteAllText(path + ".sha256", hash);
            db.Run("INSERT INTO backup_manifest VALUES(?,?,?,?)", Path.GetFileName(path), Now, hash, Version(db));
            var valid = Backups();
            foreach (string obsolete in valid.Where(file => file != preserve).Skip(preserve is null ? 7 : 6))
            {
                File.Delete(obsolete);
                File.Delete(obsolete + ".sha256");
                db.Run("DELETE FROM backup_manifest WHERE filename=?", Path.GetFileName(obsolete));
            }
            return path;
        }
        finally
        {
            File.Delete(temporary);
        }
    }

    public void Restore(string path)
    {
        if (!BackupFiles().Contains(path, StringComparer.OrdinalIgnoreCase) || !IsValidBackup(path))
            throw new InvalidOperationException("备份校验未通过。");
        using var source = new Sqlite(path, true);
        Backup(path);
        source.BackupTo(db);
        Recover();
    }

    private static string Hash(string path)
    {
        using var source = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(source));
    }

    private static bool IsValidBackup(string path)
    {
        try
        {
            if (!string.Equals(Hash(path), File.ReadAllText(path + ".sha256"), StringComparison.Ordinal))
                return false;
            Verify(path);
            return true;
        }
        catch (Exception error) when (error is IOException or InvalidOperationException or UnauthorizedAccessException)
        {
            return false;
        }
    }

    private static void Verify(string path)
    {
        using var copy = new Sqlite(path, true);
        if (Version(copy) != 1 || !copy.Query("PRAGMA integrity_check", r => r.Text(0)).SequenceEqual(["ok"]) ||
            copy.Query("PRAGMA foreign_key_check", _ => 1).Count != 0)
            throw new InvalidOperationException("SQLite 备份无效。");
    }

    public void Dispose() => db.Dispose();
}
