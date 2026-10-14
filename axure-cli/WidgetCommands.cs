using System;
using System.Text.Json.Nodes;

namespace ReverseCli.Axure {
 public static partial class Backend {
  static double WidgetNumber(JsonNode r,string name,double fallback) {
   double value=r[name]==null?fallback:r[name].GetValue<double>();
   if(!double.IsFinite(value))throw new ArgumentException(name+" must be finite");
   return value;
  }
  static object ReadBounds(object w) {
   var rect=G(w,"Rect");
   return new{x=G(rect,"X"),y=G(rect,"Y"),width=G(rect,"Width"),height=G(rect,"Height")};
  }
  static object WidgetRect(JsonNode r,object w) {
   var old=G(w,"Rect");
   double x=WidgetNumber(r,"x",Convert.ToDouble(G(old,"X")));
   double y=WidgetNumber(r,"y",Convert.ToDouble(G(old,"Y")));
   double width=WidgetNumber(r,"width",Convert.ToDouble(G(old,"Width")));
   double height=WidgetNumber(r,"height",Convert.ToDouble(G(old,"Height")));
   if(x < -10000 || x > 20000 || y < -10000 || y > 20000)throw new ArgumentException("x and y must be between -10000 and 20000");
   if(width < 1 || width > 20000 || height < 1 || height > 20000)throw new ArgumentException("width and height must be between 1 and 20000");
   return New("h5uH.j5u5",x,y,width,height);
  }
  static object WidgetCreate(JsonNode r,object c) {
   string kind=r["kind"]?.GetValue<string>()??"paragraph";
   if(kind!="paragraph"&&kind!="button"&&kind!="input")throw new ArgumentException("kind must be paragraph, button, or input");
   if(kind!="input"&&(r["password"]!=null||r["placeholder"]!=null))throw new ArgumentException("password and placeholder are only supported on input widgets");
   string text=r["text"]?.GetValue<string>()??"";
   var ed=Editor(c);var doc=C(G(ed,"Diagram"),"btnD");
   object w;
   if(kind=="paragraph") {
    w=New("Axure.DocumentModel.Objects.VectorShape",doc,Enum.Parse(T("Axure.Platform.Shape"),"Paragraph"),text,Enum.Parse(T("Axure.DocumentModel.Objects.VectorLegacyType"),"None"),true);
    S(w,"AutoFitHeight",true);S(w,"AutoFitWidth",true);S(w,"Text",text);C(w,"BNZT");
   } else {
    w=New(kind=="button"?"Axure.DocumentModel.Objects.Button":"Axure.DocumentModel.Objects.TextBox",doc);
    S(w,"Text",text);
    if(kind=="input") {
     S(w,"Type",Enum.Parse(T("Axure.DocumentModel.Objects.InputType"),(r["password"]?.GetValue<bool>()??false)?"Password":"Text"));
     if(r["placeholder"]!=null)S(w,"PlaceholderText",Str(r,"placeholder"));
    }
    // Detached widgets are configured before the native add-object transaction.
    C(w,"YJ0S",New("h5uH.j5u5",0.0,0.0,kind=="input"?300.0:120.0,40.0),true);
   }
   if(r["name"]!=null)S(w,"Name",Str(r,"name"));
   if(r["x"]!=null||r["y"]!=null||r["width"]!=null||r["height"]!=null) {
    var rect=WidgetRect(r,w);
    if(kind=="paragraph") {if(r["width"]!=null)S(w,"AutoFitWidth",false);if(r["height"]!=null)S(w,"AutoFitHeight",false);}
    C(w,"YJ0S",rect,true);
   }
   C(ed,"oFYd",w,true);C(ed,"BFYD",w,true,true);
   return WInfo(w);
  }
  static object WidgetBounds(JsonNode r,object c) {
   if(r["x"]==null&&r["y"]==null&&r["width"]==null&&r["height"]==null)throw new ArgumentException("Provide at least one of x, y, width, height");
   var w=Widget(c,Str(r,"id"));
   string type=w.GetType().FullName;
   if(type!="Axure.DocumentModel.Objects.VectorShape"&&type!="Axure.DocumentModel.Objects.Button"&&type!="Axure.DocumentModel.Objects.TextBox")throw new ArgumentException("bounds currently supports paragraph/vector, button, and input widgets");
   var before=ReadBounds(w);var rect=WidgetRect(r,w);
   // Same snapshot + geometry mutation + native editor commit used by Axure's
   // geometry inspector (QBqe.yBqx.uBqX / kBqm), preserving native undo/redo.
   using((IDisposable)C(c,"ug4",false,null)) {
    var edit=New("QSc5.kSct",w);
    object[] connectionArgs={null};
    using((IDisposable)C(edit,"FSW9",connectionArgs)) {
     if(type=="Axure.DocumentModel.Objects.VectorShape") {
      if(r["width"]!=null)S(w,"AutoFitWidth",false);
      if(r["height"]!=null)S(w,"AutoFitHeight",false);
     }
     bool allAdaptive=(bool)G(C(w,"K3FB"),"EditAllAdaptive");
     C(w,"YJ0S",rect,allAdaptive);
     C(T("Axure.DocumentModel.Objects.Connector"),"fN2F",connectionArgs[0],true);
    }
    C(edit,"YSWI");
    C(G(c,"Workspace"),"zImy",edit,false);
   }
   return new{before,after=WInfo(w),dirty=Dirty(c)};
  }
 }
}
