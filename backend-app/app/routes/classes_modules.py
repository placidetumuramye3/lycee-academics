"""Classes & Modules page.

The module catalog lives in the relational ``academic_module`` table
(seeded from the transcribed curriculum in ``app/data/module_catalog.py``).
This page renders the catalog FROM THE DATABASE so modules participate in
the relational academic structure; the transcribed data module is used
only as a read-only fallback when the database has not been seeded.

Selection model
---------------
Department -> Trade -> Level -> Class. Every dropdown loads its options from
the relational database (``/api/academics/*``) and stays disabled until its
parent selection has been made, so a department choice only ever offers its
own trades, levels and classes.

Module maintenance
------------------
Users with the ``classes_modules_edit`` permission can add a module (name,
code, hours, periods, assessment weight, category) or edit/remove an existing
one. Modules are stored on their (trade, level) so the change applies to
every class of that level. The values are written by the JSON API in
``app/routes/academic_api.py`` - never straight into the page.
"""
import json
from markupsafe import escape
from app.extensions import db
from app.models.academic_structure import (
    Department, Trade, SchoolClass, AcademicModule,
)
from app.data.module_catalog import DEPARTMENTS as FALLBACK_DEPARTMENTS
from app.utils.rendering import page
from app.utils.decorators import permission_for
from app.utils.constants import ROLE_ACCESS

