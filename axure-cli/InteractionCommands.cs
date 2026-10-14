using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Nodes;

namespace ReverseCli.Axure {
 public static partial class Backend {
  static object InteractionInfo(object w) {
   var map=C(w,"GIss");
   var events=((IEnumerable)C(map,"SJuj")).Cast<object>().Select(ev=>new {
    type=G(ev,"EventType").ToString(),
    cases=((IEnumerable)C(map,"YJuS",ev)).Cast<object>().Select(k=>new {
     name=G(k,"Description"),newIfGroup=G(k,"IsNewIfGroup"),condition=ReadCondition(G(k,"Condition")),
     actions=((IEnumerable)C(map,"vJu1",k)).Cast<object>().Select(ReadAction).ToArray()
    }).ToArray()
   }).ToArray();
   return new{id=C(w,"Mtn3").ToString(),events};
  }
  static object InteractionCommand(string op,JsonNode r,object c) {
   var w=Widget(c,Str(r,"id"));
   if(op=="interaction.get")return InteractionInfo(w);
   if(op!="interaction.set")throw new ArgumentException("Unknown interaction command");
   Writable(c);
   var old=C(w,"GIss");
   if(!(bool)C(old,"IsEmpty"))throw new InvalidOperationException("INTERACTION_EXISTS: this pilot only installs interactions on a widget with an empty interaction map; use undo to revert an installation");
   var spec=r["spec"]??throw new ArgumentException("Missing spec");
   if((spec["event"]?.GetValue<string>()??"click")!="click")throw new ArgumentException("Only click events are supported");
   var cases=spec["cases"] as JsonArray??throw new ArgumentException("spec.cases must be an array");
   if(cases.Count<1||cases.Count>20)throw new ArgumentException("Provide 1 to 20 cases");
   var doc=C(w,"btnD");var map=New("MJuB.gJuG",doc,w);
   var ev=C(map,"lJu3",Enum.Parse(T("Axure.Constants.IxEventType"),"OnClick"));
   // Build and validate a detached map first; one native replacement edit commits it.
   for(int i=0;i<cases.Count;i++) {
    var entry=cases[i]??throw new ArgumentException("Case cannot be null");
    var actions=entry["actions"] as JsonArray??throw new ArgumentException("Case actions must be an array");
    if(actions.Count<1||actions.Count>20)throw new ArgumentException("Provide 1 to 20 actions per case");
    if(entry["when"]==null&&i!=cases.Count-1)throw new ArgumentException("An unconditional case must be last");
    var kase=New("Axure.DocumentModel.Interaction.IxCase",doc);
    S(kase,"Description",entry["name"]?.GetValue<string>()??("Case "+(i+1)));
    S(kase,"IsNewIfGroup",i==0);
    if(entry["when"]!=null)S(kase,"Condition",BuildCondition(entry["when"],c,doc));
    var node=C(map,"TNFt",null,ev,i,kase);
    for(int j=0;j<actions.Count;j++)C(map,"TNFt",null,node,j,BuildAction(actions[j],c,doc));
   }
   var edit=New("uSgI.ESg1",w,old,map,new Dictionary<Guid,Guid>(),null,false,Guid.Empty,false);
   C(Editor(c),"yFZi",edit,false);
   return new{interaction=InteractionInfo(w),dirty=Dirty(c)};
  }
 }
}
