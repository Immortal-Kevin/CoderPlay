// SPDX-License-Identifier: Apache-2.0
using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using TypingTrainer;
public static class UiTests
{
    [STAThread] public static int Main(string[] args)
    {
        RenderOptions.ProcessRenderMode=System.Windows.Interop.RenderMode.SoftwareOnly;
        string root=Path.Combine(Path.GetTempPath(),"TypingTrainer-ui-"+Guid.NewGuid().ToString("N"));
        string output=Path.GetFullPath(args.FirstOrDefault()??"ui-evidence");Directory.CreateDirectory(output);
        var app=new Application();var store=new Store(root);var window=new MainWindow(store);int fail=0;var log=new List<object>();
        void Invoke(string method,params object?[] parameters)=>typeof(MainWindow).GetMethod(method,BindingFlags.Instance|BindingFlags.NonPublic)!.Invoke(window,parameters);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(window)!;
        void Check(string name,Action action){try{action();log.Add(new{name,status="PASS"});Console.WriteLine("PASS "+name);}catch(Exception e){fail++;log.Add(new{name,status="FAIL",error=e.GetBaseException().Message});Console.WriteLine("FAIL "+name+" "+e.GetBaseException().Message);}}
        void Drain(){window.Dispatcher.Invoke(()=>{},DispatcherPriority.ApplicationIdle);window.UpdateLayout();}
        void Render(string name,int width,int height,double dpi=96)
        {
            window.Width=width;window.Height=height;Drain();
            var content=(FrameworkElement)window.Content;content.Measure(new Size(width-16,height-40));content.Arrange(new Rect(0,0,width-16,height-40));content.UpdateLayout();
            var bitmap=new RenderTargetBitmap((int)((width-16)*dpi/96),(int)((height-40)*dpi/96),dpi,dpi,PixelFormats.Pbgra32);bitmap.Render(content);
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using var stream=File.Create(Path.Combine(output,name+".png"));encoder.Save(stream);
            if(content.ActualWidth<=0||content.ActualHeight<=0)throw new Exception("Empty layout");
        }
        try {
            Check("Default 1280x800 minimum 900x600 native resizable window",()=>{if(window.Width!=1280||window.Height!=800||window.MinWidth!=900||window.MinHeight!=600||window.WindowStyle!=WindowStyle.SingleBorderWindow||window.ResizeMode!=ResizeMode.CanResize)throw new Exception("Window configuration differs");});
            window.Show();Drain();
            Check("Initial window fits available high-DPI work area",()=>{if(window.Width>SystemParameters.WorkArea.Width+1||window.Height>SystemParameters.WorkArea.Height+1)throw new Exception("Startup window exceeds work area");Render("home-default",(int)window.Width,(int)window.Height);});
            File.WriteAllText(Path.Combine(output,"display-environment.json"),JsonSerializer.Serialize(new{PrimaryLogicalWidth=SystemParameters.PrimaryScreenWidth,PrimaryLogicalHeight=SystemParameters.PrimaryScreenHeight,WindowLeft=window.Left,WindowTop=window.Top,WindowWidth=window.Width,WindowHeight=window.Height,DpiX=VisualTreeHelper.GetDpi(window).PixelsPerInchX,DpiY=VisualTreeHelper.GetDpi(window).PixelsPerInchY,WorkArea=SystemParameters.WorkArea.ToString(),Note="Offscreen DPI renders do not change actual Windows display DPI."},new JsonSerializerOptions{WriteIndented=true}));
            Check("Home rendered 1920x1080",()=>Render("home-1920",1920,1080));
            Check("Minimum window layout 900x600",()=>Render("home-minimum",900,600));
            Check("Home menu centered and four buttons fit minimum window",()=>{var p=Field<StackPanel>("page");var content=(FrameworkElement)window.Content;var bounds=p.TransformToAncestor(content).TransformBounds(new Rect(p.RenderSize));if(Math.Abs(bounds.Top+bounds.Height/2-content.ActualHeight/2)>2)throw new Exception("Menu not vertically centered");var buttons=p.Children.OfType<Button>().ToList();if(buttons.Count!=4||buttons.Any(x=>x.ActualWidth!=320||x.ActualHeight!=60))throw new Exception("Menu dimensions");foreach(var b in buttons){var r=b.TransformToAncestor(content).TransformBounds(new Rect(b.RenderSize));if(r.Top<0||r.Bottom>content.ActualHeight+1||r.Left<0||r.Right>content.ActualWidth+1)throw new Exception("Menu clipped");}});
            Check("100 125 150 200 percent offscreen rendering",()=>{foreach(var dpi in new[]{96,120,144,192})Render("home-dpi-"+dpi,1280,800,dpi);});
            Check("150 percent DPI render",()=>Render("home-150dpi",1200,850,144));
            Check("Settings dark English refresh",()=>{store.Settings.Language="en";store.Settings.Dark=true;Invoke("Theme");Invoke("Settings");Render("settings-dark-en",1200,850);if(!Field<StackPanel>("page").Children.OfType<TextBlock>().Any(x=>x.Text=="Settings"))throw new Exception("Not localized");});
            Check("Library Chinese light refresh",()=>{store.Settings.Language="zh";store.Settings.Dark=false;Invoke("Theme");Invoke("Library");Render("library-light-zh",1200,850);});
            Check("Article selection render",()=>{Invoke("SelectArticle");Render("choose",1200,850);});
            var article=new Article("smoke","Smoke","English","abc",false,DateTime.Now);
            Check("Training starts at zero",()=>{Invoke("Start",article);Drain();if(Field<TrainingSession>("session").Submitted!=0)throw new Exception("Not zero");Render("training",1200,850);});
            Check("Training text change and error coloring",()=>{Field<TextBox>("input").Text="ax";Drain();if(Field<TrainingSession>("session").Submitted!=2)throw new Exception("Submission count");Render("training-error",1200,850);});
            Check("Pause locks editor and stopwatch",()=>{Invoke("TogglePause");var s=Field<TrainingSession>("session");double first=s.Measure().Seconds;Thread.Sleep(70);if(!Field<TextBox>("input").IsReadOnly||Math.Abs(first-s.Measure().Seconds)>.001)throw new Exception("Pause failure");Invoke("TogglePause");});
            Check("Automatic completion persists results",()=>{Field<TextBox>("input").Text="abc";Drain();if(store.Results().Count!=1||!store.Results()[0].Complete)throw new Exception("Not saved");Render("results",1200,1000);});
            Check("Early termination preserved",()=>{Invoke("Start",article);Field<TextBox>("input").Text="a";Invoke("Finish",false);Drain();if(store.Results().Last().Complete)throw new Exception("Wrong status");});
            Check("Zero-input session excluded",()=>{int before=store.Results().Count;Invoke("Start",article);Invoke("Finish",false);if(store.Results().Count!=before)throw new Exception("Zero input saved");});
            Check("Committed input after CRLF uses scalar target position",()=>{
                Invoke("Start",article with{Text="a\nb"});var editor=Field<TextBox>("input");editor.Text="a\r\n";editor.CaretIndex=editor.Text.Length;
                var composition=new System.Windows.Input.TextComposition(System.Windows.Input.InputManager.Current,editor,"b");
                editor.RaiseEvent(new System.Windows.Input.TextCompositionEventArgs(System.Windows.Input.InputManager.Current.PrimaryKeyboardDevice,composition){RoutedEvent=System.Windows.Input.TextCompositionManager.PreviewTextInputEvent});
                editor.AppendText("b");Drain();if(Math.Abs(store.Results().Last().Metrics.FirstAccuracy-100)>.01)throw new Exception("CRLF shifted first accuracy");
            });
            Check("Training automation bulk value pattern unavailable",()=>{Invoke("Start",article);var editor=Field<TextBox>("input");var peer=System.Windows.Automation.Peers.UIElementAutomationPeer.CreatePeerForElement(editor);if(peer.GetPattern(System.Windows.Automation.Peers.PatternInterface.Value)!=null)throw new Exception("Writable value pattern exposed");});
            Check("Pasting routed event canceled",()=>{var editor=Field<TextBox>("input");var paste=new DataObjectPastingEventArgs(new DataObject(DataFormats.UnicodeText,"abc"),false,DataFormats.UnicodeText);editor.RaiseEvent(paste);if(!paste.CommandCancelled)throw new Exception("Paste allowed");Invoke("Finish",false);});
            Check("All pages use requested dark palette",()=>{
                store.Settings.Dark=true;Invoke("Theme");
                foreach(var method in new[]{"Home","SelectArticle","Settings","Library"}){Invoke(method);Drain();Render("dark-"+method,1280,800);if(((SolidColorBrush)window.Background).Color!=Color.FromRgb(16,20,29))throw new Exception("Wrong background");}
                Invoke("Start",article);Render("dark-training",1280,800);if(((SolidColorBrush)Field<TextBox>("input").Background).Color!=Color.FromRgb(26,34,48))throw new Exception("Input not themed");Invoke("Finish",false);Render("dark-results",1280,800);
                Invoke("ImportPreview","Preview","Preview text");Render("dark-import",900,600);
            });
            Check("Dark dropdown opens with dark items",()=>{Invoke("SelectArticle");Drain();var combo=Field<StackPanel>("page").Children.OfType<ComboBox>().First();combo.IsDropDownOpen=true;Drain();if(combo.ItemContainerGenerator.ContainerFromIndex(0) is not ComboBoxItem item||((SolidColorBrush)item.Foreground).Color!=Color.FromRgb(248,250,252))throw new Exception("Dropdown item contrast");combo.IsDropDownOpen=false;});
            Check("Light preference remains available and persisted",()=>{store.Settings.Dark=false;store.SaveSettings();Invoke("Theme");Invoke("Settings");Render("light-settings",1280,800);if(((SolidColorBrush)window.Background).Color==Color.FromRgb(16,20,29)||new Store(root).Settings.Dark)throw new Exception("Light preference lost");store.Settings.Dark=true;Invoke("Theme");Invoke("Home");});
            Check("Menu action raises page navigation",()=>{var button=Field<StackPanel>("page").Children.OfType<Button>().First();button.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));if(Field<string>("screen")!="select")throw new Exception("Start navigation failed");Invoke("Home");});
            Check("App modal uses dark palette and working OK button",()=>{
                Exception? problem=null;bool observed=false;
                window.Dispatcher.BeginInvoke(DispatcherPriority.ApplicationIdle,new Action(()=>{Window? dialog=null;try{dialog=app.Windows.Cast<Window>().Single(x=>x.Title=="Theme dialog test");observed=true;if(((SolidColorBrush)dialog.Background).Color!=Color.FromRgb(16,20,29))throw new Exception("Light dialog background");var rootPanel=(Grid)dialog.Content;var actions=rootPanel.Children.OfType<WrapPanel>().Single();actions.Children.OfType<Button>().First().RaiseEvent(new RoutedEventArgs(Button.ClickEvent));}catch(Exception e){problem=e;if(dialog!=null)dialog.DialogResult=false;}}));
                var method=typeof(MainWindow).Assembly.GetType("TypingTrainer.UiDialog")!.GetMethod("Show",BindingFlags.Public|BindingFlags.Static)!;var result=method.Invoke(null,new object?[]{window,"深色弹窗检查 / Dark dialog test","Theme dialog test",false});if(problem!=null)throw problem;if(!observed||!Equals(result,true))throw new Exception("Dialog did not close via OK");
            });
            Check("Native maximize respects work area then restores and minimizes",()=>{window.WindowState=WindowState.Maximized;Drain();if(window.WindowState!=WindowState.Maximized)throw new Exception("Maximize failed");var content=(FrameworkElement)window.Content;var origin=content.PointToScreen(new Point(0,0));var end=content.PointToScreen(new Point(content.ActualWidth,content.ActualHeight));var dpi=VisualTreeHelper.GetDpi(window);var area=SystemParameters.WorkArea;if(end.Y>area.Bottom*dpi.DpiScaleY+2)throw new Exception("Content overlaps taskbar work area");window.WindowState=WindowState.Normal;Drain();if(window.WindowState!=WindowState.Normal)throw new Exception("Restore failed");window.WindowState=WindowState.Minimized;Drain();if(window.WindowState!=WindowState.Minimized)throw new Exception("Minimize failed");window.WindowState=WindowState.Normal;Drain();});
        } finally {Invoke("Home");window.Close();Directory.Delete(root,true);}
        File.WriteAllText(Path.Combine(output,"ui-test-results.json"),JsonSerializer.Serialize(log,new JsonSerializerOptions{WriteIndented=true}));return fail>0?1:0;
    }
}

