// SPDX-License-Identifier: Apache-2.0
using System.IO;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Xml;
using System.Xml.Linq;
namespace TypingTrainer;
public sealed class Store
{
    public static string DefaultRoot => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TypingTrainer");
    static string Pointer => Path.Combine(DefaultRoot, "location.json");
    public string Root { get; private set; }
    public Preferences Settings { get; private set; } = new();
    public Store(string? explicitRoot = null)
    {
        Directory.CreateDirectory(DefaultRoot);
        Root = explicitRoot ?? (File.Exists(Pointer) ? JsonSerializer.Deserialize<string>(File.ReadAllText(Pointer))! : DefaultRoot);
        Initialize();
        var path = Path.Combine(Root,"config","settings.json");
        if (File.Exists(path)) Settings = JsonSerializer.Deserialize<Preferences>(File.ReadAllText(path)) ?? new();
    }
    void Initialize()
    {
        foreach (var folder in new[]{"articles","database","config","backups"}) Directory.CreateDirectory(Path.Combine(Root,folder));
        int version=int.Parse(Query("PRAGMA user_version;").Single());
        if(version>1)throw new IOException("数据库版本较新 / Database was created by a newer version");
        Sql("PRAGMA journal_mode=DELETE; BEGIN IMMEDIATE; CREATE TABLE IF NOT EXISTS articles(id TEXT PRIMARY KEY,json TEXT NOT NULL); CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY AUTOINCREMENT,json TEXT NOT NULL); PRAGMA user_version=1; COMMIT;");
        Backup();
    }
    public void SaveSettings() => Atomic(Path.Combine(Root,"config","settings.json"),JsonSerializer.Serialize(Settings));
    static void Atomic(string path,string content)
    { var temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp"; try { File.WriteAllText(temp,content,Encoding.UTF8); File.Move(temp,path,true); } finally { if(File.Exists(temp)) File.Delete(temp); } }
    public List<Article> Articles() => BuiltIns.All().Concat(Query("SELECT json FROM articles;").Select(x => JsonSerializer.Deserialize<Article>(x)!)).ToList();
    public void Put(Article article)
    {
        var duplicate = Articles().Any(x => x.Id != article.Id && x.Text == article.Text);
        if (duplicate) throw new InvalidOperationException("重复文章 / Duplicate article");
        Sql($"INSERT INTO articles VALUES({Q(article.Id)},{Q(JsonSerializer.Serialize(article))}) ON CONFLICT(id) DO UPDATE SET json=excluded.json;");
    }
    public void Delete(Article article) { if(article.BuiltIn) throw new InvalidOperationException("Built-in article"); Sql($"DELETE FROM articles WHERE id={Q(article.Id)};"); }
    public List<Result> Results() => Query("SELECT json FROM results ORDER BY id;").Select(x=>JsonSerializer.Deserialize<Result>(x)!).ToList();
    public Result Save(Article article, bool complete, Metrics metrics)
    {
        long number = Results().Select(x=>x.Number).DefaultIfEmpty(0).Max()+1;
        var result = new Result(number,DateTime.Now,article.Id,article.Title,complete,metrics);
        Sql($"BEGIN IMMEDIATE; INSERT INTO results(json) VALUES({Q(JsonSerializer.Serialize(result))}); COMMIT;"); Backup(); return result;
    }
    public void Clear() { Backup(true); Sql("BEGIN IMMEDIATE; DELETE FROM results; COMMIT;"); }
    public void Backup(bool force=false)
    {
        var source=Path.Combine(Root,"database","trainer.db"); var backup=Path.Combine(Root,"backups");
        if(!File.Exists(source)) return;
        if(!force && Directory.GetFiles(backup,"*.db").Any(x=>File.GetLastWriteTimeUtc(x)>DateTime.UtcNow.AddHours(-24)))return;
        File.Copy(source,Path.Combine(backup,DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fffffff")+".db"));
        foreach(var old in Directory.GetFiles(backup,"*.db").OrderByDescending(File.GetLastWriteTimeUtc).Skip(7)) File.Delete(old);
    }
    public void Migrate(string destination)
    {
        destination=Path.GetFullPath(destination);
        if(destination.StartsWith(@"\\",StringComparison.Ordinal)||new DriveInfo(Path.GetPathRoot(destination)!).DriveType==DriveType.Network)
            throw new IOException("仅支持本地磁盘目录 / Only local disk folders are supported");
        var current=Path.GetFullPath(Root).TrimEnd(Path.DirectorySeparatorChar);
        if(destination.TrimEnd(Path.DirectorySeparatorChar).Equals(current,StringComparison.OrdinalIgnoreCase))return;
        if(destination.StartsWith(current+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase) || current.StartsWith(destination.TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)) throw new IOException("请选择独立的空目录 / Choose a separate empty directory");
        if(Directory.Exists(destination)&&Directory.EnumerateFileSystemEntries(destination).Any())throw new IOException("目标目录必须为空，不会覆盖文件 / Destination must be empty");
        bool created = !Directory.Exists(destination); var copied=new List<string>();
        try {
            Directory.CreateDirectory(destination);
            foreach(var file in SafeFiles(Root)) {
                if((File.GetAttributes(file)&FileAttributes.ReparsePoint)!=0)throw new IOException("Reparse points are not supported");
                var relative=Path.GetRelativePath(Root,file); if(relative=="location.json")continue;
                var target=Path.Combine(destination,relative);Directory.CreateDirectory(Path.GetDirectoryName(target)!);File.Copy(file,target,false);copied.Add(target);
                if(!System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(file)).SequenceEqual(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(target))))throw new IOException("Copy verification failed");
            }
            var probe=new Store(destination); if(probe.Query("PRAGMA integrity_check;").Single()!="ok")throw new IOException("Database integrity check failed");
            Atomic(Pointer,JsonSerializer.Serialize(destination)); Root=destination;
        } catch { foreach(var file in copied)if(File.Exists(file))File.Delete(file); if(created&&Directory.Exists(destination))Directory.Delete(destination,true);throw; }
    }
    static IEnumerable<string> SafeFiles(string directory)
    {
        if((File.GetAttributes(directory)&FileAttributes.ReparsePoint)!=0)throw new IOException("Linked directories are not supported for migration");
        foreach(var file in Directory.GetFiles(directory))yield return file;
        foreach(var child in Directory.GetDirectories(directory))foreach(var file in SafeFiles(child))yield return file;
    }
    static string Q(string value)=>"'"+value.Replace("'","''")+"'";
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Callback(IntPtr user,int columns,IntPtr values,IntPtr names);
    [DllImport("winsqlite3.dll",CallingConvention=CallingConvention.Cdecl)] static extern int sqlite3_open([MarshalAs(UnmanagedType.LPUTF8Str)]string path,out IntPtr db);
    [DllImport("winsqlite3.dll",CallingConvention=CallingConvention.Cdecl)] static extern int sqlite3_close(IntPtr db);
    [DllImport("winsqlite3.dll",CallingConvention=CallingConvention.Cdecl)] static extern int sqlite3_exec(IntPtr db,[MarshalAs(UnmanagedType.LPUTF8Str)]string sql,Callback? callback,IntPtr user,out IntPtr error);
    [DllImport("winsqlite3.dll",CallingConvention=CallingConvention.Cdecl)] static extern void sqlite3_free(IntPtr memory);
    [DllImport("winsqlite3.dll",CallingConvention=CallingConvention.Cdecl)] static extern int sqlite3_busy_timeout(IntPtr db,int milliseconds);
    void Sql(string sql)=>Query(sql);
    public List<string> Query(string sql)
    {
        int status=sqlite3_open(Path.Combine(Root,"database","trainer.db"),out var db);
        try {
            if(status!=0)throw new IOException("Cannot open SQLite database: "+status);
            sqlite3_busy_timeout(db,3000); var rows=new List<string>();
            Callback callback=(_,count,values,_)=>{rows.Add(Marshal.PtrToStringUTF8(Marshal.ReadIntPtr(values))??"");return 0;};
            status=sqlite3_exec(db,sql,callback,IntPtr.Zero,out var error);
            if(status!=0) { string message=Marshal.PtrToStringUTF8(error)??"SQLite error";sqlite3_free(error);throw new IOException(message); }
            GC.KeepAlive(callback);return rows;
        } finally { if(db!=IntPtr.Zero)sqlite3_close(db); }
    }
}
public static class Importer
{
    public static string Read(string path,string encoding="auto")
    {
        if(new FileInfo(path).Length>4*1024*1024)throw new IOException("文件过大（最大 4 MB） / Maximum file size: 4 MB");
        string text; switch(Path.GetExtension(path).ToLowerInvariant()) {
            case ".txt":
                var bytes=File.ReadAllBytes(path);
                Encoding selected=encoding switch { "GB18030"=>Encoding.GetEncoding("GB18030",EncoderFallback.ExceptionFallback,DecoderFallback.ExceptionFallback),"UTF-16LE"=>new UnicodeEncoding(false,true,true),"UTF-16BE"=>new UnicodeEncoding(true,true,true),_=>new UTF8Encoding(false,true)};
                if(encoding=="auto") {
                    if(bytes.Length>=2&&bytes[0]==255&&bytes[1]==254)selected=new UnicodeEncoding(false,true,true);
                    else if(bytes.Length>=2&&bytes[0]==254&&bytes[1]==255)selected=new UnicodeEncoding(true,true,true);
                    else if(bytes.Length>=4&&bytes.Where((b,i)=>i%2==1&&b==0).Count()>bytes.Length/4)selected=new UnicodeEncoding(false,false,true);
                }
                text=selected.GetString(bytes).TrimStart('\uFEFF');break;
            case ".docx":
                using(var zip=ZipFile.OpenRead(path)) {
                    var entry=zip.GetEntry("word/document.xml")??throw new IOException("无效 DOCX / Invalid DOCX");
                    if(entry.Length>8*1024*1024)throw new IOException("DOCX expanded content too large");
                    using var stream=entry.Open(); using var reader=XmlReader.Create(stream,new XmlReaderSettings { DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=8*1024*1024 });
                    var doc=XDocument.Load(reader); XNamespace w="http://schemas.openxmlformats.org/wordprocessingml/2006/main";
                    text=string.Join("\n",doc.Descendants(w+"p").Select(p=>string.Concat(p.Descendants().Select(e=>e.Name==w+"t"?e.Value:e.Name==w+"tab"?"\t":e.Name==w+"br"||e.Name==w+"cr"?"\n":""))));
                } break;
            case ".doc":throw new NotSupportedException("DOC 旧版二进制格式暂不支持：未引入已核验许可证的解析器。请另存为 DOCX 或 TXT。 / Legacy DOC is unavailable; save as DOCX or TXT.");
            default:throw new NotSupportedException("TXT / DOCX only");
        }
        text=TrainingSession.Normalize(text);
        if(string.IsNullOrWhiteSpace(text))throw new IOException("文章为空 / Empty article");
        if(text.EnumerateRunes().Count()>4000)throw new IOException("最多 4000 个 Unicode 字符 / Maximum 4000 Unicode characters");
        if(text.Any(c=>char.IsControl(c)&&c!='\n'&&c!='\t'))throw new IOException("包含非法控制字符 / Invalid control characters");
        return text;
    }
}
