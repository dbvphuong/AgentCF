// Agent permissions for the prototype, separate from future account/user permissions.
const rolePermissions=[
  {id:'project.read',label:'View project'},
  {id:'skill.use',label:'Use skills'},
  {id:'tool.use',label:'Use tools'},
  {id:'robot.run',label:'Run robot'},
  {id:'output.review',label:'Review output'},
  {id:'project.manage',label:'Manage project'}
];
const roles=[
  {id:'role-pm',name:'PM',duties:'Quản lý mục tiêu, tiến độ và báo cáo dự án.',permissions:[]},
  {id:'role-employee',name:'Nhân viên',duties:'Thực hiện công việc được giao và chịu trách nhiệm output.',permissions:[]}
];
let showArchivedRoles=false;
const roleById=id=>roles.find(r=>r.id===id);
const agentsWithRole=id=>agents.filter(a=>a.roleId===id);
function initializeRoles(){
  agents.forEach(agent=>{agent.roleId=agent.role==='Project Manager'?'role-pm':'role-employee';agent.role=roleById(agent.roleId).name;});
}
// Assignment of a Project PM is independent of future Role authorization.
function canAssignProjectPM(agent){return !!agent&&!agent.archived;}
function roleSelect(agent){
  return `<label class="form-field"><span>Role</span><select class="input" name="roleId" required><option value="">Select role</option>${roles.filter(role=>!role.archived||role.id===agent?.roleId).map(role=>`<option value="${role.id}" ${role.id===agent?.roleId?'selected':''}>${escapeHTML(role.name)}${role.archived?' (Archived)':''}</option>`).join('')}</select></label>`;
}
function rolesSettingsPage(){
  return `<div class="settings-toolbar role-toolbar">${button('New role','plus','primary','data-action="role-new"')}${button(showArchivedRoles?'Active':'Archived','history','','data-action="role-archived"')}</div>`+table(['Role','Duties','Agents','Actions'],roles.filter(role=>!!role.archived===showArchivedRoles).map(role=>`<tr><td><strong>${escapeHTML(role.name)}</strong></td><td>${escapeHTML(role.duties||'—')}</td><td>${agentsWithRole(role.id).length}</td><td><div class="row-controls">${role.archived?button('Restore','refresh','small',`data-action="role-restore" data-id="${role.id}"`):button('Edit','file','small',`data-action="role-edit" data-id="${role.id}"`)+button('Delete','trash','small danger',`data-action="role-delete" data-id="${role.id}"`)}</div></td></tr>`).join(''));
}
function roleDialog(id=''){
  const role=roleById(id);
  showDialog(id?'Edit role':'New role',`<form id="role-form" data-id="${id}"><label class="form-field"><span>Name</span><input class="input" name="name" required maxlength="100" value="${escapeHTML(role?.name||'')}"></label><label class="form-field"><span>Duties</span><textarea class="textarea" name="duties" maxlength="1000">${escapeHTML(role?.duties||'')}</textarea></label><details><summary>Permissions ${settingsHelp('Chuẩn bị cho phân quyền sau này; chưa áp dụng trong prototype.')}</summary><fieldset class="resource-picker"><legend>Permissions</legend>${rolePermissions.map(permission=>`<label><input type="checkbox" name="permissions" value="${permission.id}" ${role?.permissions.includes(permission.id)?'checked':''}>${permission.label}</label>`).join('')}</fieldset></details><p class="form-error" id="role-error" role="alert"></p><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">Save</button></div></form>`);
}
function saveRole(form){
  const data=new FormData(form),id=form.dataset.id,name=data.get('name').trim(),permissions=[...new Set(data.getAll('permissions'))];
  if(!name||roles.some(role=>role.id!==id&&role.name.toLowerCase()===name.toLowerCase())){document.getElementById('role-error').textContent='Tên bắt buộc và không được trùng.';return;}
  if(permissions.some(p=>!rolePermissions.some(known=>known.id===p))){document.getElementById('role-error').textContent='Quyền không hợp lệ.';return;}
  const values={id,name,duties:String(data.get('duties')||'').trim(),permissions};
  applyRole(values);
}
function applyRole(values){
  if(!values)return;
  const existing=roleById(values.id);
  if(existing){Object.assign(existing,{name:values.name,duties:values.duties,permissions:values.permissions});agentsWithRole(existing.id).forEach(a=>a.role=existing.name);}
  else roles.push({id:'role-custom-'+entitySequence++,name:values.name,duties:values.duties,permissions:values.permissions});
  modalRoot.innerHTML='';render();showToast('Đã lưu Role.');
}
function roleDeleteDialog(id){
  const role=roleById(id),assigned=agentsWithRole(id);
  showDialog(assigned.length?'Archive role?':'Delete role?',`<p><strong>${escapeHTML(role.name)}</strong></p>${assigned.length?`<p>${assigned.length} Agent đang dùng. Archive giữ liên kết hiện tại, không cho gán Role này cho Agent mới.</p><ul class="resource-usage">${assigned.map(a=>`<li>${escapeHTML(a.name)}</li>`).join('')}</ul>`:'<p>Xóa Role chưa được sử dụng?</p>'}`,button('Cancel','close','','data-action="close-modal"')+button(assigned.length?'Archive':'Delete','trash','danger',`data-action="role-confirm-delete" data-id="${id}"`));
}
function deleteRole(id){
  const role=roleById(id);if(!role)return;
  if(agentsWithRole(id).length)role.archived=true;else roles.splice(roles.indexOf(role),1);
  modalRoot.innerHTML='';render();
}
