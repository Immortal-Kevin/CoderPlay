// SPDX-License-Identifier: Apache-2.0
using System.Globalization;
using System.Windows;
using System.Windows.Media;
namespace TypingTrainer;
// A size-aware drawing surface, not a page-layout Canvas. The result data is unchanged.
public sealed class TrendChart : FrameworkElement
{
    public IReadOnlyList<Result> Results { get; set; }=Array.Empty<Result>();
    public bool English { get; set; }
    public TrendChart(){MouseMove+=(_,e)=>{if(Results.Count==0)return;double fraction=Math.Clamp((e.GetPosition(this).X-72)/Math.Max(1,ActualWidth-154),0,1);var r=Results[(int)Math.Round(fraction*(Results.Count-1))];ToolTip=$"#{r.Number} · {r.Title}\n{r.Date:g}\n{r.Metrics.Cpm:F1} CPM / {r.Metrics.Wpm:F1} WPM\n{r.Metrics.FinalAccuracy:F1}%";};}
    Brush Brush(string key)=>TryFindResource(key) as Brush??Brushes.Gray;
    protected override void OnRender(DrawingContext dc)
    {
        base.OnRender(dc);dc.DrawRoundedRectangle(Brush("SurfaceBrush"),null,new Rect(RenderSize),8,8);
        double left=72,right=Math.Max(100,ActualWidth-82),top=40,bottom=Math.Max(70,ActualHeight-38);var ink=Brush("ForegroundBrush");var secondary=Brush("SecondaryBrush");var blue=Brush("AccentBrush");var green=Brush("ChartAccuracyBrush");
        void Text(string value,double x,double y,Brush? color=null)=>dc.DrawText(new FormattedText(value,CultureInfo.CurrentCulture,FlowDirection.LeftToRight,new Typeface(FontFamily()),12,color??secondary,VisualTreeHelper.GetDpi(this).PixelsPerDip),new Point(x,y));
        if(Results.Count==0){Text(English?"No history yet":"暂无历史数据",28,ActualHeight/2);return;}
        double max=Math.Max(10,Math.Ceiling(Results.Max(x=>x.Metrics.Cpm)/10)*10);
        for(int i=0;i<=4;i++){double y=bottom-(bottom-top)*i/4;dc.DrawLine(new Pen(Brush("BorderBrush"),1),new Point(left,y),new Point(right,y));Text((max*i/4).ToString("F0"),8,y-8);Text((25*i)+"%",right+12,y-8);}
        Text("CPM / WPM (÷5)",left,12,blue);Text(English?"Final accuracy":"最终正确率",right-110,12,green);
        Point? previousSpeed=null,previousAccuracy=null;
        for(int i=0;i<Results.Count;i++){var r=Results[i];double x=left+(right-left)*(Results.Count==1?.5:(double)i/(Results.Count-1));var speed=new Point(x,bottom-(bottom-top)*r.Metrics.Cpm/max);var accuracy=new Point(x,bottom-(bottom-top)*r.Metrics.FinalAccuracy/100);
            if(previousSpeed is Point p)dc.DrawLine(new Pen(blue,2),p,speed);if(previousAccuracy is Point q)dc.DrawLine(new Pen(green,2),q,accuracy);
            dc.DrawEllipse(blue,null,speed,4,4);dc.DrawEllipse(green,null,accuracy,3,3);previousSpeed=speed;previousAccuracy=accuracy;
            if(i==0||i==Results.Count-1||Results.Count<=10)Text("#"+r.Number,x-10,bottom+10);
        }
    }
    string FontFamily()=>"Microsoft YaHei UI";
}
