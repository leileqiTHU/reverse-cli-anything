using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Nodes;

namespace ReverseCli.Axure {
 public static partial class Backend {
  static object IxString(object doc,string text) {
   // This CLI accepts plain values; Axure's [[...]] expression language is
   // intentionally outside the detached expression builder's contract.
   if(text.Contains("[["))throw new ArgumentException("Use plain text; Axure inline expressions are not supported");
   return New("Axure.DocumentModel.Expressions.StringLiteral",doc,text,null,null,null);
  }
  static object IxPath(object c,object doc,string id) {
   var w=Widget(c,id);
   var path=New("sJ8l.dJ8s",doc,null,null,(Guid)C(w,"Mtn3"));
   // Resolution against the active native diagram validates the reference
   // before any interaction is attached to its event map.
   if(C(path,"UJfj",G(Editor(c),"Diagram"))==null)throw new ArgumentException("Widget path cannot be resolved on the current page: "+id);
   return path;
  }
  static object IxCall(object doc,string function,params object[] args) {
   var call=New("Axure.DocumentModel.Expressions.FCall",doc);
   S(call,"FunctionName",function);
   foreach(var arg in args)C(call,"kS5q",arg);
   return call;
  }
  static object IxBinary(object doc,string operation,object left,object right) {
   return New("Axure.DocumentModel.Expressions.BinaryExpr",doc,Enum.Parse(T("Axure.Platform.LogicalComparison"),operation),left,right);
  }
  static object BuildCondition(JsonNode r,object c,object doc) {return IxCondition(r,c,doc,0);}
  static object IxCondition(JsonNode r,object c,object doc,int depth) {
   if(r==null)return null;
   if(depth>12)throw new ArgumentException("Condition nesting exceeds 12");
   if(r is not JsonObject)throw new ArgumentException("Condition must be an object");
   bool any=r["any"]!=null,all=r["all"]!=null;
   if(any||all) {
    if(any&&all||r["widget"]!=null||r["equals"]!=null)throw new ArgumentException("Condition must use exactly one of any, all, or widget/equals");
    string key=any?"any":"all";
    if(r[key] is not JsonArray items || items.Count<1 || items.Count>32)throw new ArgumentException(key+" requires 1 to 32 conditions");
    object result=null;
    foreach(var item in items) {
     if(item==null)throw new ArgumentException("Nested conditions cannot be null");
     var next=IxCondition(item,c,doc,depth+1);
     result=result==null?next:IxBinary(doc,any?"Or":"And",result,next);
    }
    return result;
   }
   var w=Widget(c,Str(r,"widget"));
   if(w.GetType().FullName!="Axure.DocumentModel.Objects.TextBox")throw new ArgumentException("Text conditions currently require an input widget");
   var path=IxPath(c,doc,Str(r,"widget"));
   var value=IxCall(doc,"GetWidgetText",New("Axure.DocumentModel.Expressions.DiagramObjectPathLiteral",doc,path));
   return IxBinary(doc,"Equals",value,IxString(doc,Str(r,"equals")));
  }
  static object BuildAction(JsonNode r,object c,object doc) {
   string type=Str(r,"type");
   if(type=="setText") {
    var w=Widget(c,Str(r,"target"));
    string widgetType=w.GetType().FullName;
    if(widgetType!="Axure.DocumentModel.Objects.VectorShape"&&widgetType!="Axure.DocumentModel.Objects.TextBox")throw new ArgumentException("setText currently supports paragraph/vector and input widgets");
    var path=IxPath(c,doc,Str(r,"target"));
    var literal=New("Axure.DocumentModel.Expressions.DiagramObjectPathLiteral",doc,path);
    string function=widgetType=="Axure.DocumentModel.Objects.TextBox"?"SetWidgetFormText":"SetWidgetRichText";
    var text=IxString(doc,Str(r,"text"));
    var call=function=="SetWidgetFormText"?IxCall(doc,function,literal,text):IxCall(doc,function,literal,text,New("Axure.DocumentModel.Expressions.BooleanLiteral",doc,true));
    var action=New("Axure.DocumentModel.Interaction.IxActionSetFunction",doc,function);
    C(action,"QNyH",path,call);
    return action;
   }
   if(type=="navigate") {
    Guid id=Guid.Parse(Str(r,"page"));
    var page=PageNodes(PageTree(c)).SingleOrDefault(n=>string.Equals((string)G(n,"Id"),id.ToString(),StringComparison.OrdinalIgnoreCase));
    if(page==null||string.Equals((string)G(page,"Type"),"folder",StringComparison.OrdinalIgnoreCase))throw new ArgumentException("Page not found: "+id);
    var action=New("Axure.DocumentModel.Interaction.IxLinkWindowAction",doc,Enum.Parse(T("Axure.DocumentModel.Interaction.LinkType"),"Current"));
    var target=G(action,"Target");
    S(target,"TargetType",Enum.Parse(T("Axure.DocumentModel.Interaction.IxTargetType"),"Page"));
    S(target,"TargetPagePackageId",id);
    return action;
   }
   throw new ArgumentException("Action type must be setText or navigate");
  }
  static object ReadCondition(object expr) {return IxReadExpr(expr,0);}
  static object IxReadExpr(object expr,int depth) {
   if(expr==null)return null;
   if(depth>64)throw new InvalidOperationException("Native expression nesting exceeds inspection limit");
   string type=expr.GetType().FullName;
   if(type=="Axure.DocumentModel.Expressions.BinaryExpr")return new{node="binary",operation=G(expr,"Operation").ToString(),left=IxReadExpr(G(expr,"LeftExpr"),depth+1),right=IxReadExpr(G(expr,"RightExpr"),depth+1)};
   if(type=="Axure.DocumentModel.Expressions.FCall")return new{node="call",function=G(expr,"FunctionName"),args=((IEnumerable)G(expr,"Args")).Cast<object>().Select(a=>IxReadExpr(a,depth+1)).ToArray()};
   if(type=="Axure.DocumentModel.Expressions.DiagramObjectPathLiteral") {
    var path=G(expr,"LiteralValue");
    return new{node="widget",id=C(path,"xJfE").ToString(),referencePath=((IEnumerable)C(path,"lJf1")).Cast<object>().Select(i=>i.ToString()).ToArray(),adaptivePath=((IEnumerable)C(path,"AJft")).Cast<object>().Select(i=>i.ToString()).ToArray()};
   }
   if(type=="Axure.DocumentModel.Expressions.StringLiteral")return new{node="string",value=G(expr,"LiteralValue"),raw=G(expr,"RawValue")};
   if(type=="Axure.DocumentModel.Expressions.BooleanLiteral")return new{node="boolean",value=G(expr,"LiteralValue")};
   return new{node="unsupported",nativeType=type};
  }
  static object ReadAction(object action) {
   string type=action.GetType().FullName;
   if(type=="Axure.DocumentModel.Interaction.IxActionSetFunction")return new{type="setText",function=G(action,"SetFunction"),expressions=((IEnumerable)G(G(action,"Action"),"SubExpressions")).Cast<object>().Select(e=>IxReadExpr(e,0)).ToArray()};
   if(type=="Axure.DocumentModel.Interaction.IxLinkWindowAction") {
    var target=G(action,"Target");
    return new{type="navigate",linkType=G(action,"CurrentLinkType").ToString(),targetType=G(target,"TargetType").ToString(),page=G(target,"TargetPagePackageId").ToString()};
   }
   return new{type="unsupported",nativeType=type};
  }
 }
}
