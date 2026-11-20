// Project management preview. Target counts are approved results, independent of Run status.
let projectSearch='',targetSequence=1;
function vnDate(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
function periodDates(period,start=vnDate()){
  const date=new Date(start+'T00:00:00Z');
  if(period==='month'){date.setUTCDate(1);const first=date.toISOString().slice(0,10);date.setUTCMonth(date.getUTCMonth()+1);date.setUTCDate(0);return {start:first,end:date.toISOString().slice(0,10)};}
  const first=date.toISOString().slice(0,10);date.setUTCDate(date.getUTCDate()+6);return {start:first,end:date.toISOString().slice(0,10)};
}
function defaultPeriod(period){
  if(period==='month')return periodDates('month');
  const date=new Date(vnDate()+'T00:00:00Z');date.setUTCDate(date.getUTCDate()-((date.getUTCDay()+6)%7));return periodDates('week',date.toISOString().slice(0,10));
}
function initializeProjectUI(){
  projects.forEach(p=>{
    p.pmId=agents.find(a=>a.name===p.pm)?.id;
    p.memberIds=[...new Set([p.pmId,...processes.filter(x=>x.project===p.id).flatMap(x=>graphs[x.id].map(n=>n.agentId))].filter(Boolean))];
    const period=p.id==='internal'?'week':'month';
    p.targets=[{id:'target-'+targetSequence++,title:p.target,period,...defaultPeriod(period),total:p.total,done:p.done,criteria:p.id==='internal'?'Đồng bộ hoàn tất và được kiểm tra.':'PM duyệt nội dung và xác nhận kết quả.'}];
    syncProjectTarget(p);
  });
}
function currentProjectTarget(p){
  const today=vnDate();return (p.targets||[]).filter(t=>t.start<=today&&t.end>=today).sort((a,b)=>(a.period==='month'?-1:1)-(b.period==='month'?-1:1)||b.start.localeCompare(a.start))[0];
}
function syncProjectTarget(p){const target=currentProjectTarget(p);p.target=target?.title||'Chưa có target kỳ này';p.done=target?.done||0;p.total=target?.total||0;}
function projectAssignedIds(p){return [...new Set(processes.filter(x=>x.project===p.id&&!x.archived).flatMap(x=>[...(graphs[x.id]||[]),...(processDrafts[x.id]||[])].map(n=>n.agentId)))];}
function projectAgents(p){const ids=new Set([p.pmId,...p.memberIds,...projectAssignedIds(p)]);return agents.filter(a=>ids.has(a.id));}
function projectProblems(p){
  const failed=runs.filter(r=>processById(r.process)?.project===p.id&&runNeedsAttention(r));
  return failed;
}
function projectStatus(p){
  const failed=projectProblems(p);
  if(p.archived)return '<span class="badge stopped">Archived</span>';
  if(failed.length)return `<button class="badge failed status-button" data-action="open-run" data-id="${failed[0].id}" title="${escapeHTML(processById(failed[0].process).name)}">${failed.length} lỗi</button>`;
  if(!currentProjectTarget(p))return '<span class="badge stopped">Chưa có target</span>';
  return '<span class="badge active">Không có lỗi</span>';
}
function projectProgress(p){
  const target=currentProjectTarget(p);if(!target)return '—';
  const pct=Math.round(target.done/target.total*100);
  return `<div class="overview-progress"><strong>${target.done} / ${target.total} <small>· ${pct}%</small></strong><div class="progress-line"><span style="width:${Math.min(100,pct)}%"></span></div></div>`;
}
function projectListPage(){
  const list=projects.filter(p=>!!p.archived===!!state.showArchivedProjects&&[p.name,p.pm].join(' ').toLocaleLowerCase('vi').includes(projectSearch.toLocaleLowerCase('vi')));
  return `<div class="page-heading"><div class="heading-copy"><h1>Projects</h1></div><div class="heading-actions">${button('New project','plus','primary','data-action="new-project"')}${button(state.showArchivedProjects?'Active':'Archived','history','','data-action="archive-projects"')}</div></div><div class="robot-toolbar"><input class="input" type="search" id="project-search" placeholder="Search projects" aria-label="Search projects" value="${escapeHTML(projectSearch)}"></div>`+table(['Project','PM','Target','Progress','Processes','Status'],list.map(p=>{const target=currentProjectTarget(p);return `<tr><td><button class="entity-link" ${projectLink(p.id)}>${escapeHTML(p.name)}</button></td><td>${escapeHTML(agents.find(a=>a.id===p.pmId)?.name||p.pm)}</td><td>${target?`${escapeHTML(target.title)}<small class="cell-note">${target.period==='month'?'Monthly':'Weekly'} · ${target.start} → ${target.end}</small>`:'—'}</td><td>${projectProgress(p)}</td><td>${processes.filter(x=>x.project===p.id&&!x.archived).length}</td><td>${projectStatus(p)}</td></tr>`;}).join(''));
}
function projectDetailPage(){
  const p=projectById(state.project),list=processes.filter(x=>x.project===p.id&&!!x.archived===!!state.showArchivedProcesses),projectRuns=runs.filter(r=>processById(r.process)?.project===p.id),target=currentProjectTarget(p);
  const tabs=[['processes','Processes'],['team','Team'],['targets','Targets'],['results','Runs']];
  let body='';
  if(state.tab==='team')body=projectTeamTable(p);
  else if(state.tab==='targets')body=projectTargetTable(p);
  else if(state.tab==='results')body=`<div class="project-run-filters"><button class="${state.projectRunFilter==='running'?'':'active'}" data-action="project-run-filter" data-id="all">All</button><button class="${state.projectRunFilter==='running'?'active':''}" data-action="project-run-filter" data-id="running">Running</button></div>`+runTable(projectRuns.filter(r=>state.projectRunFilter!=='running'||['running','cancelling'].includes(r.status)));
  else body=`<div class="project-toolbar"><span>${list.length} processes</span><div class="row-controls">${button(state.showArchivedProcesses?'Active':'Archived','history','','data-action="archive-processes"')}${button('New process','plus','primary',`data-action="new-process" ${p.archived?'disabled':''}`)}</div></div>${compactProcessTable(list)}`;
  return `<button class="text-button" data-route="projects">← Projects</button><div class="page-heading"><div class="heading-copy"><h1>${escapeHTML(p.name)}</h1></div><div class="heading-actions">${p.archived?button('Restore project','refresh','primary',`data-action="restore-project" data-id="${p.id}"`):button('Edit project','file','',`data-action="edit-project" data-id="${p.id}"`)+button('Delete','trash','danger',`data-action="delete-project" data-id="${p.id}"`)}</div></div><div class="project-brief"><span>PM <strong>${escapeHTML(agents.find(a=>a.id===p.pmId)?.name||p.pm)}</strong></span><button class="text-button" data-action="project-tab" data-id="targets">Target <strong>${target?target.done+' / '+target.total:'—'}</strong></button><button class="text-button" data-action="project-tab" data-id="results"><strong>${projectRuns.filter(r=>['running','cancelling'].includes(r.status)).length}</strong> running</button>${projectStatus(p)}</div><div class="review-tabs">${tabs.map(([id,label])=>`<button class="${state.tab===id?'active':''}" data-action="project-tab" data-id="${id}">${label}</button>`).join('')}</div>${body}`;
}
function compactProcessTable(list){
  return table(['Process','Schedule','Next run','Last run','Actions'],list.map(p=>{const last=runs.find(r=>r.process===p.id),disabled=!p.version||p.archived||projectById(p.project).archived;
    return `<tr><td><button class="entity-link" data-action="open-process" data-id="${p.id}">${escapeHTML(p.name)}</button><small class="cell-note">${p.version?'Published v'+p.version:'Draft'} · ${p.tasks} tasks</small></td><td>${scheduleText(p)}<small class="cell-note">${p.frequency==='manual'?'Manual':`${p.enabled?'On':'Off'} · v${p.scheduleVersion||p.version}`}</small></td><td>${nextLabel(p)}</td><td>${last?`<button class="run-status-button" data-action="open-run" data-id="${last.id}">${badge(last.status)}</button>`:'—'}</td><td><div class="row-controls">${button('Run','play-circle','small',`data-action="run-now" data-id="${p.id}" title="Run v${p.version}" ${disabled?'disabled':''}`)}${button(p.enabled?'Stop':'Start',p.enabled?'close':'play-circle',p.enabled?'small':'small primary',`data-action="toggle-process" data-id="${p.id}" ${disabled||p.frequency==='manual'?'disabled':''}`)}<button class="button small process-menu-trigger" aria-label="More actions for ${escapeHTML(p.name)}" aria-haspopup="menu" data-action="process-menu" data-id="${p.id}">⋯</button></div></td></tr>`;
  }).join(''));
}
function closeProcessMenu(){document.getElementById('process-action-menu')?.remove();}
function openProcessMenu(id,anchor){
  const existing=document.getElementById('process-action-menu'),same=existing?.dataset.id===id;closeProcessMenu();if(same)return;
  const p=processById(id),menu=document.createElement('div');menu.id='process-action-menu';menu.className='process-action-menu';menu.dataset.id=id;menu.setAttribute('role','menu');
  menu.innerHTML=button('Schedule','clock','small',`role="menuitem" data-action="schedule" data-id="${id}" ${!p.version||p.archived||projectById(p.project).archived?'disabled':''}`)+(p.archived?button('Restore','refresh','small',`role="menuitem" data-action="restore-process" data-id="${id}"`):button('Edit','file','small',`role="menuitem" data-action="edit-process" data-id="${id}"`))+button('Delete','trash','small danger',`role="menuitem" data-action="delete-process" data-id="${id}"`);
  document.body.append(menu);const rect=anchor.getBoundingClientRect();menu.style.left=Math.max(8,Math.min(rect.right-menu.offsetWidth,innerWidth-menu.offsetWidth-8))+'px';menu.style.top=(rect.bottom+menu.offsetHeight>innerHeight?Math.max(8,rect.top-menu.offsetHeight-6):rect.bottom+6)+'px';menu.querySelector('button:not(:disabled)')?.focus({preventScroll:true});
}
function projectTeamTable(p){
  const members=projectAgents(p);
  return `<div class="project-toolbar"><span>${members.length} agents</span>${button('Manage team','agent','',`data-action="project-team" ${p.archived?'disabled':''}`)}</div>`+table(['Agent','Role','Model','Tasks'],members.map(a=>{
    const count=processes.filter(x=>x.project===p.id&&!x.archived).flatMap(x=>graphs[x.id]).filter(n=>n.agentId===a.id).length;
    return `<tr><td><strong>${escapeHTML(a.name)}</strong>${a.archived?'<small class="cell-note">Archived</small>':''}</td><td>${a.id===p.pmId?'<span class="badge running">PM</span>':escapeHTML(a.role)}</td><td>${escapeHTML(a.model)}</td><td>${count}</td></tr>`;
  }).join(''));
}
function projectTeamDialog(){
  const p=projectById(state.project),required=new Set([p.pmId,...projectAssignedIds(p)]),selected=new Set(projectAgents(p).map(a=>a.id));
  showDialog('Team',`<form id="project-team-form"><fieldset class="resource-picker"><legend>Agents</legend>${agents.filter(a=>!a.archived||selected.has(a.id)).map(a=>`<label><input type="checkbox" name="memberIds" value="${a.id}" ${selected.has(a.id)?'checked':''} ${required.has(a.id)?'disabled':''}>${escapeHTML(a.name)}${a.id===p.pmId?' · PM':required.has(a.id)?' · assigned':''}</label>`).join('')}</fieldset><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">Save</button></div></form>`);
}
function projectTargetTable(p){
  return `<div class="project-toolbar"><span>Approved results</span>${button('New target','plus','primary',`data-action="project-target-new" ${p.archived?'disabled':''}`)}</div>`+table(['Target','Period','Approved','Acceptance criteria','Actions'],(p.targets||[]).map(t=>`<tr><td><strong>${escapeHTML(t.title)}</strong></td><td>${t.period==='week'?'Weekly':'Monthly'}<small class="cell-note">${t.start} → ${t.end}</small></td><td>${t.done} / ${t.total}</td><td>${escapeHTML(t.criteria)}</td><td>${button('Edit','file','small',`data-action="project-target-edit" data-id="${t.id}" ${p.archived?'disabled':''}`)}</td></tr>`).join(''));
}
function projectTargetDialog(id=''){
  const target=(projectById(state.project).targets||[]).find(t=>t.id===id),period=target?.period||'month';
  showDialog(id?'Edit target':'New target',`<form id="project-target-form" data-id="${id}"><label class="form-field"><span>Target</span><input class="input" name="title" required maxlength="180" value="${escapeHTML(target?.title||'')}"></label><div class="form-row"><label class="form-field"><span>Period</span><select class="input" name="period"><option value="month" ${period==='month'?'selected':''}>Monthly</option><option value="week" ${period==='week'?'selected':''}>Weekly</option></select></label><label class="form-field"><span>Start</span><input class="input" name="start" type="date" required value="${target?.start||defaultPeriod(period).start}"></label></div><div class="form-row"><label class="form-field"><span>Goal</span><input class="input" name="total" type="number" min="1" step="1" required value="${target?.total||1}"></label><label class="form-field"><span>Approved</span><input class="input" name="done" type="number" min="0" step="1" required value="${target?.done||0}"></label></div><label class="form-field"><span>Acceptance criteria</span><textarea class="textarea" name="criteria" required maxlength="2000">${escapeHTML(target?.criteria||'')}</textarea></label><p id="project-target-error" class="form-error" role="alert"></p><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">Save</button></div></form>`);
}
function saveProjectTarget(form){
  const p=projectById(state.project),data=Object.fromEntries(new FormData(form)),error=document.getElementById('project-target-error');
  const values={title:data.title.trim(),criteria:data.criteria.trim(),period:data.period,total:Number(data.total),done:Number(data.done)};
  if(!values.title||!values.criteria||!['week','month'].includes(values.period)||!/^\d{4}-\d{2}-\d{2}$/.test(data.start)||!Number.isInteger(values.total)||values.total<1||!Number.isInteger(values.done)||values.done<0){error.textContent='Kiểm tra Target, Period, Goal, Approved và tiêu chí nghiệm thu.';return;}
  let dates;try{dates=periodDates(values.period,data.start);}catch{error.textContent='Ngày không hợp lệ.';return;}
  Object.assign(values,dates);p.targets??=[];
  const target=p.targets.find(t=>t.id===form.dataset.id);if(target)Object.assign(target,values);else p.targets.push({id:'target-'+targetSequence++,...values});
  syncProjectTarget(p);modalRoot.innerHTML='';render();
}
function projectEntityDialog(id=''){
  const p=projectById(id);
  showDialog(id?'Edit project':'New project',`<form id="project-entity-form" data-id="${id}"><label class="form-field"><span>Name</span><input class="input" name="name" required maxlength="120" value="${escapeHTML(p?.name||'')}"></label><label class="form-field"><span>Description</span><textarea class="textarea" name="desc" maxlength="1000">${escapeHTML(p?.desc||'')}</textarea></label><label class="form-field"><span>PM</span><select class="input" name="pmId" required>${agents.filter(a=>!a.archived&&canAssignProjectPM(a)||a.id===p?.pmId).map(a=>`<option value="${a.id}" ${a.id===p?.pmId?'selected':''}>${escapeHTML(a.name)}${a.archived?' (Archived)':''}</option>`).join('')}</select></label><p id="project-entity-error" class="form-error" role="alert"></p><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">Save</button></div></form>`);
}
function saveProjectEntity(form){
  const data=new FormData(form),name=data.get('name').trim(),pm=agents.find(a=>a.id===data.get('pmId')&&!a.archived),id=form.dataset.id;
  if(!name||!pm||!canAssignProjectPM(pm)){document.getElementById('project-entity-error').textContent='Nhập Name và chọn PM đang hoạt động.';return;}
  if(id){const p=projectById(id);Object.assign(p,{name,desc:data.get('desc').trim(),pmId:pm.id,pm:pm.name});p.memberIds=[...new Set([...p.memberIds,pm.id])];}
  else {const p={id:'project-'+entitySequence++,name,desc:data.get('desc').trim(),pmId:pm.id,pm:pm.name,memberIds:[pm.id],targets:[],target:'Chưa có target kỳ này',done:0,total:0,health:'active'};projects.push(p);state.project=p.id;state.tab='processes';}
  modalRoot.innerHTML='';navigate('project');
}
