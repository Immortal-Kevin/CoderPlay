// SPDX-License-Identifier: Apache-2.0
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
namespace TypingTrainer;
internal static class WindowAppearance
{
    [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr window,int attribute,ref int value,int size);
    [DllImport("user32.dll")] static extern IntPtr MonitorFromWindow(IntPtr window,uint flags);
    [DllImport("user32.dll",CharSet=CharSet.Auto)] [return:MarshalAs(UnmanagedType.Bool)] static extern bool GetMonitorInfo(IntPtr monitor,ref MonitorInfo info);
    [StructLayout(LayoutKind.Sequential)] struct NativeRect {public int Left,Top,Right,Bottom;}
    [StructLayout(LayoutKind.Sequential)] struct MonitorInfo {public int Size;public NativeRect Monitor,Work;public uint Flags;}
    public static void FitInitialWindow(Window window)
    {
        var handle=new WindowInteropHelper(window).Handle;
        var monitor=MonitorFromWindow(handle,2);var info=new MonitorInfo{Size=Marshal.SizeOf<MonitorInfo>()};
        if(!GetMonitorInfo(monitor,ref info))return;
        var source=HwndSource.FromHwnd(handle);if(source?.CompositionTarget==null)return;
        var transform=source.CompositionTarget.TransformFromDevice;
        var size=transform.Transform(new Vector(info.Work.Right-info.Work.Left,info.Work.Bottom-info.Work.Top));
        // Keep the requested DIP defaults when they fit; high DPI / smaller desktops need a usable title bar.
        window.Width=Math.Max(window.MinWidth,Math.Min(window.Width,size.X-24));
        window.Height=Math.Max(window.MinHeight,Math.Min(window.Height,size.Y-24));
        var origin=transform.Transform(new Point(info.Work.Left,info.Work.Top));
        window.WindowStartupLocation=WindowStartupLocation.Manual;
        window.Left=origin.X+Math.Max(0,(size.X-window.Width)/2);
        window.Top=origin.Y+Math.Max(0,(size.Y-window.Height)/2);
    }
    public static void NativeTitleBar(Window window,bool dark)
    {
        var handle=new WindowInteropHelper(window).Handle;if(handle==IntPtr.Zero)return;
        int mode=dark?1:0;DwmSetWindowAttribute(handle,20,ref mode,sizeof(int));
        int caption=dark?0x001D1410:-1;DwmSetWindowAttribute(handle,35,ref caption,sizeof(int));
        int text=dark?0x00FCFAF8:-1;DwmSetWindowAttribute(handle,36,ref text,sizeof(int));
    }
}
internal static class UiDialog
{
    public static bool Show(Window? owner,string message,string title,bool confirm=false)
    {
        Brush Get(string key,Brush fallback)=>owner?.TryFindResource(key) as Brush??Application.Current?.TryFindResource(key) as Brush??fallback;
        var window=new Window{Title=title,Width=480,MaxWidth=640,SizeToContent=SizeToContent.Height,MinHeight=170,ResizeMode=ResizeMode.NoResize,WindowStyle=WindowStyle.SingleBorderWindow,ShowInTaskbar=false,WindowStartupLocation=owner!=null?WindowStartupLocation.CenterOwner:WindowStartupLocation.CenterScreen,Background=Get("BackgroundBrush",new SolidColorBrush(Color.FromRgb(16,20,29))),Foreground=Get("ForegroundBrush",Brushes.White),FontFamily=new FontFamily("Microsoft YaHei UI"),FontSize=16};
        window.Resources.MergedDictionaries.Add(new ResourceDictionary{Source=new Uri("/TypingTrainer;component/UiTheme.xaml",UriKind.Relative)});
        foreach(var pair in new[]{("BackgroundBrush","#10141D"),("SurfaceBrush","#1A2230"),("ForegroundBrush","#F8FAFC"),("SecondaryBrush","#94A3B8"),("BorderBrush","#334155"),("AccentBrush","#2563EB"),("HoverBrush","#3B82F6"),("PressedBrush","#1D4ED8")})
            window.Resources[pair.Item1]=Get(pair.Item1,new SolidColorBrush((Color)ColorConverter.ConvertFromString(pair.Item2)));
        if(owner!=null)window.Owner=owner;
        var grid=new Grid{Margin=new Thickness(26)};grid.RowDefinitions.Add(new RowDefinition{Height=GridLength.Auto});grid.RowDefinitions.Add(new RowDefinition{Height=GridLength.Auto});
        grid.Children.Add(new TextBlock{Text=message,TextWrapping=TextWrapping.Wrap,MaxHeight=420,Margin=new Thickness(0,0,0,22)});
        var actions=new WrapPanel{HorizontalAlignment=HorizontalAlignment.Right};Grid.SetRow(actions,1);grid.Children.Add(actions);
        bool english=owner?.Language.IetfLanguageTag.StartsWith("en")==true;
        var ok=new Button{Content=confirm?(english?"Yes":"确定"):(english?"OK":"确定"),MinWidth=92,IsDefault=true};ok.Click+=(_,_)=>window.DialogResult=true;actions.Children.Add(ok);
        if(confirm){var cancel=new Button{Content=english?"Cancel":"取消",MinWidth=92,IsCancel=true};actions.Children.Add(cancel);}
        window.Content=grid;bool dark=(window.Background as SolidColorBrush)?.Color==Color.FromRgb(16,20,29);window.SourceInitialized+=(_,_)=>WindowAppearance.NativeTitleBar(window,dark);
        return window.ShowDialog()==true;
    }
}
