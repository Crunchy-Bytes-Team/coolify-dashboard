"use strict";
const $ = id => document.getElementById(id);
const i18n = window.SentinelI18n;
const tr = (message, values) => i18n.t(message, values);
const state = {server:null,entity:"server",resources:[],hours:24,revision:0,overview:null,projects:null,charts:{},updatedAt:null,lastError:null};
const statusKeys = {fresh:"Aggiornato",stale:"Dati non recenti",waiting:"In attesa",error:"Lettura incompleta",partial:"Dati parziali"};
const statusText = new Proxy(statusKeys,{get:(labels,key)=>tr(labels[key]||"In attesa")});
let fmt = new Intl.NumberFormat(i18n.locale,{maximumFractionDigits:1});
let timeFmt = new Intl.DateTimeFormat(i18n.locale,{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"});
function valueText(value,metric) {
  if(value===null || value===undefined) return "—";
  if(metric==="cpu") return fmt.format(value)+"%";
  if(value>=1073741824) return fmt.format(value/1073741824)+" GiB";
  if(value>=1048576) return fmt.format(value/1048576)+" MiB";
  return fmt.format(value/1024)+" KiB";
}
function relative(ts) {
  if(!ts) return tr("Nessun campione");
  const seconds = Math.max(0,Math.floor((Date.now()-ts)/1000));
  if(seconds<60) return tr("{count} s fa",{count:fmt.format(seconds)});
  if(seconds<3600) return tr("{count} min fa",{count:fmt.format(Math.floor(seconds/60))});
  return timeFmt.format(ts);
}
function node(tag,className,text) {
  const element=document.createElement(tag);
  if(className)element.className=className;
  if(text!==undefined)element.textContent=text;
  return element;
}
function badge(status,text) { return node("span","badge "+status,text||statusText[status]||tr("In attesa")); }
async function api(path) {
  const response=await fetch(path,{cache:"no-store",signal:AbortSignal.timeout(15000)});
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||"Impossibile leggere i dati.");
  return data;
}
function renderServers(servers) {
  $("server-count").textContent=servers.length;
  $("servers").replaceChildren();
  for(const server of servers) {
    const button=node("button","server-button");button.type="button";
    const fresh=server.enabled&&!server.error&&server.metrics?.status==="fresh";
    const high=fresh&&((server.metrics.cpu??0)>=80||(server.metrics.memory_percent??0)>=80);
    if(high)button.classList.add("high-usage");
    button.setAttribute("aria-current",String(server.id===state.server));
    button.append(node("strong","",server.name));
    button.append(node("span","",!server.enabled?tr("Da collegare"):server.error?tr("Gateway non raggiungibile"):fresh?"CPU "+valueText(server.metrics.cpu,"cpu")+" · RAM "+valueText(server.metrics.memory_percent,"cpu"):tr("In attesa di campioni recenti")));
    if(high)button.append(node("span","usage-warning",tr("⚠ Utilizzo elevato")));
    button.title=fresh?tr("Soglia di attenzione: CPU o RAM ≥ 80%. ")+(server.metrics.memory_total?tr("RAM: {used} su {total}.",{used:valueText(server.metrics.memory,"memory"),total:valueText(server.metrics.memory_total,"memory")}):tr("Percentuale RAM non disponibile: manca la memoria totale.")):"";
    button.addEventListener("click",()=>{state.server=server.id;state.entity="server";refresh();});
    $("servers").append(button);
  }
}
function renderTable() {
  const query=$("search").value.trim().toLocaleLowerCase();
  const sort=$("sort").value;
  const resources=state.resources.filter(row=>row.id!=="server" && (row.name+" "+row.project).toLocaleLowerCase().includes(query));
  resources.sort((a,b)=>sort==="name"?a.name.localeCompare(b.name,i18n.locale):((b[sort]??-1)-(a[sort]??-1)));
  $("resource-count").textContent=state.resources.filter(r=>r.id!=="server").length;
  const body=$("resource-rows");body.replaceChildren();
  if(!resources.length) {
    const row=node("tr"),cell=node("td","table-empty",query?tr("Nessuna risorsa corrisponde alla ricerca."):tr("L'inventario comparirà dopo il collegamento del gateway."));
    cell.colSpan=5;row.append(cell);body.append(row);return;
  }
  for(const resource of resources) {
    const row=node("tr"),title=node("td"),button=node("button","resource-link",resource.name);
    button.type="button";button.addEventListener("click",()=>{state.entity=resource.id;refresh();});
    title.append(button,node("p","resource-project",[resource.project,resource.kind==="application"?tr("Applicazione"):resource.kind==="database"?"Database":resource.kind==="service"?tr("Servizio"):"Container",resource.running===0?tr("Non in esecuzione"):""].filter(Boolean).join(" · ")));
    const status=node("td");status.append(badge(resource.status));
    const at=Math.min(resource.cpu_at||0,resource.memory_at||0);
    const date=node("td","muted",relative(at));if(at)date.title=new Date(at).toLocaleString(i18n.locale);
    row.append(title,status,node("td","number",valueText(resource.cpu,"cpu")),node("td","number",valueText(resource.memory,"memory")),date);
    body.append(row);
  }
}
function renderProjects(data) {
    state.projects=data;
    $('project-count').textContent=data.projects.length;
    $('projects').replaceChildren();
    for(const project of data.projects) {
      const group=node('section','project-group');
      group.append(node('h3','',project.name));
      for(const resource of project.resources) {
        const button=node('button','project-resource');button.type='button';
        button.setAttribute('aria-current',String(resource.server===state.server&&resource.id===state.entity));
        button.append(node('span','',resource.name),node('small','muted',resource.server_name));
        button.addEventListener('click',()=>{state.server=resource.server;state.entity=resource.id;refresh();});
        group.append(button);
      }
      $('projects').append(group);
    }
    if(!data.projects.length)$('projects').append(node('p','muted',tr('Nessun progetto disponibile.')));
}
async function refreshProjects() {
  try { renderProjects(await api('/api/projects')); }
  catch { state.projects=null;$('projects').replaceChildren(node('p','muted',tr('Elenco progetti non disponibile.'))); }
}
function svgNode(tag,attrs,text) {
  const element=document.createElementNS("http://www.w3.org/2000/svg",tag);
  for(const [key,value] of Object.entries(attrs||{}))element.setAttribute(key,String(value));
  if(text!==undefined)element.textContent=text;
  return element;
}
function renderChart(metric,data,entity) {
  state.charts[metric]={data,entity};
  const area=$(metric+"-chart");
  area.replaceChildren();
  $(metric+"-value").textContent=valueText(entity?.[metric],metric);
  $(metric+"-freshness").textContent=entity?.[metric+"_at"]?tr("Ultimo campione · ")+relative(entity[metric+"_at"]):tr("Nessun campione");
  if(!data.samples.length) {
    area.append(node("p","plot-empty",tr("Nessun campione in questo periodo")));
    $(metric+"-summary").textContent=tr("I dati mancanti non vengono rappresentati come zero.");
    return;
  }
  const points=data.samples;
  const maximum=Math.max(...points.map(p=>p.high));
  const top=Math.max(maximum*1.1,metric==="cpu"?(state.entity==="server"?100:1):1048576);
  const left=56,right=588,up=15,bottom=168;
  const x=ts=>left+(ts-data.from)/(data.to-data.from)*(right-left);
  const y=value=>bottom-value/top*(bottom-up);
  const svg=svgNode("svg",{viewBox:"0 0 610 200",role:"img","aria-label":tr("{metric}, andamento nelle ultime {hours} ore",{metric:metric==="cpu"?"CPU":tr("Memoria"),hours:fmt.format(state.hours)})});
  svg.append(svgNode("title",{},metric==="cpu"?tr("Utilizzo CPU"):tr("Memoria utilizzata")));
  for(let i=0;i<=3;i++) {
    const value=top*i/3,position=y(value);
    svg.append(svgNode("line",{x1:left,x2:right,y1:position,y2:position,class:"grid"}));
    svg.append(svgNode("text",{x:left-8,y:position+4,"text-anchor":"end"},valueText(value,metric)));
  }
  for(const [ts,anchor] of [[data.from,"start"],[(data.from+data.to)/2,"middle"],[data.to,"end"]]) {
    const text=new Date(ts).toLocaleString(i18n.locale,state.hours>24?{day:"2-digit",month:"short"}:{hour:"2-digit",minute:"2-digit"});
    svg.append(svgNode("text",{x:x(ts),y:191,"text-anchor":anchor},text));
  }
  let path="",previous=null;
  for(const point of points) {
    const gap=previous===null||point.time-previous>data.bucket_ms*1.6;
    const pointX=Math.max(left,Math.min(right,x(point.time)));
    path+=(gap?"M":"L")+pointX.toFixed(2)+","+y(point.value).toFixed(2)+" ";
    previous=point.time;
  }
  svg.append(svgNode("path",{d:path,class:"trace"}));
  if(points.length===1)svg.append(svgNode("circle",{cx:Math.max(left,x(points[0].time)),cy:y(points[0].value),r:3,class:"point"}));
  area.append(svg);
  const weight=points.reduce((s,p)=>s+p.count,0);
  const average=points.reduce((s,p)=>s+p.value*p.count,0)/weight;
  $(metric+"-summary").textContent=tr("Media {average} · Picco {peak} · Solo campioni disponibili",{average:valueText(average,metric),peak:valueText(maximum,metric)});
}
function renderOverview(overview) {
  state.overview=overview;
    if(!state.server)state.server=overview.servers[0]?.id;
    renderServers(overview.servers);
    const server=overview.servers.find(s=>s.id===state.server);
    $("collection-info").textContent=tr("Sincronizzazione ogni {seconds} secondi. Conservazione: {days} giorni.",{seconds:fmt.format(overview.poll_seconds),days:fmt.format(overview.retention_days)});
    if(!server) {
      $("server-name").textContent=tr("Nessun server configurato");
      $("setup").hidden=false;
      return null;
    }
    $("server-name").textContent=server.name;
    $("server-subtitle").textContent=server.enabled?(server.contacted?tr("Ultimo contatto con il gateway · ")+relative(server.contacted):tr("In attesa del primo contatto con il gateway")):tr("Server pilota · Gateway HTTPS da collegare");
    $("setup").hidden=server.enabled;
    $("error").hidden=!server.error;
    $("error").textContent=server.error?i18n.error(server.error):"";
    const connection=server.enabled?(server.error?"error":server.metrics?.status||"waiting"):"waiting";
    $("connection").className="badge "+connection;
    $("connection").textContent=server.enabled?statusText[connection]:tr("Da collegare");
    return server;
}
function renderEntityCaption() {
  const entity=state.resources.find(r=>r.id===state.entity);
  $("entity-caption").textContent=state.entity==="server"?tr("Totale del server"):(entity?.name||tr("Risorsa"))+tr(" · storico dei container associati");
}
function renderUpdated() {
  if(state.updatedAt)$("updated").textContent=tr("Vista aggiornata alle ")+new Date(state.updatedAt).toLocaleTimeString(i18n.locale,{hour:"2-digit",minute:"2-digit"});
}
function showViewError(message) {
  state.lastError=message;
  $("error").textContent=i18n.error(message);$("error").hidden=false;
  $("connection").textContent=tr("Vista non aggiornata");$("connection").className="badge stale";
}
async function refresh() {
  const revision=++state.revision;
  $("refresh").disabled=true;
  try {
    const overview=await api("/api/overview");
    if(revision!==state.revision)return;
    const server=renderOverview(overview);
    refreshProjects();
    if(!server)return;
    const prefix="?"+new URLSearchParams({server:state.server});
    const entityParams=new URLSearchParams({server:state.server,entity:state.entity,hours:state.hours});
    const [resources,cpu,memory]=await Promise.all([api("/api/resources"+prefix),api("/api/history?"+entityParams+"&metric=cpu"),api("/api/history?"+entityParams+"&metric=memory")]);
    if(revision!==state.revision)return;
    state.resources=resources.resources;
    const entity=state.resources.find(r=>r.id===state.entity);
    renderEntityCaption();
    $("back-server").hidden=state.entity==="server";
    renderChart("cpu",cpu,entity);renderChart("memory",memory,entity);renderTable();
    updateAlarmTarget();
    state.lastError=null;state.updatedAt=Date.now();renderUpdated();
  }catch(error){
    if(revision!==state.revision)return;
    showViewError(error.name==="TimeoutError"?"La richiesta ha impiegato troppo tempo. Nuovo tentativo automatico.":error.message);
  }finally{
    if(revision===state.revision)$("refresh").disabled=false;
  }
}
$("refresh").addEventListener("click",refresh);
$("period").addEventListener("change",()=>{state.hours=Number($("period").value);refresh();});
$("search").addEventListener("input",renderTable);
$("sort").addEventListener("change",renderTable);
$("back-server").addEventListener("click",()=>{state.entity="server";refresh();});
setInterval(()=>{if(!document.hidden)refresh();},30000);
refresh();

// ALARM CORE START
const ALARM_REPEAT=300000;
function quietNow(settings,date=new Date()) {
  if(settings.manual)return true;
  if(!settings.schedule)return false;
  const minutes=text=>Number(text.slice(0,2))*60+Number(text.slice(3));
  const start=minutes(settings.start),end=minutes(settings.end),now=date.getHours()*60+date.getMinutes();
  return start<end?now>=start&&now<end:now>=start||now<end;
}
function alertDue(target,last,settings,now=Date.now()) {
  return settings.enabled&&!quietNow(settings,new Date(now))&&target.state==='active'&&
    (last===undefined||now-last>=ALARM_REPEAT||last>now);
}
// ALARM CORE END
const SETTINGS_KEY='sentinel.alerts.settings.v1', DELIVERY_KEY='sentinel.alerts.delivery.v1';
const alarmDefaults={enabled:true,sound:true,manual:false,schedule:true,start:'00:00',end:'06:00',cpu:80,memory:80,seconds:30,rules:[]};
function readStored(key,fallback) {try {return JSON.parse(localStorage.getItem(key))??fallback;}catch{return fallback;}}
function writeStored(key,value) {
  try {localStorage.setItem(key,JSON.stringify(value));return true;}
  catch {setFeedback(tr('Il browser non consente di salvare le preferenze. Mantieni aperta una sola scheda.'));return false;}
}
function validRule(rule) {
  return rule&&Number.isFinite(rule.cpu)&&rule.cpu>=1&&rule.cpu<=10000&&
    Number.isFinite(rule.memory)&&rule.memory>=1&&rule.memory<=(rule.entity==='server'?100:10485760)&&
    Number.isInteger(rule.seconds)&&rule.seconds>=10&&rule.seconds<=1800;
}
function loadAlarmSettings() {
  const saved=readStored(SETTINGS_KEY,{}),result={...alarmDefaults,rules:[]};
  for(const key of ['enabled','sound','manual','schedule'])if(typeof saved[key]==='boolean')result[key]=saved[key];
  for(const key of ['start','end'])if(/^([01]\d|2[0-3]):[0-5]\d$/.test(saved[key]))result[key]=saved[key];
  if(result.start===result.end){result.start='00:00';result.end='06:00';}
  if(validRule({...saved,entity:'server'})&&saved.cpu<=100)for(const key of ['cpu','memory','seconds'])result[key]=saved[key];
  if(Array.isArray(saved.rules))result.rules=saved.rules.filter(r=>validRule(r)&&typeof r.server==='string'&&typeof r.entity==='string'&&typeof r.name==='string').slice(0,20);
  return result;
}
let alarmSettings=loadAlarmSettings(),alarmRevision=0,alarmBusy=false,audioContext=null,lastAlarmTarget='',deliveryMemory={};
let feedback=null,lastAlarmSummary=null;
function setFeedback(message,values={}) { feedback={message:i18n.source(message),values};$('alarm-feedback').textContent=tr(feedback.message,values); }
function fillAlarmForm() {
  for(const [id,key] of [['alarms-enabled','enabled'],['alarm-sound','sound'],['dnd-manual','manual'],['dnd-schedule','schedule']])$(id).checked=alarmSettings[key];
  for(const [id,key] of [['alarm-cpu','cpu'],['alarm-memory','memory'],['alarm-duration','seconds'],['dnd-start','start'],['dnd-end','end']])$(id).value=alarmSettings[key];
  $('alarm-timezone').textContent=Intl.DateTimeFormat().resolvedOptions().timeZone;
  renderAlarmRules();permissionStatus();
}
function permissionStatus() {
  $('enable-alerts').textContent=tr(window.isSecureContext?'Abilita notifiche e audio':'Abilita audio');
  const permission=!window.isSecureContext?tr('Notifiche non disponibili su HTTP'):!('Notification' in window)?tr('Notifiche non supportate in questo browser'):Notification.permission==='granted'?tr('Notifiche autorizzate'):Notification.permission==='denied'?tr('Notifiche bloccate: consentile nelle impostazioni del browser'):tr('Notifiche da autorizzare');
  $('alarm-permission').textContent=permission+' · '+(audioContext?.state==='running'?tr('Audio pronto'):tr('Audio da abilitare per questa scheda'))+'.';
}
function updateAlarmTarget() {
  const key=state.server+'|'+state.entity;
  $('resource-memory-label').textContent=state.entity==='server'?tr('RAM (%)'):tr('RAM (MiB utilizzati)');
  if(key===lastAlarmTarget)return;
  lastAlarmTarget=key;
  const resource=state.resources.find(r=>r.id===state.entity);
  const rule=alarmSettings.rules.find(r=>r.server===state.server&&r.entity===state.entity);
  $('alarm-target').textContent=$('server-name').textContent+(state.entity==='server'?'': ' / '+(resource?.name||state.entity));
  $('resource-memory-label').textContent=state.entity==='server'?tr('RAM (%)'):tr('RAM (MiB utilizzati)');
  $('resource-alarm-memory').max=state.entity==='server'?100:10485760;
  $('resource-alarm-cpu').value=rule?.cpu??alarmSettings.cpu;
  $('resource-alarm-memory').value=rule?.memory??(state.entity==='server'?alarmSettings.memory:512);
  $('resource-alarm-duration').value=rule?.seconds??alarmSettings.seconds;
}
function renderAlarmRules() {
  $('alarm-rules').replaceChildren();
  for(const rule of alarmSettings.rules) {
    const item=node('li');
    item.append(node('span','',tr("{name} · CPU > {cpu}% o RAM > {memory}{unit} per {seconds} s",{name:rule.name,cpu:fmt.format(rule.cpu),memory:fmt.format(rule.memory),unit:rule.entity==='server'?'%':' MiB',seconds:fmt.format(rule.seconds)})));
    const remove=node('button','',tr('Rimuovi'));remove.type='button';remove.setAttribute('aria-label',tr('Rimuovi regola ')+rule.name);
    remove.addEventListener('click',()=>{alarmSettings.rules=alarmSettings.rules.filter(r=>r!==rule);saveAlarmSettings();renderAlarmRules();lastAlarmTarget='';updateAlarmTarget();});
    item.append(remove);$('alarm-rules').append(item);
  }
  if(!alarmSettings.rules.length)$('alarm-rules').append(node('li','muted',tr('Tutti i server usano le soglie generali. Aggiungi qui eventuali regole specifiche; per le applicazioni la RAM è espressa in MiB.')));
}
function saveAlarmSettings() {
  alarmRevision++;writeStored(SETTINGS_KEY,alarmSettings);pollAlarms();
}
function soundAlarm() {
  if(!alarmSettings.sound||audioContext?.state!=='running')return false;
  try {
    for(let i=0;i<3;i++) {
      const start=audioContext.currentTime+i*.3,osc=audioContext.createOscillator(),gain=audioContext.createGain();
      osc.frequency.value=i===1?740:880;gain.gain.setValueAtTime(0,start);gain.gain.linearRampToValueAtTime(.07,start+.02);gain.gain.linearRampToValueAtTime(0,start+.2);
      osc.connect(gain);gain.connect(audioContext.destination);osc.start(start);osc.stop(start+.22);
    }
    return true;
  }catch{return false;}
}
function deliverAlarm(targets,test=false) {
  if(!alarmSettings.enabled||quietNow(alarmSettings))return false;
  let sent=false;
  if('Notification' in window&&Notification.permission==='granted')try {
    const notification=new Notification(test?tr('Sentinel · Prova avviso'):tr('Sentinel · Utilizzo elevato'),{
      body:test?tr('Notifiche attive. Il suono viene riprodotto se abilitato.'):targets.slice(0,3).map(t=>t.name).join('\n')+(targets.length>3?"\n"+tr("Altre {count} risorse",{count:fmt.format(targets.length-3)}):''),tag:'sentinel-alerts',silent:true});
    notification.onclick=()=>{window.focus();if(targets[0]){state.server=targets[0].server;state.entity=targets[0].entity;refresh();}notification.close();};
    sent=true;
  }catch{/* Audio remains available if the browser cannot display notifications. */}
  return soundAlarm()||sent;
}
function renderAlarmSummary(summary) {
  if(!summary)return;
  lastAlarmSummary=summary;
  const {active,failures,unknown}=summary,quiet=quietNow(alarmSettings);
    $('alarm-mode').textContent=!alarmSettings.enabled?tr('Disattivati'):quiet?tr('Non disturbare attivo'):active.length?tr("{count} in corso",{count:fmt.format(active.length)}):tr('Attivi');
    $('alarm-banner').hidden=!active.length&&!failures&&!unknown;
    $('alarm-banner').textContent=(active.length?tr('Sopra soglia: ')+active.map(t=>t.name).join(', ')+'. ':'')+(!alarmSettings.enabled?tr('Allarmi disattivati. '):quiet?tr('Non disturbare: notifiche e suono silenziati. '):'')+((failures||unknown)?tr('Verifica incompleta: alcuni dati non sono disponibili.'):'');
}
async function pollAlarms() {
  if(alarmBusy)return;
  alarmBusy=true;const revision=alarmRevision;
  try {
    const rules=[{...alarmSettings,server:'*',entity:'server'},...alarmSettings.rules];
    const results=await Promise.allSettled(rules.map(rule=>api('/api/alert-status?'+new URLSearchParams({server:rule.server,entity:rule.entity,cpu:rule.cpu,memory:rule.memory,seconds:rule.seconds}))));
    if(revision!==alarmRevision)return;
    const targets=new Map();let failures=0;
    results.forEach((result,index)=>{
      const rule=rules[index];
      if(result.status==='rejected') {
        failures++;
        if(index)targets.set(rule.server+'|'+rule.entity,{key:rule.server+'|'+rule.entity,state:'unknown',name:rule.name});
        return;
      }
      for(const target of result.value.targets)targets.set(target.key,{...target,deliveryKey:JSON.stringify([target.key,rule.cpu,rule.memory,rule.seconds])});
    });
    const active=[...targets.values()].filter(t=>t.state==='active'),unknown=[...targets.values()].filter(t=>t.state==='unknown').length;
    const quiet=quietNow(alarmSettings);
    renderAlarmSummary({active,failures,unknown});
    const checkAndDeliver=()=>{
      if(revision!==alarmRevision)return;
      const stored=readStored(DELIVERY_KEY,{}),records=stored&&typeof stored==='object'&&!Array.isArray(stored)?stored:{};
      Object.assign(records,deliveryMemory);
      for(const target of targets.values())if(target.state==='normal'){delete records[target.deliveryKey];delete deliveryMemory[target.deliveryKey];}
      const now=Date.now(),due=active.filter(t=>alertDue(t,records[t.deliveryKey],alarmSettings,now));
      if(due.length&&deliverAlarm(due))for(const target of due)records[target.deliveryKey]=now;
      // Bound browser storage when rules or the inventory change.
      for(const key of Object.keys(records))if(!Number.isFinite(records[key])||now-records[key]>86400000)delete records[key];
      deliveryMemory=writeStored(DELIVERY_KEY,records)?{}:records;
    };
    if(navigator.locks)await navigator.locks.request('sentinel-alert-delivery',{ifAvailable:true},lock=>{if(lock)checkAndDeliver();});
    else checkAndDeliver();
  }catch {$('alarm-mode').textContent=tr('Verifica non disponibile');}
  finally {alarmBusy=false;}
}
$('alarm-toggle').addEventListener('click',()=>{$('alarm-settings').open=!$('alarm-settings').open;if($('alarm-settings').open)$('alarm-settings').scrollIntoView({block:'start'});});
$('alarm-form').addEventListener('submit',event=>{
  event.preventDefault();
  if($('dnd-start').value===$('dnd-end').value){setFeedback(tr('Scegli orari di inizio e fine diversi.'));return;}
  for(const [id,key] of [['alarms-enabled','enabled'],['alarm-sound','sound'],['dnd-manual','manual'],['dnd-schedule','schedule']])alarmSettings[key]=$(id).checked;
  for(const [id,key] of [['alarm-cpu','cpu'],['alarm-memory','memory'],['alarm-duration','seconds']])alarmSettings[key]=Number($(id).value);
  alarmSettings.start=$('dnd-start').value;alarmSettings.end=$('dnd-end').value;
  setFeedback(tr('Impostazioni salvate. Promemoria ogni 5 minuti durante il superamento.'));saveAlarmSettings();
});
$('resource-alarm-form').addEventListener('submit',event=>{
  event.preventDefault();if(!state.server)return;
  const rule={server:state.server,entity:state.entity,name:$('alarm-target').textContent,cpu:Number($('resource-alarm-cpu').value),memory:Number($('resource-alarm-memory').value),seconds:Number($('resource-alarm-duration').value)};
  const others=alarmSettings.rules.filter(r=>r.server!==rule.server||r.entity!==rule.entity);
  if(others.length>=20){setFeedback(tr('Puoi salvare al massimo 20 regole specifiche.'));return;}
  if(!validRule(rule))return;
  alarmSettings.rules=[...others,rule];saveAlarmSettings();renderAlarmRules();setFeedback("Regola salvata per {name}.",{name:rule.name});
});
$('enable-alerts').addEventListener('click',async()=>{
  try {
    const Audio=window.AudioContext||window.webkitAudioContext;
    if(Audio&&!audioContext)audioContext=new Audio();
    const resumed=audioContext?.resume();
    const permission=window.isSecureContext&&'Notification' in window&&Notification.permission==='default'?Notification.requestPermission():Promise.resolve();
    await Promise.allSettled([resumed,permission]);permissionStatus();pollAlarms();
  }catch {permissionStatus();}
});
$('test-alert').addEventListener('click',()=>{
  setFeedback(!alarmSettings.enabled?tr('Attiva gli allarmi prima della prova.'):quietNow(alarmSettings)?tr('Non disturbare è attivo: prova silenziata.'):deliverAlarm([],true)?tr('Avviso di prova inviato.'):tr('Premi “Abilita notifiche e audio” per preparare gli avvisi.'));
});
window.addEventListener('storage',event=>{if(event.key===SETTINGS_KEY){alarmSettings=loadAlarmSettings();alarmRevision++;fillAlarmForm();lastAlarmTarget='';updateAlarmTarget();pollAlarms();}});
fillAlarmForm();setInterval(pollAlarms,10000);pollAlarms();

window.addEventListener('sentinel-language-change',()=>{
  fmt=new Intl.NumberFormat(i18n.locale,{maximumFractionDigits:1});
  timeFmt=new Intl.DateTimeFormat(i18n.locale,{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"});
  if(state.overview)renderOverview(state.overview);
  if(state.projects)renderProjects(state.projects);
  else $('projects').replaceChildren(node('p','muted',tr('Elenco progetti non disponibile.')));
  renderTable();renderEntityCaption();
  for(const [metric,{data,entity}] of Object.entries(state.charts))renderChart(metric,data,entity);
  renderUpdated();if(state.lastError)showViewError(state.lastError);
  renderAlarmRules();updateAlarmTarget();permissionStatus();renderAlarmSummary(lastAlarmSummary);
  if(feedback)$('alarm-feedback').textContent=tr(feedback.message,feedback.values);
});
