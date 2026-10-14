using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Nodes;

namespace ReverseCli.Axure {
 public static partial class Backend {
  static void RefreshPages(object c){C(G(C(c,"nIXw"),"Sitemap"),"UNrz",EventArgs.Empty);}
  static object PageTree(object c) {
   return C(T("Axure.McpServer.Mapping.SitemapMapper"),"MapSitemap",C(c,"nIXw"));
  }
  static IEnumerable<object> PageNodes(object nodes) {
   foreach(var node in ((IEnumerable)nodes).Cast<object>()) {
    yield return node;
    var children=G(node,"Children");
    if(children!=null) foreach(var child in PageNodes(children)) yield return child;
   }
  }
  static object PageCommand(string op,JsonNode r,object c) {
   if(op=="page.list") return new{activeId=C(c,"KE5").ToString(),pages=PageTree(c)};
   if(op=="page.open") {
    Guid id=Guid.Parse(Str(r,"id"));
    var page=PageNodes(PageTree(c)).SingleOrDefault(n=>string.Equals((string)G(n,"Id"),id.ToString(),StringComparison.OrdinalIgnoreCase));
    if(page==null || string.Equals((string)G(page,"Type"),"folder",StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("Page not found: "+id);
    C(c,"CommitOuterObject",true);
    C(c,"TImN",id,Guid.Empty,false);
    if((Guid)C(c,"KE5")!=id) throw new InvalidOperationException("Native page open did not activate the requested page");
    return new{activeId=id.ToString(),page,project=Summary(c)};
   }
   if(op=="page.create") {
    Writable(c);
    string name=Str(r,"name").Trim();
    if(string.IsNullOrWhiteSpace(name)||name.Length>200)throw new ArgumentException("Page name must contain 1 to 200 characters");
    if(PageNodes(PageTree(c)).Any(n=>string.Equals((string)G(n,"Name"),name,StringComparison.OrdinalIgnoreCase)))throw new ArgumentException("A page or folder with this name already exists: "+name);
    // Use the same AddNode edit as the native sitemap controller, bypassing
    // only selection/focus and inline-rename UI. Its Commit/Rollback owns the
    // package metadata and tree insertion/removal.
    C(c,"CommitOuterObject",true);
    var doc=C(c,"nIXw");var map=G(doc,"Sitemap");var root=G(map,"Tree");
    Guid id=Guid.NewGuid();
    var parents=Array.CreateInstance(T("FJlc.QJlk"),1);parents.SetValue(root,0);
    // The native add command always generates a numbered name. Prepare the
    // detached node so its exact rename can share the same undo transaction.
    var node=New("FJlc.QJlk",doc,Guid.NewGuid());C(node,"OJl6",root);
    var nodes=Array.CreateInstance(T("FJlc.QJlk"),1);nodes.SetValue(node,0);
    var edit=New("ESDL.lSDD",Enum.Parse(T("Axure.DocumentModel.Edit.TreeEditType"),"AddNode"),map,parents);
    C(edit,"TSDA",((IEnumerable)G(root,"Children")).Cast<object>().Count());
    C(edit,"pSDd",(object)new object[]{id});
    C(edit,"tSDy",nodes);
    C(edit,"tSDY",name);
    var rename=New("ESDL.lSDD",Enum.Parse(T("Axure.DocumentModel.Edit.TreeEditType"),"RenameNode"),map,nodes);
    C(rename,"tSDY",name);
    var edits=Array.CreateInstance(T("JS3I.bS31"),2);edits.SetValue(edit,0);edits.SetValue(rename,1);
    var transaction=New("BS11.pS1H",(object)edits);
    if(!(bool)C(T("IS3F.TS3r"),"GS3j",transaction))throw new InvalidOperationException("Native page edit was rejected before execution");
    C(G(c,"Workspace"),"QIml",transaction);
    RefreshPages(c);
    var page=PageNodes(PageTree(c)).SingleOrDefault(n=>string.Equals((string)G(n,"Id"),id.ToString(),StringComparison.OrdinalIgnoreCase));
    if(page==null)throw new InvalidOperationException("Native page edit did not produce the requested page");
    if(!string.Equals((string)G(page,"Name"),name,StringComparison.Ordinal))throw new InvalidOperationException("Native page name differs from requested name; inspect page list before retrying");
    // Keep the original active page so undo remains in the same native
    // workspace history context. A caller selects the new page explicitly.
    return new{page,activeId=C(c,"KE5").ToString(),dirty=Dirty(c)};
   }
   throw new ArgumentException("Unknown page command: "+op);
  }
 }
}
