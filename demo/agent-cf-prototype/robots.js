// Robot catalog and Process node UI. All executions and statistics are sample data.
const robots=[
  {id:'robot-import',name:'Import data',desc:'Nhập và chuẩn hóa dữ liệu.',versions:[{number:1,entry:'import_data.py',notes:'Initial release',succeeded:36,failed:4,cancelled:2},{number:2,entry:'import_data.py',notes:'Validate input',succeeded:19,failed:1,cancelled:0}]},
  {id:'robot-report',name:'Export report',desc:'Tạo file báo cáo từ dữ liệu đầu vào.',versions:[{number:1,entry:'export_report.py',notes:'Initial release',succeeded:48,failed:2,cancelled:1}]},
  {id:'robot-sync',name:'Sync files',desc:'Đồng bộ file trong thư mục được cấp quyền.',versions:[{number:1,entry:'sync_files.py',notes:'Initial release',succeeded:0,failed:0,cancelled:0}]}
];
const processDrafts={},processVersions={};
let robotSequence=1,showArchivedRobots=false,robotSearch='',robotPosition=null;
function initializeRobotUI(){
  robots.forEach(r=>r.activeVersion=r.versions.at(-1).number);
  processes.forEach(p=>{if(p.version){processVersions[p.id]={[p.version]:structuredClone(graphs[p.id])};p.scheduleVersion=p.version;}});
  runs.forEach(run=>run.graphSnapshot=structuredClone(graphs[run.process]));
}
const robotById=id=>robots.find(r=>r.id===id);
const robotVersion=(r,number)=>r.versions.find(v=>v.number===Number(number));
const activeRobotVersion=r=>robotVersion(r,r.activeVersion)||r.versions.at(-1);
const builderNodes=()=>processDrafts[state.process]||graphs[state.process];
function robotRate(version){const finished=version.succeeded+version.failed;return finished?Math.round(version.succeeded/finished*100):null;}
function robotsPage(){
  const list=robots.filter(r=>!!r.archived===showArchivedRobots&&r.name.toLocaleLowerCase('vi').includes(robotSearch.toLocaleLowerCase('vi')));
  return `<div class="page-heading"><div class="heading-copy"><h1>Robots</h1></div><div class="heading-actions">${button('New robot','plus','primary','data-action="robot-new"')}${button(showArchivedRobots?'Active':'Archived','history','','data-action="robot-archived"')}</div></div><div class="robot-toolbar"><input id="robot-search" class="input" type="search" aria-label="Search robots" placeholder="Search robots" value="${escapeHTML(robotSearch)}"></div>`+table(['Robot','Version','Success rate','Runs','Actions'],list.map(r=>{
    const v=activeRobotVersion(r),rate=robotRate(v);
    return `<tr><td><strong>${escapeHTML(r.name)}</strong><small class="cell-note">${escapeHTML(r.desc)}</small></td><td><span class="robot-active-version">v${v.number}</span></td><td>${rate===null?'<span class="cell-note">Chưa có dữ liệu</span>':`<span class="pc-metric" tabindex="0" data-tooltip="${v.succeeded} thành công / ${v.succeeded+v.failed} lần kết thúc\n${v.failed} lỗi · ${v.cancelled} hủy" aria-label="${rate}% thành công">${rate}%</span>`}</td><td>${v.succeeded+v.failed}<small class="cell-note">${v.failed} failed</small></td><td><div class="row-controls">${r.archived?button('Restore','refresh','small',`data-action="robot-restore" data-id="${r.id}"`):button('Edit','file','small',`data-action="robot-edit" data-id="${r.id}"`)+button('New version','upload','small',`data-action="robot-version" data-id="${r.id}"`)+button('Delete','trash','small danger',`data-action="robot-delete" data-id="${r.id}"`)}</div></td></tr>`;
  }).join(''));
}
function robotDialog(id='',newVersion=false){
  const robot=robotById(id),version=robot?.versions.at(-1);
  const field=(name,label,value='',required=false)=>`<label class="form-field"><span>${label}</span><input class="input" name="${name}" value="${escapeHTML(value)}" maxlength="200" ${required?'required':''}></label>`;
  showDialog(newVersion?`New version · ${robot.name}`:id?'Edit robot':'New robot',`<form id="robot-form" data-id="${id}" data-version="${newVersion}">${newVersion?field('version','Version','v'+(version.number+1)):field('name','Name',robot?.name||'',true)+`<label class="form-field"><span>Description</span><textarea class="textarea" name="desc" maxlength="1000">${escapeHTML(robot?.desc||'')}</textarea></label>`}${id&&!newVersion?`<label class="form-field"><span>Active version ${settingsHelp('Chỉ làm mặc định khi thêm node mới; không đổi version đã gán trong Process.')} </span><select class="input" name="activeVersion" required>${[...robot.versions].reverse().map(v=>`<option value="${v.number}" ${v.number===activeRobotVersion(robot).number?'selected':''}>v${v.number}</option>`).join('')}</select></label>`:''}${!id||newVersion?field('entry','Entry point',version?.entry||'',true)+field('notes','Changes'):''}<p class="form-error" id="robot-error" role="alert"></p><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">${newVersion?'Create version':'Save'}</button></div></form>`);
  if(newVersion)document.querySelector('#robot-form [name=version]').readOnly=true;
}
function saveRobot(form){
  const id=form.dataset.id,newVersion=form.dataset.version==='true',data=new FormData(form),robot=robotById(id),fail=msg=>document.getElementById('robot-error').textContent=msg;
  const name=String(data.get('name')||'').trim(),entry=String(data.get('entry')||'').trim();
  if(!newVersion&&(!name||robots.some(r=>r.id!==id&&r.name.toLowerCase()===name.toLowerCase())))return fail('Tên bắt buộc và không được trùng.');
  if((!id||newVersion)&&!entry)return fail('Nhập Entry point.');
  const version={number:robot?robot.versions.at(-1).number+1:1,entry,notes:String(data.get('notes')||'').trim(),succeeded:0,failed:0,cancelled:0};
  if(newVersion){robot.versions.push(version);}
  else if(robot){const activeVersion=Number(data.get('activeVersion'));if(!robotVersion(robot,activeVersion))return fail('Chọn version hợp lệ.');Object.assign(robot,{name,desc:data.get('desc').trim(),activeVersion});}
  else robots.push({id:'robot-custom-'+robotSequence++,name,desc:data.get('desc').trim(),activeVersion:1,versions:[version]});
  modalRoot.innerHTML='';navigate('tools');showToast(newVersion?'Đã tạo version mới. Active version giữ nguyên.':'Đã lưu Robot.');
}
function robotReferences(id){
  return processes.filter(p=>[graphs[p.id],processDrafts[p.id],...Object.values(processVersions[p.id]||{})].filter(Boolean).some(nodes=>nodes.some(n=>n.robotId===id))||runs.some(r=>(r.graphSnapshot||[]).some(n=>n.robotId===id)&&r.process===p.id));
}
function robotDeleteDialog(id){
  const robot=robotById(id),refs=robotReferences(id),keep=refs.length||robot.versions.some(v=>v.succeeded+v.failed+v.cancelled>0);
  showDialog(`${keep?'Archive':'Delete'} robot?`,`<p><strong>${escapeHTML(robot.name)}</strong></p><p>${keep?'Giữ version, thống kê và lịch sử. Process dùng Robot này sẽ không tạo run mới.':'Xóa Robot chưa sử dụng khỏi danh mục.'}</p>${refs.length?`<ul class="resource-usage">${refs.map(p=>`<li>${escapeHTML(p.name)}</li>`).join('')}</ul>`:''}`,button('Cancel','close','','data-action="close-modal"')+button(keep?'Archive':'Delete','trash','danger',`data-action="robot-confirm-delete" data-id="${id}"`));
}
function deleteRobot(id){
  const robot=robotById(id),refs=robotReferences(id);
  if(refs.length||robot.versions.some(v=>v.succeeded+v.failed+v.cancelled)){robot.archived=true;refs.forEach(p=>p.enabled=false);}
  else robots.splice(robots.indexOf(robot),1);
  modalRoot.innerHTML='';render();
}
function renderSkillsPage(){
  const toolTab=state.skillsTab==='tools';
  const tabs=`<div class="review-tabs"><button data-action="skill-tab" data-id="skills" class="${toolTab?'':'active'}">Skills</button><button data-action="skill-tab" data-id="tools" class="${toolTab?'active':''}">Tools</button></div>`;
  if(!toolTab)return skillsCatalogPage().replace('<div class="card table-card">',tabs+'<div class="card table-card">');
  return `<div class="page-heading"><div class="heading-copy"><h1>Skills</h1></div><div class="heading-actions">${resourcePageActions('tool')}</div></div>`+tabs+table(['Tool','Type','Status','Actions'],tools.filter(t=>!!t.archived===archivedResources.tool).map(t=>`<tr><td><strong>${escapeHTML(t.name)}</strong><small class="cell-note">${escapeHTML(t.desc)}</small></td><td>${escapeHTML(t.icon)}</td><td>${t.archived?'Archived':t.status==='warning'?'Needs attention':'Enabled'}</td><td>${resourceControls('tool',t)}</td></tr>`).join(''));
}
function robotNodeDialog(robotId,nodeId='',position=null){
  const robot=robotById(robotId),node=builderNodes().find(n=>n.id===nodeId);if(!robot||robot.archived)return;
  robotPosition=position;
  showDialog(node?'Edit Robot node':'Add Robot node',`<form id="robot-node-form" data-robot="${robotId}" data-node="${nodeId}"><strong>${escapeHTML(robot.name)}</strong><label class="form-field"><span>Version</span><select class="input" name="version">${[...robot.versions].reverse().map(v=>`<option value="${v.number}" ${(node?.robotVersion??activeRobotVersion(robot).number)===v.number?'selected':''}>v${v.number}</option>`).join('')}</select></label><label class="form-field"><span>Agent</span><select class="input" name="agentId" required><option value="">Select Agent</option>${projectAgents(projectById(state.project)).filter(a=>!a.archived).map(a=>`<option value="${a.id}" ${node?.agentId===a.id?'selected':''}>${escapeHTML(a.name)}</option>`).join('')}</select></label><label class="form-field"><span>PC</span><select class="input" name="pc" required><option value="">Select PC</option>${pcs.filter(pc=>!pc.removed&&!pc.disabled||pc.name===node?.pc).map(pc=>`<option value="${escapeHTML(pc.name)}" ${node?.pc===pc.name?'selected':''} ${pc.disabled||pc.removed?'disabled':''}>${escapeHTML(pc.label)}${pc.status==='offline'?' (Offline)':''}</option>`).join('')}</select></label><label class="form-field"><span>Input · JSON</span><textarea class="textarea" name="input" required>${escapeHTML(node?JSON.stringify(node.robotInput,null,2):'{}')}</textarea></label><p class="form-error" id="robot-node-error" role="alert"></p><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">Save node</button></div></form>`);
}
function saveRobotNode(form){
  const p=currentProcess(),robot=robotById(form.dataset.robot),data=new FormData(form),agent=agents.find(a=>a.id===data.get('agentId')&&!a.archived),pc=pcs.find(pc=>pc.name===data.get('pc')&&!pc.disabled&&!pc.removed),version=robotVersion(robot,data.get('version'));
  const fail=msg=>document.getElementById('robot-node-error').textContent=msg;
  if(!agent||!pc||!version||robot.archived)return fail('Chọn Version, Agent và PC hợp lệ.');
  if(!projectAgents(projectById(p.project)).some(a=>a.id===agent.id))return fail('Chọn Agent thuộc Team của Project.');
  let input;try{input=JSON.parse(data.get('input'));}catch{return fail('Input phải là JSON hợp lệ.');}
  if(p.version&&!processDrafts[p.id])processDrafts[p.id]=structuredClone(graphs[p.id]);
  const nodes=builderNodes(),old=nodes.find(n=>n.id===form.dataset.node);
  const node={id:old?.id||'robot-node-'+robotSequence++,kind:'robot',robotId:robot.id,robotVersion:version.number,robotEntry:version.entry,title:robot.name,agentId:agent.id,agent:agent.name,agentModel:agent.model,skill:'',skillId:null,toolIds:[],tools:'',pc:pc.name,robotInput:input,instructions:'',timeout:settings.taskTimeout+' phút',x:old?.x??robotPosition?.x??40+nodes.length*260,y:old?.y??robotPosition?.y??110};
  if(old)nodes[nodes.indexOf(old)]=node;else nodes.push(node);
  state.selectedNode=node.id;modalRoot.innerHTML='';render();
}
function publishProcessDraft(id){
  const p=processById(id),nodes=processDrafts[id]||graphs[id];
  if(p.archived||projectById(p.project).archived||!nodes.length)return;
  if(nodes.some(n=>!agents.some(a=>a.id===n.agentId&&!a.archived)||n.robotId&&(!robotById(n.robotId)||robotById(n.robotId).archived||!robotVersion(robotById(n.robotId),n.robotVersion)||!pcs.some(pc=>pc.name===n.pc&&!pc.disabled&&!pc.removed)))){showToast('Kiểm tra Agent, Robot và PC trước khi Publish.');return;}
  p.version++;graphs[id]=structuredClone(nodes);p.tasks=nodes.length;
  processVersions[id]??={};processVersions[id][p.version]=structuredClone(nodes);delete processDrafts[id];
  if(!p.scheduleVersion)p.scheduleVersion=p.version;
  render();showToast('Đã Publish v'+p.version+'. Lịch hiện tại giữ nguyên version.');
}
function robotBuilderPage(){
  const p=currentProcess(),nodes=builderNodes(),selected=nodes.find(n=>n.id===state.selectedNode)||nodes[0],draft=!!processDrafts[p.id]||!p.version,width=Math.max(1000,...nodes.map(n=>n.x+300));
  const inspector=selected.kind==='robot'?`<p class="panel-label">Robot node</p><h2>${escapeHTML(selected.title)}</h2><dl class="pc-specs"><div><dt>Version</dt><dd>v${selected.robotVersion}</dd></div><div><dt>Agent</dt><dd>${escapeHTML(selected.agent)}</dd></div><div><dt>PC</dt><dd>${escapeHTML(pcDisplay(selected.pc))}</dd></div></dl><label class="form-field"><span>Input</span><textarea class="textarea" readonly>${escapeHTML(JSON.stringify(selected.robotInput,null,2))}</textarea></label>${button('Edit node','file','',`data-action="robot-node-edit" data-id="${selected.id}"`)}`:`<p class="panel-label">Agent task</p><h2>${escapeHTML(selected.title)}</h2><div class="form-field"><span>Agent</span><strong>${escapeHTML(selected.agent)}</strong></div><div class="form-field"><span>Skill</span><p>${escapeHTML(selected.skill)}</p></div><div class="form-field"><span>Tools</span><p>${escapeHTML(selected.tools)}</p></div>`;
  return `<div class="builder-toolbar"><div class="builder-title"><button class="back-button" ${projectLink(p.project)} aria-label="Back to Project">${icon('back')}</button><div><h1>${escapeHTML(p.name)}</h1><p>${draft?'Draft v'+(p.version+1):'Published v'+p.version}</p></div></div><div class="builder-actions">${draft?button('Publish','upload','primary small',`data-action="publish-process" data-id="${p.id}"`):''}${button('Schedule','clock','small',`data-action="schedule" data-id="${p.id}" ${!p.version?'disabled':''}`)}${button('Run','play-circle','small',`data-action="run-now" data-id="${p.id}" ${!p.version?'disabled':''}`)}</div></div><div class="review-builder robot-builder"><aside class="robot-palette"><h2>Robots</h2>${robots.filter(r=>!r.archived).map(r=>`<button class="robot-source" draggable="true" data-robot="${r.id}" data-action="robot-node-add" data-id="${r.id}">${icon('process')}<span>${escapeHTML(r.name)}<small>v${activeRobotVersion(r).number}</small></span></button>`).join('')}</aside><section class="canvas" aria-label="Process canvas"><div class="canvas-toolbar"><button type="button" data-action="zoom-out" aria-label="Zoom out">${icon('zoomout')}</button><button type="button" data-action="zoom-in" aria-label="Zoom in">${icon('zoomin')}</button><button type="button" data-action="zoom-reset" aria-label="Reset zoom">${icon('fit')}</button></div><div class="graph-surface" style="width:${width*state.zoom}px;height:${600*state.zoom}px"><div class="review-flow" style="width:${width}px;transform:scale(${state.zoom})"><svg class="review-edges" aria-hidden="true"></svg>${nodes.map((n,i)=>`<button class="review-node ${n.id===selected.id?'selected':''}" data-node="${n.id}" style="left:${n.x}px;top:${n.y}px"><span class="node-step">${n.kind==='robot'?'ROBOT · v'+n.robotVersion:'TASK '+(i+1)}</span><strong>${escapeHTML(n.title)}</strong><span class="node-agent">${escapeHTML(n.agent)}</span><span class="node-skill">${escapeHTML(n.kind==='robot'?pcDisplay(n.pc):n.skill)}</span><span class="node-in"></span><span class="node-out"></span></button>`).join('')}</div></div></section><aside class="review-inspector">${inspector}</aside></div>`;
}
