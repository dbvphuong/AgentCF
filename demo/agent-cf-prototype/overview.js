// Attention tracking is separate from immutable execution history.
const handledRunAlerts=new Map();
const runNeedsAttention=run=>run.status==='failed'&&!handledRunAlerts.has(run.id);
function overviewPage(){
  const failed=runs.filter(run=>runNeedsAttention(run)&&!processById(run.process)?.archived&&!projectById(processById(run.process)?.project)?.archived);
  const offline=pcs.filter(pc=>!pc.removed&&!pc.disabled&&pc.status==='offline');
  const alerts=failed.length;
  const attention=alerts?`<section class="overview-errors" aria-labelledby="overview-errors-title"><h2 id="overview-errors-title">${icon('close')} ${alerts} cảnh báo</h2>${failed.map(run=>`<div class="overview-alert-row"><button class="overview-alert-link" data-action="open-run" data-id="${run.id}"><span><strong>${escapeHTML(processById(run.process).name)}</strong> · ${escapeHTML(projectById(processById(run.process).project).name)}<small>${escapeHTML(run.logs.at(-1)||'Run thất bại.')}</small></span><span>Logs →</span></button><button class="overview-alert-resolve" data-action="handle-run-alert" data-id="${run.id}">Đã xử lý</button></div>`).join('')}</section>`:'';
  const rows=projects.filter(p=>!p.archived).map(p=>{
    const target=currentProjectTarget(p),running=runs.filter(r=>processById(r.process)?.project===p.id&&['running','cancelling'].includes(r.status)).length;
    return `<tr><td><button class="entity-link" ${projectLink(p.id)}>${escapeHTML(p.name)}</button><small class="cell-note">PM · ${escapeHTML(agents.find(a=>a.id===p.pmId)?.name||p.pm)}</small></td><td>${target?`${escapeHTML(target.title)}<small class="cell-note">${target.period==='week'?'Weekly':'Monthly'} · ${target.start} → ${target.end}</small>`:'—'}</td><td>${projectProgress(p)}</td><td>${running?`<button class="badge running status-button" data-action="project-running" data-id="${p.id}">${running} running</button>`:'—'}</td><td>${projectStatus(p)}</td></tr>`;
  }).join('');
  return `<div class="page-heading"><div class="heading-copy"><h1>Overview</h1></div></div>`+attention+`<section class="overview-section" aria-labelledby="project-progress-title"><div class="section-heading"><h2 id="project-progress-title">Projects</h2>${offline.length?`<button class="text-button pc-notice" data-route="runners">${offline.length} PC offline →</button>`:''}</div>${table(['Project','Target','Progress','Running','Status'],rows)}</section>`+overviewTokenTable();
}
function overviewTokenOrder(list){return [...list].sort((a,b)=>b.tokens-a.tokens);}
function overviewTokenTable(){
  const total=agents.reduce((sum,a)=>sum+a.tokens,0);
  return `<section class="overview-section" aria-labelledby="agent-token-title"><div class="section-heading"><h2 id="agent-token-title">Agent tokens</h2><span class="token-total">Tháng này <strong>${formatTokens(total)}</strong></span></div>`+table(['Agent','Model','Tokens'],overviewTokenOrder(agents).map(a=>`<tr><td><button class="entity-link" data-action="agent-token-detail" data-id="${a.id}">${escapeHTML(a.name)}</button><small class="cell-note">${escapeHTML(a.role)}</small></td><td>${escapeHTML(a.model)}</td><td>${formatTokens(a.tokens)}</td></tr>`).join(''))+'</section>';
}
function agentTokenDetail(id){
  const agent=agents.find(a=>a.id===id);if(!agent)return;
  showDialog(agent.name,`<span>Tháng này</span><dl class="pc-specs"><div><dt>Model</dt><dd>${escapeHTML(agent.model)}</dd></div><div><dt>Tokens</dt><dd>${new Intl.NumberFormat('en-US').format(agent.tokens)}</dd></div></dl>`,button('Edit agent','file','',`data-action="edit-resource" data-type="agent" data-id="${agent.id}"`));
}
function handleRunAlert(id,reopen=false){
  const run=runs.find(r=>r.id===id);if(!run||run.status!=='failed')return;
  if(reopen)handledRunAlerts.delete(id);else handledRunAlerts.set(id,{handledAt:new Date().toISOString()});
  modalRoot.innerHTML='';render();showToast(reopen?'Đã mở lại cảnh báo.':'Đã xử lý cảnh báo. Lịch sử run giữ nguyên.');
}