CLASSES_MODULES_BODY = r"""<style>
:root{--bg:#f6f7f9;--card:#fff;--tx:#1d2330;--mu:#667085;--bd:#e3e6ec;--ac:#1f5eff;--c1:#0e7490;--c2:#6b7280;--c3:#c2410c;--ok:#15803d;--bad:#b42318;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14171c;--card:#1d2128;--tx:#eceff4;--mu:#98a2b3;--bd:#2c323c;--ac:#6b93ff;--c1:#38bdf8;--c2:#9ca3af;--c3:#fb923c;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#14171c;--card:#1d2128;--tx:#eceff4;--mu:#98a2b3;--bd:#2c323c;--ac:#6b93ff;--c1:#38bdf8;--c2:#9ca3af;--c3:#fb923c;color-scheme:dark}
*{box-sizing:border-box}html{scroll-padding-top:env(safe-area-inset-top,0px)}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:16px 20px;border-bottom:1px solid var(--bd);background:var(--card)}
h1{margin:0;font-size:18px}header p{margin:2px 0 0;color:var(--mu);font-size:13px}
.wrap{display:flex;gap:16px;padding:16px 20px;max-width:1180px;margin:auto}
nav{width:300px;flex:none}
.filters{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px;margin-bottom:12px;display:grid;gap:9px}
.filters label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--mu);display:block;margin-bottom:4px}
select{width:100%;padding:8px 10px;border:1px solid var(--bd);border-radius:8px;background:var(--card);color:var(--tx);font:inherit;font-size:14px}
select:disabled{opacity:.65;cursor:not-allowed}
.dept{font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--mu);margin:14px 0 6px}
.trade{font-size:13px;font-weight:600;margin:8px 0 4px}
.cls{display:block;width:100%;text-align:left;background:var(--card);border:1px solid var(--bd);color:var(--tx);padding:8px 10px;border-radius:8px;margin-bottom:5px;cursor:pointer;font:inherit;font-size:14px}
.cls:hover{border-color:var(--ac)}.cls.on{background:var(--ac);color:#fff;border-color:var(--ac)}
main{flex:1;min-width:0}
.top{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;justify-content:space-between;margin-bottom:10px}
.top h2{margin:0;font-size:20px}.stats{color:var(--mu);font-size:13px}
.search{width:100%;padding:9px 12px;border:1px solid var(--bd);border-radius:8px;background:var(--card);color:var(--tx);font:inherit;margin-bottom:12px}
.btn{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:8px;padding:8px 13px;font:inherit;font-size:13px;font-weight:600;cursor:pointer}
.btn:hover{border-color:var(--ac)}.btn.primary{background:var(--ac);border-color:var(--ac);color:#fff}
.btn.danger{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 34%,var(--bd))}
.btn.mini{padding:4px 8px;font-size:12px}
.grp{background:var(--card);border:1px solid var(--bd);border-radius:10px;margin-bottom:14px;overflow:hidden}
.gh{display:flex;justify-content:space-between;padding:10px 14px;font-weight:700;border-left:5px solid var(--g)}
.gh span{font-weight:500;color:var(--mu);font-size:13px}
.tw{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:8px 14px;text-align:left;border-top:1px solid var(--bd)}th{font-size:12px;color:var(--mu);font-weight:600}
td.n{text-align:right;white-space:nowrap}code{font-weight:600}
.empty{background:var(--card);border:1px dashed var(--bd);border-radius:10px;padding:28px;text-align:center;color:var(--mu)}
.note{margin:0 0 12px;padding:10px 13px;border-radius:9px;font-size:13px;border:1px solid var(--bd);background:var(--card)}
.note.ok{border-color:color-mix(in srgb,var(--ok) 40%,var(--bd));color:var(--ok)}
.note.bad{border-color:color-mix(in srgb,var(--bad) 40%,var(--bd));color:var(--bad)}
dialog{border:1px solid var(--bd);border-radius:14px;padding:0;width:min(560px,calc(100vw - 28px));background:var(--card);color:var(--tx);box-shadow:0 24px 60px rgba(10,20,30,.3)}
dialog::backdrop{background:rgba(10,16,24,.5)}
.dlg-head{display:flex;justify-content:space-between;align-items:center;padding:16px 18px;border-bottom:1px solid var(--bd)}
.dlg-head h3{margin:0;font-size:17px}
.dlg-body{padding:16px 18px}
.dlg-foot{display:flex;justify-content:flex-end;gap:8px;padding:14px 18px;border-top:1px solid var(--bd)}
.fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,210px),1fr));gap:12px}
.field label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--mu);display:block;margin-bottom:4px}
.field input{width:100%;padding:8px 10px;border:1px solid var(--bd);border-radius:8px;background:var(--card);color:var(--tx);font:inherit;font-size:14px}
.field.wide{grid-column:1/-1}
.hint{font-size:12px;color:var(--mu);margin:10px 0 0}
@media(max-width:860px){.wrap{flex-direction:column}nav{width:100%}}
</style>
<header><h1>Classes &amp; Modules — __YEAR__</h1><p>Pick a department, then its trade, level and class. Each list only shows options that belong to the selection above it.</p></header>
<div class="wrap">
<nav>
<div class="filters">
<div><label for="f-dept">Department</label><select id="f-dept" data-academic="department" data-targets="trade,level,class"></select></div>
<div><label for="f-trade">Trade</label><select id="f-trade" data-academic="trade" data-parent="department" data-targets="level,class" disabled></select></div>
<div><label for="f-level">Level</label><select id="f-level" data-academic="level" data-parent="trade" data-targets="class" disabled></select></div>
<div><label for="f-class">Class</label><select id="f-class" data-academic="class" data-parent="level" data-require="trade,level" disabled></select></div>
</div>
<div id="nav"></div>
</nav>
<main id="main"></main>
</div>
<script src="/static/js/academic-cascade.js"></script>
<script>if(window.AcademicCascade)AcademicCascade.init(document);</script>
<dialog id="dlg" aria-labelledby="dlg-title">
<form id="dlg-form" method="dialog">
<div class="dlg-head"><h3 id="dlg-title">Add module</h3><button type="button" class="btn mini" data-close aria-label="Close">✕</button></div>
<div class="dlg-body">
<div class="fields">
<div class="field"><label for="m-dept">Department</label><select id="m-dept" data-academic="department" data-targets="trade,level,class"></select></div>
<div class="field"><label for="m-trade">Trade</label><select id="m-trade" data-academic="trade" data-parent="department" data-targets="level,class" disabled></select></div>
<div class="field"><label for="m-level">Level</label><select id="m-level" data-academic="level" data-parent="trade" data-targets="class" disabled></select></div>
<div class="field"><label for="m-class">Class</label><select id="m-class" data-academic="class" data-parent="level" data-require="trade,level" disabled></select></div>
<div class="field wide"><label for="m-name">Module name</label><input id="m-name" name="name" maxlength="180" required autocomplete="off"></div>
<div class="field"><label for="m-code">Module code</label><input id="m-code" name="code" maxlength="50" autocomplete="off"></div>
<div class="field"><label for="m-cat">Category</label><select id="m-cat" name="category"><option value="Specific">Specific (Core)</option><option value="General">General</option><option value="Complementary">Complementary</option></select></div>
<div class="field"><label for="m-hours">Hours</label><input id="m-hours" name="hours" type="number" min="0" step="0.5" inputmode="decimal"></div>
<div class="field"><label for="m-periods">Periods</label><input id="m-periods" name="periods" type="number" min="0" step="0.5" inputmode="decimal"></div>
<div class="field"><label for="m-weight">Weight</label><input id="m-weight" name="weight" type="number" min="0" step="0.1" value="1" inputmode="decimal"></div>
</div>
<p class="hint">The module is saved for the selected department, trade and level, so every class of that level sees it.</p>
<div id="m-msg" class="note" hidden></div>
</div>
<div class="dlg-foot"><button type="button" class="btn" data-close>Cancel</button><button type="submit" class="btn primary" id="m-save">Save module</button></div>
</form>
</dialog>
<script>
const API="/api/academics/";
const PLACEHOLDERS={department:"Select a department…",trade:"Choose a department first",level:"Choose a trade first","class":"Choose a trade and level first"};
const CAN_EDIT=__CAN_EDIT__;
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const $=id=>document.getElementById(id);
const f={dept:$("f-dept"),trade:$("f-trade"),level:$("f-level"),class:$("f-class")};
const m={dept:$("m-dept"),trade:$("m-trade"),level:$("m-level"),class:$("m-class")};
let modules=[],selectedIds={module:null},q="",editing=null,refreshing=0;

/* The academic-cascade engine owns every selector's options: each list loads
   only the rows related to the selection above it, stays disabled (and shows
   "waiting for user selection") until then, and resets when a parent changes. */
async function getJSON(url){
  const r=await fetch(url,{headers:{Accept:"application/json"}});
  if(!r.ok)throw new Error("request failed");
  const data=await r.json();
  return Array.isArray(data)?data:(Array.isArray(data.modules)?data.modules:[]);
}
function renderNav(){
  const wrap=$("nav");wrap.innerHTML="";
  if(f.dept.value){const d=document.createElement("div");d.className="dept";d.textContent=navLabels.dept||"";wrap.appendChild(d);}
  if(f.trade.value){const t=document.createElement("div");t.className="trade";t.textContent=navLabels.trade||"";wrap.appendChild(t);}
  Array.from(f.class.options).filter(o=>o.value).forEach(o=>{
    const b=document.createElement("button");b.type="button";b.className="cls"+(o.value===f.class.value?" on":"");b.dataset.id=o.value;b.textContent=o.textContent;wrap.appendChild(b);
  });
  if(!wrap.children.length){const p=document.createElement("p");p.className="empty";p.textContent="Choose a department to list its classes.";wrap.appendChild(p);}
}
function bucket(cat){
  const c=String(cat||"").toLowerCase();
  return c.startsWith("comp")?"C":c.startsWith("gen")?"G":"S";
}
function fmt(n){return n==null||n===""?"—":String(Math.round(Number(n)*10)/10);}
function renderModules(){
  const chain=breadcrumb().join(" · ");
  let h=`<div class="top"><div><h2>${esc(pick(f.class))}</h2><div class="stats">${esc(chain)}</div></div>`;
  h+=`<div class="stats">${modules.length} module${modules.length===1?"":"s"} · ${fmt(modules.reduce((s,x)=>s+(Number(x.hours)||0),0))} h · ${fmt(modules.reduce((s,x)=>s+(Number(x.periods)||0),0))} periods</div>`;
  if(CAN_EDIT)h+=`<button type="button" class="btn primary" id="add-btn">+ Add module</button>`;
  h+=`</div><div id="msg" class="note" hidden></div><input id="q" class="search" placeholder="Search module code or title…" value="${esc(q)}">`;
  const rows=modules.filter(x=>((x.code||"")+" "+(x.name||"")).toLowerCase().includes(q.toLowerCase()));
  let shown=0;
  [[ "C","Complementary Modules","--c1"],["G","General Modules","--c2"],["S","Specific (Core) Modules","--c3"]].forEach(([k,t,col])=>{
    const list=rows.filter(x=>bucket(x.category)===k);
    if(!list.length)return;shown+=list.length;
    h+=`<div class="grp" style="--g:var(${col})"><div class="gh">${t}<span>${list.length} module${list.length===1?"":"s"} · ${fmt(list.reduce((s,x)=>s+(Number(x.hours)||0),0))} h</span></div><div class="tw"><table><tr><th>Code</th><th>Module title</th><th class="n">Hours</th><th class="n">Periods</th><th class="n">Weight</th>${CAN_EDIT?'<th>Actions</th>':""}</tr>`;
    h+=list.map(x=>`<tr><td><code>${esc(x.code||"—")}</code></td><td>${esc(x.name)}</td><td class="n">${fmt(x.hours)}</td><td class="n">${fmt(x.periods)}</td><td class="n">${fmt(x.weight)}</td>`+
      (CAN_EDIT?`<td><button type="button" class="btn mini" data-edit="${x.id}">Edit</button> <button type="button" class="btn mini danger" data-del="${x.id}">Remove</button></td>`:"")+`</tr>`).join("");
    h+=`</table></div></div>`;
  });
  if(!shown)h+=`<div class="empty">${modules.length?"No module matches the search.":"No modules yet for this class level. Use “Add module” to create the first one."}</div>`;
  $("main").innerHTML=h;
  const input=$("q");
  if(input)input.oninput=e=>{q=e.target.value;const p=input.selectionStart;renderModules();const n=$("q");n.focus();n.setSelectionRange(p,p);};
  const add=$("add-btn");if(add)add.onclick=()=>openDialog(null);
  $("main").querySelectorAll("[data-edit]").forEach(b=>b.onclick=()=>openDialog(Number(b.dataset.edit)));
  $("main").querySelectorAll("[data-del]").forEach(b=>b.onclick=()=>removeModule(Number(b.dataset.del)));
}
function message(text,ok){
  const box=$("msg");if(!box)return;
  box.hidden=!text;box.className="note "+(ok?"ok":"bad");box.textContent=text||"";
}
/* The dialog repeats the same cascade as the page. When it opens, pick the
   module's own department/trade/level/class by preselecting the dialog
   selectors; the cascade engine then loads each dependent list from the
   database and waits for the user before enabling the next input. */
function preset(g,name,value,then){
  const select=g[name];if(!value){if(then)then();return;}
  const typed=String(value);
  let tries=0;
  const attempt=()=>{
    const existed=Array.from(select.options).some(o=>o.value===typed);
    if(existed&&select.value===typed){select.dispatchEvent(new Event("change",{bubbles:true}));if(then)then();return;}
    if(tries++<40){setTimeout(attempt,50);return;}
    // Option not in the list: leave it unselected so the user must choose.
    if(then)then();
  };
  attempt();
}
function openDialog(id){
  if(!CAN_EDIT)return;
  $("dlg-form").reset();
  $("m-msg").hidden=true;
  const mod=id?modules.find(x=>Number(x.id)===Number(id)):null;
  editing=mod?Number(id):null;
  $("dlg-title").textContent=mod?"Edit module":"Add module";
  $("m-save").textContent=mod?"Save changes":"Save module";
  $("m-name").value=mod?mod.name:"";
  $("m-code").value=mod?mod.code:"";
  $("m-cat").value=mod?(mod.category||"Specific"):"Specific";
  $("m-hours").value=mod&&mod.hours!=null?mod.hours:"";
  $("m-periods").value=mod&&mod.periods!=null?mod.periods:"";
  $("m-weight").value=mod&&mod.weight!=null?mod.weight:1;
  $("dlg").showModal();
  preset(m,"dept",mod?mod.department_id:f.dept.value,()=>
    preset(m,"trade",mod?mod.trade_id:f.trade.value,()=>
      preset(m,"level",mod?mod.level:f.level.value,()=>
        preset(m,"class",mod&&mod.class_ids.length?mod.class_ids[0]:f.class.value))));
}
async function submitModule(ev){
  ev.preventDefault();
  const btn=$("m-save");
  if(!m.dept.value||!m.level.value){
    const box=$("m-msg");box.hidden=false;box.className="note bad";
    box.textContent="Choose a department and level (or a class) before saving the module.";
    return;
  }
  btn.disabled=true;
  const box=$("m-msg");box.hidden=true;
  const body={
    department_id:m.dept.value,trade_id:m.trade.value,level:m.level.value,class_id:m.class.value,
    name:$("m-name").value.trim(),code:$("m-code").value.trim(),category:$("m-cat").value,
    hours:$("m-hours").value,periods:$("m-periods").value,weight:$("m-weight").value
  };
  try{
    const r=await fetch(editing?API+"modules/"+editing:API+"modules",{
      method:editing?"PUT":"POST",headers:{"Content-Type":"application/json",Accept:"application/json"},body:JSON.stringify(body)});
    const data=await r.json().catch(()=>({}));
    if(!r.ok||data.ok===false){
      box.hidden=false;box.className="note bad";box.textContent=data.message||"The module could not be saved.";
      return;
    }
    $("dlg").close();
    q="";
    await loadModules();
    message(data.message||"Module saved.",true);
  }catch(e){
    box.hidden=false;box.className="note bad";box.textContent="Network error. Check the connection and try again.";
  }finally{btn.disabled=false;}
}
async function removeModule(id){
  const mod=modules.find(x=>Number(x.id)===Number(id));
  if(!mod)return;
  if(!confirm(`Remove “${mod.name}” from ${mod.level} ${mod.trade||""}? Historical grades keep their reference.`))return;
  try{
    const r=await fetch(API+"modules/"+id,{method:"DELETE",headers:{Accept:"application/json"}});
    const data=await r.json().catch(()=>({}));
    if(!r.ok||data.ok===false){message(data.message||"The module could not be removed.",false);return;}
    await loadModules();message(data.message||"Module removed.",true);
  }catch(e){message("Network error. Check the connection and try again.",false);}
}
/* Periods follow hours (1 period = 1.5 hours) but stay editable. */
function autoPeriods(){
  const h=$("m-hours"),p=$("m-periods");
  h.addEventListener("input",()=>{if(h.value!=="")p.value=String(Math.round(Number(h.value)*1.5*10)/10);});
}
/* Each cascade list keeps the option that was actually chosen, so the
   breadcrumb does not fall back to the "Choose a trade first" placeholder
   while the next list is still loading. */
function pick(sel){
  if(!sel||!sel.value)return "";
  const saved=sel.dataset.picked,label=sel.selectedOptions[0]?sel.selectedOptions[0].textContent.trim():sel.value;
  return saved&&sel.dataset.pickedValue===sel.value?saved:label;
}
function remember(sel){sel.dataset.picked=pick(sel);sel.dataset.pickedValue=sel.value;}
function breadcrumb(){
  return [pick(f.dept),pick(f.trade),f.level.value,pick(f.class)].filter(Boolean);
}
let navToken=0;
async function loadModules(){
  const wrap=$("main"),classId=f.class.value,token=++navToken;
  if(!classId){
    modules=[];renderNav();
    wrap.innerHTML='<div class="empty">Select a department, trade, level and class to see its modules.</div>';
    return;
  }
  renderNav();
  const chosen=pick(f.class),chain=breadcrumb().join(" · ");
  wrap.innerHTML=`<div class="top"><div><h2>${esc(chosen)}</h2><div class="stats">${esc(chain)}</div></div></div><div class="empty">Loading modules…</div>`;
  let rows=[];
  try{rows=await getJSON(API+"modules?class_id="+classId);}
  catch(e){
    if(token===navToken)wrap.innerHTML='<div class="empty">Could not load the modules for this class. Refresh and try again.</div>';
    return;
  }
  if(token!==navToken||classId!==f.class.value)return;
  modules=rows;
  renderModules();
}
f.dept.addEventListener("change",()=>{remember(f.dept);renderNav();});
f.trade.addEventListener("change",()=>{remember(f.trade);renderNav();});
f.level.addEventListener("change",()=>{remember(f.level);renderNav();loadModules();});
f.class.addEventListener("change",()=>{remember(f.class);loadModules();});
$("nav").addEventListener("click",e=>{const b=e.target.closest("button[data-id]");if(b&&b.dataset.id!==f.class.value){f.class.value=b.dataset.id;f.class.dispatchEvent(new Event("change",{bubbles:true}));}});
document.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>$("dlg").close());
$("dlg-form").addEventListener("submit",submitModule);
autoPeriods();
renderNav();loadModules();
</script>"""


