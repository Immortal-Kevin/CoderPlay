using System.Runtime.InteropServices;

namespace DesktopGoose.Core;

// Uses the Windows 11 inbox SQLite library. Values are bound separately from SQL.
internal sealed class Sqlite : IDisposable
{
    private nint db;
    private const string Library = "winsqlite3.dll";
    private const int Row = 100;
    private const int Done = 101;

    public Sqlite(string path, bool readOnly = false)
    {
        int result = sqlite3_open_v2(path, out db, readOnly ? 1 : 6, 0);
        if (result != 0)
        {
            var error = Error(result);
            Dispose();
            throw error;
        }
        Check(sqlite3_busy_timeout(db, 3000));
        Exec("PRAGMA foreign_keys=ON;");
    }

    public void Exec(string sql)
    {
        Check(sqlite3_exec(db, sql, 0, 0, 0));
    }

    public void Run(string sql, params object?[] args)
    {
        using var statement = Prepare(sql, args);
        int result = sqlite3_step(statement.Handle);
        if (result != Done)
            throw Error(result);
    }

    public List<T> Query<T>(string sql, Func<Statement, T> map, params object?[] args)
    {
        using var statement = Prepare(sql, args);
        var values = new List<T>();
        int result;
        while ((result = sqlite3_step(statement.Handle)) == Row)
            values.Add(map(statement));
        if (result != Done)
            throw Error(result);
        return values;
    }

    public long InsertId => sqlite3_last_insert_rowid(db);
    public int Changes => sqlite3_changes(db);

    public void BackupTo(Sqlite destination)
    {
        nint backup = sqlite3_backup_init(destination.db, "main", db, "main");
        if (backup == 0)
            throw destination.Error(sqlite3_errcode(destination.db));
        int result = sqlite3_backup_step(backup, -1);
        int finish = sqlite3_backup_finish(backup);
        if (result != Done)
            throw destination.Error(result);
        destination.Check(finish);
    }

    private Statement Prepare(string sql, object?[] args)
    {
        Check(sqlite3_prepare_v2(db, sql, -1, out nint handle, 0));
        var statement = new Statement(handle);
        try
        {
            for (int i = 0; i < args.Length; i++)
            {
                int index = i + 1;
                int code = args[i] switch
                {
                    null => sqlite3_bind_null(handle, index),
                    string value => sqlite3_bind_text(handle, index, value, -1, -1),
                    double value => sqlite3_bind_double(handle, index, value),
                    var value => sqlite3_bind_int64(handle, index, Convert.ToInt64(value))
                };
                Check(code);
            }
            return statement;
        }
        catch
        {
            statement.Dispose();
            throw;
        }
    }

    private void Check(int code)
    {
        if (code != 0)
            throw Error(code);
    }

    private InvalidOperationException Error(int code) =>
        new($"SQLite ({code}): {Marshal.PtrToStringUTF8(sqlite3_errmsg(db))}");

    public void Dispose()
    {
        if (db != 0)
        {
            sqlite3_close_v2(db);
            db = 0;
        }
    }

    internal sealed class Statement(nint handle) : IDisposable
    {
        public nint Handle { get; } = handle;
        public long Long(int column) => sqlite3_column_int64(Handle, column);
        public int Int(int column) => checked((int)Long(column));
        public double Double(int column) => sqlite3_column_double(Handle, column);
        public long? Optional(int column) => sqlite3_column_type(Handle, column) == 5 ? null : Long(column);
        public string Text(int column) => Marshal.PtrToStringUTF8(sqlite3_column_text(Handle, column)) ?? "";
        public void Dispose() => sqlite3_finalize(Handle);
    }

    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_open_v2([MarshalAs(UnmanagedType.LPUTF8Str)] string path, out nint db, int flags, nint vfs);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_close_v2(nint db);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_busy_timeout(nint db, int milliseconds);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_exec(nint db, [MarshalAs(UnmanagedType.LPUTF8Str)] string sql, nint callback, nint arg, nint error);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_prepare_v2(nint db, [MarshalAs(UnmanagedType.LPUTF8Str)] string sql, int length, out nint statement, nint tail);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_step(nint statement);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_finalize(nint statement);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_bind_null(nint statement, int index);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_bind_int64(nint statement, int index, long value);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_bind_double(nint statement, int index, double value);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_bind_text(nint statement, int index, [MarshalAs(UnmanagedType.LPUTF8Str)] string value, int length, nint destructor);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern long sqlite3_column_int64(nint statement, int index);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern double sqlite3_column_double(nint statement, int index);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern nint sqlite3_column_text(nint statement, int index);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_column_type(nint statement, int index);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern nint sqlite3_errmsg(nint db);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_errcode(nint db);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern long sqlite3_last_insert_rowid(nint db);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_changes(nint db);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern nint sqlite3_backup_init(nint destination, string destinationName, nint source, string sourceName);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_backup_step(nint backup, int pages);
    [DllImport(Library, CallingConvention = CallingConvention.Cdecl)]
    private static extern int sqlite3_backup_finish(nint backup);
}
