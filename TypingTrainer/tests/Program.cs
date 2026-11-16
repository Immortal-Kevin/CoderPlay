// SPDX-License-Identifier: Apache-2.0
using System.IO.Compression;
using System.Text;
using System.Text.Json;
using TypingTrainer;
Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
var tests=new List<object>();int failed=0;
void Test(string name,Action action){try{action();tests.Add(new{name,status="PASS"});Console.WriteLine("PASS "+name);}catch(Exception e){failed++;tests.Add(new{name,status="FAIL",error=e.Message});Console.WriteLine("FAIL "+name+": "+e.Message);}}
void Eq<T>(T actual,T expected){if(!Equals(actual,expected))throw new Exception($"Expected {expected}, actual {actual}");}
void Near(double actual,double expected){if(Math.Abs(actual-expected)>.01)throw new Exception($"Expected {expected}, actual {actual}");}
void Throws(Action action){try{action();}catch{return;}throw new Exception("Expected exception");}
TrainingSession Session(string target,string input){var s=new TrainingSession(target);s.Update(input);return s;}
Test("Zero input has finite zero metrics",()=>{var m=new TrainingSession("abc").Measure(0);Near(m.Cpm,0);Near(m.FirstAccuracy,0);Near(m.FinalAccuracy,0);});
Test("CPM and WPM",()=>{var m=Session("abcde","abcde").Measure(30,true);Near(m.Cpm,10);Near(m.Wpm,2);});
Test("Early termination ignores untyped suffix",()=>{var m=Session("abcdef","abc").Measure(60);Near(m.FinalAccuracy,100);Near(m.Progress,50);Eq(m.Completed,3);});
Test("Substitution",()=>Near(Session("abc","axc").Measure(60,true).FinalAccuracy,200.0/3));
Test("Insertion uses edit distance",()=>Near(Session("abc","axbc").Measure(60,true).FinalAccuracy,75));
Test("Deletion uses edit distance",()=>Near(Session("abcd","acd").Measure(60,true).FinalAccuracy,75));
Test("Case sensitive",()=>Near(Session("A","a").Measure(60,true).FinalAccuracy,0));
Test("Unicode scalar count",()=>Eq(TrainingSession.Characters("中😀文").Length,3));
Test("Unicode final accuracy",()=>Near(Session("中😀文","中😀文").Measure(60,true).FinalAccuracy,100));
Test("Newline normalization",()=>Eq(TrainingSession.Normalize("a\r\nb\rc"),"a\nb\nc"));
Test("Whitespace significant",()=>Near(Session("a b","ab").Measure(60,true).FinalAccuracy,200.0/3));
Test("Corrections retain submitted errors",()=>{var s=Session("abc","ax");s.Update("a");s.Update("ab");Eq(s.Submitted,3L);Eq(s.Correct,2L);Near(s.Measure(60).FirstAccuracy,200.0/3);});
Test("Deletion creates no submission",()=>{var s=Session("abc","abc");s.Update("ac");Eq(s.Submitted,3L);});
Test("Insertion logs only new characters",()=>{var s=Session("abc","ac");s.Update("abc");Eq(s.Submitted,3L);});
Test("Composition batch logged once",()=>{var s=Session("中文","中文");s.Update("中文");Eq(s.Submitted,2L);});
Test("Identical replacement counts committed event",()=>{var s=Session("abc","a");s.RecordSubmission("a",0);s.Update("a",false);Eq(s.Submitted,2L);Eq(s.Correct,2L);});
Test("IME commit event not double counted",()=>{var s=new TrainingSession("中文");s.RecordSubmission("中文",0);s.Update("中文",false);Eq(s.Submitted,2L);});
Test("Pause rejects updates",()=>{var s=Session("abc","a");s.TogglePause();s.Update("ab");Eq(s.Input,"a");});
Test("Pause freezes stopwatch",()=>{var s=Session("abc","a");s.TogglePause();double first=s.Measure().Seconds;Thread.Sleep(80);Near(s.Measure().Seconds,first);});
Test("Resume restarts stopwatch",()=>{var s=Session("abc","a");s.TogglePause();double first=s.Measure().Seconds;s.TogglePause();Thread.Sleep(50);if(s.Measure().Seconds<=first)throw new Exception("Clock did not advance");});
Test("Excess input never exceeds 100 percent",()=>{var m=Session("a","aaaaaaaa").Measure(60,true);if(m.FinalAccuracy>100||m.Progress>100||m.FirstAccuracy>100)throw new Exception("Overflow");});
Test("Wrong text cannot inflate speed",()=>Near(Session("abc","xxx").Measure(60,true).Cpm,0));
Test("Empty target safe",()=>Near(new TrainingSession("").Measure(0).Progress,0));
Test("Negative duration clamped",()=>Near(Session("a","a").Measure(-1).Seconds,0));
Test("12 original built-ins",()=>{Eq(BuiltIns.All().Count,12);if(BuiltIns.All().Any(x=>string.IsNullOrEmpty(x.Text)))throw new Exception();});
var root=Path.Combine(Path.GetTempPath(),"TypingTrainer-test-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
try {
 var store=new Store(Path.Combine(root,"data"));var a=new Article("test","测试文章","Mixed","Hello 中文",false,DateTime.Now);
 Test("SQLite initialization",()=>Eq(store.Query("PRAGMA integrity_check;").Single(),"ok"));
 Test("Article persistence",()=>{store.Put(a);Eq(new Store(store.Root).Articles().Single(x=>x.Id==a.Id).Text,a.Text);});
 Test("Duplicate import rejected",()=>Throws(()=>store.Put(a with{Id="duplicate"})));
 Test("Settings JSON persistence",()=>{store.Settings.Language="en";store.SaveSettings();Eq(new Store(store.Root).Settings.Language,"en");});
 Test("Transactional result persistence",()=>{store.Save(a,true,Session(a.Text,a.Text).Measure(60,true));Eq(new Store(store.Root).Results().Count,1);});
 Test("Deleted article preserves history",()=>{store.Delete(a);Eq(store.Results().Single().Title,a.Title);});
 Test("Built-in cannot be deleted",()=>Throws(()=>store.Delete(BuiltIns.All()[0])));
 Test("Migration rejects nonempty destination",()=>{var dest=Path.Combine(root,"occupied");Directory.CreateDirectory(dest);File.WriteAllText(Path.Combine(dest,"keep.txt"),"keep");Throws(()=>store.Migrate(dest));Eq(File.ReadAllText(Path.Combine(dest,"keep.txt")),"keep");});
 Test("Network migration rejected before IO",()=>Throws(()=>store.Migrate(@"\\localhost\TypingTrainer-test")));
 Test("Future schema is not downgraded",()=>{store.Query("PRAGMA user_version=99;");try{Throws(()=>new Store(store.Root));Eq(store.Query("PRAGMA user_version;").Single(),"99");}finally{store.Query("PRAGMA user_version=1;");}});
 Test("Failed migration rolls back destination and root",()=>{string original=store.Root;string dest=Path.Combine(root,"failed-copy");store.Query("PRAGMA user_version=99;");try{Throws(()=>store.Migrate(dest));Eq(store.Root,original);Eq(Directory.Exists(dest),false);}finally{store.Query("PRAGMA user_version=1;");}});
 Test("Successful migration verifies database and settings",()=>{
   string pointer=Path.Combine(Store.DefaultRoot,"location.json");byte[]? before=File.Exists(pointer)?File.ReadAllBytes(pointer):null;
   try{string dest=Path.Combine(root,"migrated");store.Migrate(dest);Eq(store.Root,dest);Eq(new Store(dest).Settings.Language,"en");Eq(store.Query("PRAGMA integrity_check;").Single(),"ok");Eq(store.Results().Count,1);}
   finally{if(before==null){if(File.Exists(pointer))File.Delete(pointer);}else File.WriteAllBytes(pointer,before);}
 });
 Test("Backup retained on clear",()=>{store.Clear();Eq(store.Results().Count,0);if(!Directory.GetFiles(Path.Combine(store.Root,"backups")).Any())throw new Exception("Missing backup");});
 string Write(string name,byte[] bytes){var p=Path.Combine(root,name);File.WriteAllBytes(p,bytes);return p;}
 Test("UTF8 BOM TXT",()=>Eq(Importer.Read(Write("bom.txt",Encoding.UTF8.GetPreamble().Concat(Encoding.UTF8.GetBytes("中文\r\nabc")).ToArray())),"中文\nabc"));
 Test("UTF16LE TXT",()=>Eq(Importer.Read(Write("utf16.txt",Encoding.Unicode.GetPreamble().Concat(Encoding.Unicode.GetBytes("中文")).ToArray())),"中文"));
 Test("UTF16BE TXT",()=>Eq(Importer.Read(Write("utf16be.txt",Encoding.BigEndianUnicode.GetPreamble().Concat(Encoding.BigEndianUnicode.GetBytes("中文")).ToArray())),"中文"));
 Test("GB18030 manual TXT",()=>Eq(Importer.Read(Write("gb.txt",Encoding.GetEncoding("GB18030").GetBytes("中文")),"GB18030"),"中文"));
 Test("Empty TXT rejected",()=>Throws(()=>Importer.Read(Write("empty.txt",[]))));
 Test("Invalid UTF8 rejected",()=>Throws(()=>Importer.Read(Write("invalid.txt",[255,255,255]))));
 Test("Control character rejected",()=>Throws(()=>Importer.Read(Write("control.txt",[97,0,98]))));
 Test("Long text rejected",()=>Throws(()=>Importer.Read(Write("long.txt",Encoding.UTF8.GetBytes(new string('a',4001))))));
 Test("Legacy DOC honest rejection",()=>Throws(()=>Importer.Read(Write("legacy.doc",[1,2,3]))));
 Test("DOCX paragraphs tabs breaks",()=>{var p=Path.Combine(root,"good.docx");using(var zip=ZipFile.Open(p,ZipArchiveMode.Create)){using var writer=new StreamWriter(zip.CreateEntry("word/document.xml").Open());writer.Write("<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body><w:p><w:r><w:t>Hello</w:t><w:tab/><w:t>中</w:t><w:br/><w:t>X</w:t></w:r></w:p><w:p><w:r><w:t>End</w:t></w:r></w:p></w:body></w:document>");}Eq(Importer.Read(p),"Hello\t中\nX\nEnd");});
 Test("Corrupt DOCX rejected",()=>Throws(()=>Importer.Read(Write("broken.docx",[1,2,3]))));
 Test("DOCX external entity prohibited",()=>{var p=Path.Combine(root,"xxe.docx");using(var zip=ZipFile.Open(p,ZipArchiveMode.Create)){using var writer=new StreamWriter(zip.CreateEntry("word/document.xml").Open());writer.Write("<!DOCTYPE document [<!ENTITY x SYSTEM 'file:///C:/Windows/win.ini'>]><document>&x;</document>");}Throws(()=>Importer.Read(p));});
} finally {Directory.Delete(root,true);}
File.WriteAllText(Path.Combine(AppContext.BaseDirectory,"test-results.json"),JsonSerializer.Serialize(tests,new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine($"{tests.Count-failed} PASS / {failed} FAIL");return failed>0?1:0;
