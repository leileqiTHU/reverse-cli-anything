using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ReverseCli.Axure {
 public static partial class Backend {
  public const string Version="11.0.0.4150";
  public const string Hash="dae5748f6be3e69c063ef117bab0b400586d94adf119f5a9ba260df59dc4e4a7";
  const BindingFlags BF=BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static|BindingFlags.Instance;
  static bool checkedHash;
  static Assembly Assembly {get {return AppDomain.CurrentDomain.GetAssemblies().First(a=>a.GetName().Name=="AxureRP11");}}
  static Type T(string name){string candidate=name;while(true){var found=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType(candidate,false)).FirstOrDefault(t=>t!=null);if(found!=null)return found;int dot=candidate.LastIndexOf('.');if(dot<0)throw new TypeLoadException(name);candidate=candidate.Substring(0,dot)+"+"+candidate.Substring(dot+1);}}
  static object G(object obj,string name){for(Type t=obj as Type??obj.GetType();t!=null;t=t.BaseType){var p=t.GetProperty(name,BF|BindingFlags.DeclaredOnly);if(p!=null)return p.GetValue(obj is Type?null:obj);var f=t.GetField(name,BF|BindingFlags.DeclaredOnly);if(f!=null)return f.GetValue(obj is Type?null:obj);}throw new MissingMemberException(obj.GetType().FullName,name);}
  static void S(object obj,string name,object value){var property=obj.GetType().GetProperty(name,BF)??throw new MissingMemberException(obj.GetType().FullName,name);property.SetValue(obj,value);}
  static object C(object obj,string name,params object[] args){Type t=obj as Type??obj.GetType();var methods=t.GetMethods(BF).Where(m=>m.Name==name&&m.GetParameters().Length==args.Length);foreach(var m in methods){var ps=m.GetParameters();bool match=true;for(int i=0;i<args.Length;i++){var pt=ps[i].ParameterType;if(pt.IsByRef)pt=pt.GetElementType();if(args[i]!=null&&!pt.IsInstanceOfType(args[i])){match=false;break;}}if(match)return m.Invoke(obj is Type?null:obj,args);}throw new MissingMethodException(t.FullName,name);}
  static object New(string type,params object[] args){return Activator.CreateInstance(T(type),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,args,null);}
  static object Client(){return C(T("W30.M3m"),"vRo")??throw new InvalidOperationException("NO_PROJECT: no active Axure client");}
  static object File(object c){return C(c,"XIXf");}
  static object Editor(object c){return G(c,"Editor");}
  static bool Dirty(object c){return (bool)C(c,"TIX7");}
  static void Writable(object c){if(!(bool)C(c,"LImL"))throw new InvalidOperationException("NOT_WRITABLE: native editor does not permit edits; complete normal activation or unlock the project");}
  static void Clean(object c){C(c,"CommitOuterObject",true);if(Dirty(c))throw new InvalidOperationException("UNSAVED_CHANGES: save the project before new/open/close");}
  static string Str(JsonNode r,string n){return r[n]?.GetValue<string>()??throw new ArgumentException("Missing "+n);}
  static string Full(string path){if(!Path.IsPathFullyQualified(path))throw new ArgumentException("Path must be absolute");return Path.GetFullPath(path);}
  static IEnumerable<object> Widgets(object c){return ((IEnumerable)G(Editor(c),"DiagramObjects")).Cast<object>();}
  static object Widget(object c,string id){Guid g=Guid.Parse(id);return Widgets(c).SingleOrDefault(w=>(Guid)C(w,"Mtn3")==g)??throw new ArgumentException("Widget not found on current page: "+id);}
  static object WInfo(object w){return new{id=C(w,"Mtn3").ToString(),type=w.GetType().FullName,name=G(w,"Name"),text=G(w,"Text"),bounds=ReadBounds(w),inputType=w.GetType().Name=="TextBox"?G(w,"Type").ToString():null,placeholder=w.GetType().Name=="TextBox"?G(w,"PlaceholderText"):null};}
  static object Summary(object c){return new{file=G(File(c),"FileName"),dirty=Dirty(c),writable=C(c,"LImL"),widgets=Widgets(c).Select(WInfo).ToArray()};}
  public static string ExecuteJson(string json){try{return JsonSerializer.Serialize(new{ok=true,result=Execute(JsonNode.Parse(json))});}catch(Exception ex){while(ex is TargetInvocationException&&ex.InnerException!=null)ex=ex.InnerException;return JsonSerializer.Serialize(new{ok=false,error=ex.Message,kind=ex.GetType().Name,outcome="inspect_before_retry"});}}
  public static object Execute(JsonNode r){if(!checkedHash){using(var sha=SHA256.Create())using(var f=System.IO.File.OpenRead(Assembly.Location)){string hash=Convert.ToHexString(sha.ComputeHash(f)).ToLowerInvariant();if(hash!=Hash)throw new InvalidOperationException("UNSUPPORTED_BUILD: assembly hash mismatch");}checkedHash=true;}
   string op=Str(r,"op");var c=Client();
   if(op=="status")return new{pid=Environment.ProcessId,version=Version,sha256=Hash,app=Assembly.Location,temp=Path.GetTempPath(),configuredCache=G(T("y9JG.P9bz"),"AppTemporaryPath"),project=Summary(c)};
   if(op=="inspect")return Summary(c);
   if(op=="widget.list")return Widgets(c).Select(WInfo).ToArray();
   if(op.StartsWith("page."))return PageCommand(op,r,c);
   if(op.StartsWith("interaction."))return InteractionCommand(op,r,c);
   if(op=="project.sitemap"){var dir=New("Axure.McpServer.InProcDocumentDirectory");var id=C(T("Axure.McpServer.InProcDocumentDirectory"),"DocumentIdFor",c);return C(dir,"GetSitemap",id);}
   if(op=="settings.cache"){string path=Full(Str(r,"path"));Directory.CreateDirectory(path);var platform=C(T("kSnw.xSnT"),"iS8H");var prefs=C(platform,"cIzy");C(prefs,"set_Item","AppTemporaryPath",path);return new{configuredCache=G(T("y9JG.P9bz"),"AppTemporaryPath"),restartRequired=true};}
   Writable(c);
   if(op=="widget.create")return WidgetCreate(r,c);
   if(op=="widget.bounds")return WidgetBounds(r,c);
   if(op=="widget.text"){
    var w=Widget(c,Str(r,"id"));var before=G(w,"Text");var attr=G(w,"AttributedString");if(attr==null)throw new InvalidOperationException("Widget has no attributed text");
    var replacement=C(T("tSmX.rSma"),"lSmU",Str(r,"text"),C(attr,"VIvs"));
    var edit=C(T("djCv.ljCy"),"HjCQ",w,replacement);C(Editor(c),"yFZi",edit,false);
    return new{before,after=WInfo(w),dirty=Dirty(c)};
   }
   if(op=="undo"||op=="redo"){C(c,op=="undo"?"Undo":"Redo",G(c,"Workspace"));RefreshPages(c);return Summary(c);}
   if(op=="project.save"){
    C(c,"CommitOuterObject",true);var f=File(c);string path=r["path"]==null?(string)G(f,"FileName"):Full(Str(r,"path"));
    if(string.IsNullOrEmpty(path)||!Path.IsPathFullyQualified(path))throw new ArgumentException("Unsaved document requires an absolute path");
    string current=(string)G(f,"FileName");if(System.IO.File.Exists(path)&&!string.Equals(path,current,StringComparison.OrdinalIgnoreCase))throw new IOException("Destination already exists");Directory.CreateDirectory(Path.GetDirectoryName(path));
    if(string.Equals(path,current,StringComparison.OrdinalIgnoreCase))C(f,"Save");else{object[] args={path,null};bool ok=(bool)C(f,"INR4",args);if(!ok)throw new IOException("Native save failed: "+args[1]);}
    if(!System.IO.File.Exists(path)||Dirty(c))throw new IOException("Native save did not produce a clean persisted project");return new{path,bytes=new FileInfo(path).Length,dirty=Dirty(c)};
   }
   if(op=="project.open"){Clean(c);var path=Full(Str(r,"path"));if(!System.IO.File.Exists(path))throw new FileNotFoundException(path);C(c,"OpenDocument",path,false);return Summary(c);}
   if(op=="project.new"){Clean(c);C(c,"vImH",Enum.Parse(T("Axure.Platform.ObjectPersistanceContext.DesignDocumentType"),"Standard"),false);return Summary(c);}
   if(op=="project.close"){Clean(c);C(c,"CloseClient");return new{closed=true};}
   if(op=="export.html"){
    var output=Full(Str(r,"output"));if(Directory.Exists(output)&&Directory.EnumerateFileSystemEntries(output).Any())throw new IOException("Export destination must be empty");Directory.CreateDirectory(output);C(c,"CommitOuterObject",true);var f=File(c);
    var cfg=New("LSr8.GSrn",C(f,"DNET"));C(cfg,"HSFG",output);C(cfg,"ESFS",false);C(cfg,"jSFg",true);
    var gen=New("OJF5.cJFt",cfg);var result=C(gen,"Generate",f,null,null,null);bool success=(bool)C(result,"zJFb");if(!success)throw new IOException("Native HTML generator did not report success");
    return new{output,nativeSuccess=success,files=Directory.EnumerateFiles(output,"*",SearchOption.AllDirectories).Count()};
   }
   throw new ArgumentException("Unknown command: "+op);
  }
 }
}
