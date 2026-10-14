using System;
using System.IO;
using System.IO.Pipes;
using System.Reflection;
using System.Threading;
using System.Linq;
using System.Collections;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using ReverseCli.Axure;

// Loaded only in a process explicitly launched with DOTNET_STARTUP_HOOKS.
// No disk patching and no global environment changes.
public class StartupHook {
 const BindingFlags BF=BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static;
 public static void Initialize(){var thread=new Thread(Serve){IsBackground=true,Name="reverse-cli Axure bridge"};thread.Start();}
 static Type T(string name){return AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType(name,false)).FirstOrDefault(t=>t!=null)??throw new InvalidOperationException("APP_STARTING");}
 static object G(object obj,string name){Type t=obj as Type??obj.GetType();for(;t!=null;t=t.BaseType){var p=t.GetProperty(name,BF|BindingFlags.DeclaredOnly);if(p!=null)return p.GetValue(obj is Type?null:obj);var f=t.GetField(name,BF|BindingFlags.DeclaredOnly);if(f!=null)return f.GetValue(obj is Type?null:obj);}throw new MissingMemberException(name);}
 static string Dispatch(string request){var forms=((IEnumerable)G(T("System.Windows.Forms.Application"),"OpenForms")).Cast<object>().ToArray();var form=forms.FirstOrDefault(f=>(bool)G(f,"IsHandleCreated"));if(form==null)throw new InvalidOperationException("APP_STARTING");string result=null;
  Action work=()=>{try{
    foreach(var f in forms.Where(f=>(bool)G(f,"Modal"))){bool welcome=false;try{welcome=G(G(f,"zb3o"),"nrmj").GetType().FullName=="Jr78.Dr7n";}catch{}if(welcome)f.GetType().GetMethod("Close").Invoke(f,null);else throw new InvalidOperationException("APP_MODAL: finish the application's current dialog before running commands");}
    result=Backend.ExecuteJson(request);
   }catch(Exception e){result=JsonSerializer.Serialize(new{ok=false,error=e.Message,kind=e.GetType().Name});}};
  form.GetType().GetMethod("Invoke",new[]{typeof(Delegate)}).Invoke(form,new object[]{work});return result;
 }
 static void Serve(){string state=Environment.GetEnvironmentVariable("AXURE_CLI_STATE");if(string.IsNullOrWhiteSpace(state)||!Path.IsPathFullyQualified(state))return;Directory.CreateDirectory(state);string pipe="reverse-cli-axure-"+Environment.ProcessId;
  File.WriteAllText(Path.Combine(state,"endpoint.json"),JsonSerializer.Serialize(new{pid=Environment.ProcessId,pipe,protocol=1,version=Backend.Version,startedUtc=DateTime.UtcNow}));
  while(true){try{using(var server=new NamedPipeServerStream(pipe,PipeDirection.InOut,1,PipeTransmissionMode.Byte,PipeOptions.CurrentUserOnly)){
    server.WaitForConnection();using(var reader=new StreamReader(server,Encoding.UTF8,false,4096,true))using(var writer=new StreamWriter(server,new UTF8Encoding(false),4096,true){AutoFlush=true}){
     string id=null;string output;
     try{var buf=new StringBuilder();int ch;while((ch=reader.Read())!=-1&&ch!='\n'){if(buf.Length>=262144)throw new ArgumentException("Request too large");buf.Append((char)ch);}var req=JsonNode.Parse(buf.ToString());id=Guid.Parse(req["requestId"].GetValue<string>()).ToString();
      var path=Path.Combine(state,"requests",id+".json");if(File.Exists(path))throw new InvalidOperationException("DUPLICATE_REQUEST: inspect the retained result; do not replay mutations");
      Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllText(path,JsonSerializer.Serialize(new{requestId=id,state="started",op=req["op"]?.GetValue<string>(),utc=DateTime.UtcNow}));
      output=Dispatch(buf.ToString());File.WriteAllText(path,output);
     }catch(Exception ex){while(ex is TargetInvocationException&&ex.InnerException!=null)ex=ex.InnerException;output=JsonSerializer.Serialize(new{ok=false,error=ex.Message,requestId=id,kind=ex.GetType().Name});}
     writer.WriteLine(output);
    }
   }}catch{Thread.Sleep(50);}}
 }
}
