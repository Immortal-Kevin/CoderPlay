// SPDX-License-Identifier: Apache-2.0
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using System.Windows;
using Microsoft.Win32;
public static class Installer
{
    const string Key=@"Software\Microsoft\Windows\CurrentVersion\Uninstall\TypingTrainer";
    static string InstallRoot=>Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","TypingTrainer");
    static string Shortcut=>Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs),"Typing Trainer.lnk");
    [STAThread] public static int Main(string[] args)
    {
        try {
            bool silent=args.Contains("--silent");
            if(args.Contains("--uninstall-worker")) {
                Uninstall();if(!silent)MessageBox.Show("卸载完成，训练数据已保留。\nUninstalled. Personal data was preserved.");return 0;
            }
            if(args.Contains("--uninstall")) {
                if(!silent&&MessageBox.Show("卸载 Typing Trainer？训练数据将保留。\nUninstall Typing Trainer? Personal data will be kept.","Typing Trainer",MessageBoxButton.YesNo)!=MessageBoxResult.Yes)return 0;
                string worker=Path.Combine(Path.GetTempPath(),"TypingTrainer-uninstall-"+Guid.NewGuid().ToString("N")+".exe");
                File.Copy(Environment.ProcessPath!,worker);
                Process.Start(new ProcessStartInfo(worker,"--uninstall-worker"+(silent?" --silent":"")){UseShellExecute=false,CreateNoWindow=true});return 0;
            }
            if(args.Contains("--verify-payload")){using var resource=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip")!;using var zip=new ZipArchive(resource);return zip.GetEntry("TypingTrainer.exe")!=null&&zip.GetEntry("LICENSE")!=null?0:1;}
            if(!silent&&MessageBox.Show("将安装到当前用户目录，无需管理员权限。\nInstall for the current user without administrator rights?\n"+InstallRoot,"Typing Trainer 1.0",MessageBoxButton.OKCancel)!=MessageBoxResult.OK)return 0;
            Install();if(!silent)MessageBox.Show("安装完成，请从开始菜单启动。\nInstalled. Open Typing Trainer from the Start menu.");return 0;
        } catch(Exception e){if(!args.Contains("--silent"))MessageBox.Show(e.Message,"Typing Trainer Setup");return 1;}
    }
    static void Install()
    {
        if(Directory.Exists(InstallRoot)&&Directory.EnumerateFileSystemEntries(InstallRoot).Any())throw new IOException("安装目录已存在，请先卸载。\nInstallation already exists. Uninstall first.");
        string staging=InstallRoot+".stage-"+Guid.NewGuid().ToString("N");Directory.CreateDirectory(staging);bool moved=false;
        try {
            using(var resource=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip")!)using(var zip=new ZipArchive(resource))zip.ExtractToDirectory(staging);
            var files=Directory.GetFiles(staging,"*",SearchOption.AllDirectories).ToDictionary(p=>Path.GetRelativePath(staging,p),p=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))));
            string self=Environment.ProcessPath!;File.Copy(self,Path.Combine(staging,"Uninstall.exe"));files["Uninstall.exe"]=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(self)));
            File.WriteAllText(Path.Combine(staging,"install-manifest.json"),JsonSerializer.Serialize(files));
            if(Directory.Exists(InstallRoot))Directory.Delete(InstallRoot);Directory.Move(staging,InstallRoot);moved=true;
            Type shellType=Type.GetTypeFromProgID("WScript.Shell")!;dynamic shell=Activator.CreateInstance(shellType)!;dynamic shortcut=shell.CreateShortcut(Shortcut);shortcut.TargetPath=Path.Combine(InstallRoot,"TypingTrainer.exe");shortcut.WorkingDirectory=InstallRoot;shortcut.Save();
            using var key=Registry.CurrentUser.CreateSubKey(Key);key.SetValue("DisplayName","Typing Trainer");key.SetValue("DisplayVersion","1.0.0");key.SetValue("InstallLocation",InstallRoot);key.SetValue("UninstallString","\""+Path.Combine(InstallRoot,"Uninstall.exe")+"\" --uninstall");key.SetValue("NoModify",1);key.SetValue("NoRepair",1);
        } catch {if(moved) { if(File.Exists(Shortcut))File.Delete(Shortcut);Registry.CurrentUser.DeleteSubKeyTree(Key,false);Directory.Delete(InstallRoot,true); } else if(Directory.Exists(staging))Directory.Delete(staging,true);throw;}
    }
    static void Uninstall()
    {
        var files=JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(InstallRoot,"install-manifest.json")))!;
        // Only remove unchanged installer-owned files, and only beneath the fixed installation directory.
        foreach(var item in files) {
            string file=Path.GetFullPath(Path.Combine(InstallRoot,item.Key));
            if(!file.StartsWith(InstallRoot+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new IOException("Invalid manifest path");
            if(!File.Exists(file))continue;
            if(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(file)))==item.Value) {
                for(int retry=0;;retry++){try{File.Delete(file);break;}catch(IOException)when(retry<50){Thread.Sleep(100);}}
            }
        }
        if(File.Exists(Shortcut))File.Delete(Shortcut);Registry.CurrentUser.DeleteSubKeyTree(Key,false);File.Delete(Path.Combine(InstallRoot,"install-manifest.json"));
        foreach(var dir in Directory.GetDirectories(InstallRoot,"*",SearchOption.AllDirectories).OrderByDescending(p=>p.Length))if(!Directory.EnumerateFileSystemEntries(dir).Any())Directory.Delete(dir);
        if(!Directory.EnumerateFileSystemEntries(InstallRoot).Any())Directory.Delete(InstallRoot);
    }
}