def _bucket_for_category(category):
    return {
        "Complementary": "C",
        "General": "G",
        "Specific": "S",
    }.get((category or "").strip().title(), "A")


def _catalog_from_database():
    """Build the nested catalog from the relational tables.

    Shape mirrors the legacy JS structure:
    [{n: department, t: [{n: trade, c: [[class_name, {C:[],G:[],S:[],A:[]}]]}]}]
    Returns (catalog, is_db_backed).
    """
    catalog = []
    try:
        departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
        for department in departments:
            trades_payload = []
            trades = Trade.query.filter_by(department_id=department.id, is_active=True) \
                .order_by(Trade.name).all()
            for trade in trades:
                classes_payload = []
                classes = SchoolClass.query.filter_by(trade_id=trade.id, is_active=True) \
                    .order_by(SchoolClass.name).all()
                modules = AcademicModule.query.filter_by(trade_id=trade.id, is_active=True).all()
                modules_by_level = {}
                for module in modules:
                    modules_by_level.setdefault((module.level or "").casefold(), []).append(module)
                for klass in classes:
                    buckets = {"C": [], "G": [], "S": [], "A": []}
                    for module in modules_by_level.get((klass.level or "").casefold(), []):
                        bucket = _bucket_for_category(module.category)
                        buckets[bucket].append({
                            "code": module.code or "",
                            "title": module.name,
                            "h": int(module.weight or 0) or None,
                        })
                    classes_payload.append((klass.name, buckets))
                if classes_payload:
                    trades_payload.append({"n": trade.name, "c": classes_payload})
            if trades_payload:
                catalog.append({"n": department.name, "t": trades_payload})
    except Exception:
        # Database not ready (e.g. fresh install before migrations) - the
        # caller falls back to the transcribed catalog.
        db.session.rollback()
        return [], False
    return catalog, bool(catalog)


def _catalog_from_fallback():
    """Same shape, built from the transcribed data module."""
    catalog = []
    for department in FALLBACK_DEPARTMENTS:
        trades_payload = []
        for trade in department["trades"]:
            classes_payload = []
            for class_data in trade["classes"]:
                buckets = {"C": [], "G": [], "S": [], "A": []}
                for bucket, entries in class_data["modules"].items():
                    for entry in entries:
                        buckets[bucket].append({
                            "code": entry.get("code", ""),
                            "title": entry["title"],
                            "h": entry.get("hours") or None,
                        })
                classes_payload.append((class_data["name"], buckets))
            trades_payload.append({"n": trade["name"], "c": classes_payload})
        catalog.append({"n": department["name"], "t": trades_payload})
    return catalog


def _first_class_name(catalog):
    for department in catalog:
        for trade in department["t"]:
            if trade["c"]:
                return trade["c"][0][0]
    return ""


def classes_modules():
    import datetime
    from flask_login import current_user

    catalog, db_backed = _catalog_from_database()
    if not db_backed:
        catalog = _catalog_from_fallback()
    payload_json = json.dumps(catalog, ensure_ascii=False).replace("</", "<\\/")
    first_class = _first_class_name(catalog)
    year = f"{datetime.date.today().year}" \
           f"–{datetime.date.today().year + 1}"
    editors = ROLE_ACCESS.get("classes_modules_edit", set())
    can_edit = bool(current_user.is_authenticated and current_user.role in editors)
    body = CLASSES_MODULES_BODY \
        .replace("__CAN_EDIT__", "true" if can_edit else "false") \
        .replace("ACADEMIC_DEPTS", payload_json) \
        .replace("FIRST_CLASS", json.dumps(first_class, ensure_ascii=False)) \
        .replace("__YEAR__", escape(year))
    source_note = (
        "<p class='muted'>Showing modules from the relational academic catalog.</p>"
        if db_backed else
        "<p class='muted' role='status'>The relational module catalog has not been seeded yet; "
        "showing the reference curriculum. Run the application once to seed it.</p>")
    body = body.replace("</header>", f"{source_note}</header>")
    return page("Classes & Modules", body, "dashboard")


def register_routes(app):
    app.add_url_rule(
        "/classes-modules",
        endpoint="classes_modules",
        view_func=permission_for("classes_modules")(classes_modules),
        methods=["GET"],
    )
