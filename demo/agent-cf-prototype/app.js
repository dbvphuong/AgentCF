const iconPaths = {
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  folder: '<path d="M3 6.5A2.5 2.5 0 0 1 5.5 4H9l2 2h7.5A2.5 2.5 0 0 1 21 8.5v8A3.5 3.5 0 0 1 17.5 20h-11A3.5 3.5 0 0 1 3 16.5z"/>',
  process: '<circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="5" r="2.5"/><circle cx="19" cy="19" r="2.5"/><path d="M7.5 11c4-1 5-4 9-5M7.5 13c4 1 5 4 9 5"/>',
  'play-circle': '<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4z"/>',
  agent: '<path d="M12 3v3M8 6h8a4 4 0 0 1 4 4v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-6a4 4 0 0 1 4-4Z"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><path d="M9 16h6"/>',
  monitor: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
  tool: '<path d="M14.7 6.3a4 4 0 0 0-5-5L12 3.6 9.6 6 7.3 3.7a4 4 0 0 0 5 5L20 16.4a2.5 2.5 0 0 1-3.6 3.6l-7.7-7.7"/>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/>',
  chevrons: '<path d="m8 9 4-4 4 4M16 15l-4 4-4-4"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.8 9a2.4 2.4 0 1 1 3.4 2.2c-.9.4-1.2.9-1.2 1.8M12 17h.01"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  arrow: '<path d="M5 12h14M14 7l5 5-5 5"/>',
  trend: '<path d="m4 16 5-5 4 4 7-8M15 7h5v5"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  cpu: '<rect x="7" y="7" width="10" height="10" rx="2"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3M10 10h4v4h-4z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  zap: '<path d="m13 2-9 12h8l-1 8 9-12h-8z"/>',
  grid: '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
  back: '<path d="m15 18-6-6 6-6"/>',
  save: '<path d="M5 3h12l3 3v15H4V4a1 1 0 0 1 1-1Z"/><path d="M8 3v6h8V3M8 21v-7h8v7"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5M5 20h14"/>',
  zoomin: '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5M10 7v6M7 10h6"/>',
  zoomout: '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5M7 10h6"/>',
  fit: '<path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/>',
  filter: '<path d="M4 5h16l-6 7v6l-4 2v-8z"/>',
  terminal: '<path d="m5 7 4 4-4 4M11 17h8"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  code: '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 4l-4 16"/>',
  shield: '<path d="M12 3 4 6v5c0 5 3.4 8.3 8 10 4.6-1.7 8-5 8-10V6z"/><path d="m9 12 2 2 4-5"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
  refresh: '<path d="M20 6v5h-5M4 18v-5h5M6.1 9a7 7 0 0 1 11.7-2.6L20 11M4 13l2.2 4.6A7 7 0 0 0 18 15"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  eye: '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.5"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6"/>',
  laptop: '<rect x="4" y="4" width="16" height="12" rx="2"/><path d="M2 20h20M9 20h6"/>',
  branch: '<circle cx="6" cy="5" r="2"/><circle cx="18" cy="7" r="2"/><circle cx="6" cy="19" r="2"/><path d="M6 7v10M8 9c0-1 1-2 3-2h5"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
  file: '<path d="M6 2h8l4 4v16H6z"/><path d="M14 2v5h5M9 13h6M9 17h5"/>',
};

const icon = (name, label = '') => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" ${label ? `aria-label="${label}"` : 'aria-hidden="true"'}>${iconPaths[name] || iconPaths.dashboard}</svg>`;

// Review data stays in memory. Refresh restores the sample company.
const state = { route: 'dashboard', project: 'market', process: 'brief', tab: 'processes', runFilter: 'all', selectedNode: 'research', zoom: 1 };
const projects = [
  { id: 'market', name: 'Market Research', desc: 'Theo dõi thị trường và đối thủ để đưa ra quyết định.', pm: 'Research PM', target: '4 báo cáo được duyệt / tháng', done: 3, total: 4, health: 'warning' },
  { id: 'content', name: 'Content Operations', desc: 'Nghiên cứu, biên tập và xuất bản nội dung.', pm: 'Content PM', target: '12 bài viết được duyệt / tháng', done: 8, total: 12, health: 'active' },
  { id: 'customer', name: 'Customer Intelligence', desc: 'Tổng hợp phản hồi và phát hiện insight khách hàng.', pm: 'Research PM', target: '4 bản tổng hợp / tháng', done: 2, total: 4, health: 'active' },
  { id: 'internal', name: 'Internal Automation', desc: 'Chuẩn hóa dữ liệu và hỗ trợ vận hành nội bộ.', pm: 'Operations PM', target: '20 lần đồng bộ thành công / tuần', done: 16, total: 20, health: 'active' }
];
const processes = [
  { id: 'brief', project: 'market', name: 'Weekly Market Brief', version: 4, enabled: true, frequency: 'weekly', day: '5', time: '16:00', pc: 'PHUONG-PC', tasks: 5 },
  { id: 'watch', project: 'market', name: 'Competitor Watch', version: 2, enabled: false, frequency: 'daily', day: '1', time: '08:00', pc: 'Auto', tasks: 4 },
  { id: 'pricing', project: 'market', name: 'Pricing Signal Scan', version: 3, enabled: false, frequency: 'daily', day: '1', time: '09:00', pc: 'Auto', tasks: 3 },
  { id: 'blog', project: 'content', name: 'Blog Production', version: 7, enabled: true, frequency: 'daily', day: '1', time: '09:00', pc: 'DESIGN-02', tasks: 5 },
  { id: 'social', project: 'content', name: 'Social Repurpose', version: 3, enabled: false, frequency: 'weekly', day: '1', time: '10:00', pc: 'Auto', tasks: 3 },
  { id: 'quality', project: 'content', name: 'Content Quality Review', version: 2, enabled: false, frequency: 'manual', day: '1', time: '10:00', pc: 'Auto', tasks: 3 },
  { id: 'feedback', project: 'customer', name: 'Customer Feedback Digest', version: 3, enabled: false, frequency: 'weekly', day: '1', time: '09:00', pc: 'Auto', tasks: 3 },
  { id: 'sync', project: 'internal', name: 'Daily Data Sync', version: 6, enabled: true, frequency: 'daily', day: '1', time: '23:00', pc: 'OPS-LAPTOP', tasks: 3 }
];
const pcs = [
  { name: 'PHUONG-PC', os: 'Windows 11', status: 'busy', heartbeat: 'Vừa xong', cpu: 42 },
  { name: 'DESIGN-02', os: 'Windows 11', status: 'busy', heartbeat: '5 giây trước', cpu: 28 },
  { name: 'OPS-LAPTOP', os: 'macOS', status: 'online', heartbeat: '8 giây trước', cpu: 8 },
  { name: 'RESEARCH-01', os: 'Ubuntu', status: 'offline', heartbeat: '2 giờ trước', cpu: 0 }
];
pcs.forEach((pc,i)=>Object.assign(pc,{id:'pc-'+(i+1),label:pc.name,disabled:false,removed:false,ramUsed:[9.6,7.5,5.1,0][i],ramTotal:[16,16,16,32][i],cores:[12,8,8,16][i],threads:[20,16,8,32][i],ghz:[3.6,3.4,3.2,3.5][i],clientVersion:'0.4.2',toolIds:['tool-1','tool-2','tool-3','tool-4']}));
const skills = [
  { id: 'research', name: 'Market research', desc: 'Tìm nguồn, đối chiếu và trích dẫn thông tin.', output: 'Bộ nguồn có dẫn chứng', tools: 'Web Search, Browser', version: 'v2' },
  { id: 'analysis', name: 'Insight analysis', desc: 'Tách dữ kiện, so sánh và đánh giá mức tin cậy.', output: 'Insight kèm bằng chứng', tools: 'Python, Local Files', version: 'v1' },
  { id: 'writing', name: 'Report writing', desc: 'Viết báo cáo theo cấu trúc và mẫu đã quy định.', output: 'Báo cáo có cấu trúc', tools: 'Local Files', version: 'v3' },
  { id: 'review', name: 'Quality review', desc: 'Kiểm chứng nội dung theo checklist chất lượng.', output: 'Đạt / cần sửa và lý do', tools: 'Browser, Local Files', version: 'v2' },
  { id: 'publish', name: 'Report delivery', desc: 'Lưu kết quả đã duyệt vào đúng thư mục.', output: 'File và đường dẫn kết quả', tools: 'Local Files', version: 'v1' }
];
const agents = [
  { name: 'Research PM', role: 'Project Manager', model: 'Model chất lượng cao', skills: ['Quality review'], tokens: 182000, quality: 97 },
  { name: 'Researcher', role: 'Nghiên cứu', model: 'Model cân bằng', skills: ['Market research'], tokens: 420000, quality: 95 },
  { name: 'Data Analyst', role: 'Phân tích', model: 'Model cân bằng', skills: ['Insight analysis'], tokens: 265000, quality: 94 },
  { name: 'Content Writer', role: 'Biên soạn', model: 'Model cân bằng', skills: ['Report writing'], tokens: 610000, quality: 96 },
  { name: 'Quality Reviewer', role: 'Kiểm tra chất lượng', model: 'Model chất lượng cao', skills: ['Quality review'], tokens: 198000, quality: 98 },
  { name: 'Publisher', role: 'Xuất kết quả', model: 'Model tiết kiệm', skills: ['Report delivery'], tokens: 48000, quality: 99 },
  { name: 'Content PM', role: 'Project Manager', model: 'Model chất lượng cao', skills: ['Quality review'], tokens: 156000, quality: 96 },
  { name: 'Operations PM', role: 'Project Manager', model: 'Model cân bằng', skills: ['Quality review'], tokens: 72000, quality: 95 }
];
const tools = [
  { name: 'Web Search', desc: 'Tìm nguồn trên internet.', status: 'active', icon: 'globe' },
  { name: 'Browser', desc: 'Đọc và kiểm chứng nội dung trang web.', status: 'active', icon: 'eye' },
  { name: 'Local Files', desc: 'Đọc, ghi trong thư mục được cấp quyền.', status: 'active', icon: 'folder' },
  { name: 'Python', desc: 'Phân tích dữ liệu bằng script.', status: 'active', icon: 'code' },
  { name: 'CMS', desc: 'Kết nối xuất bản cần được kiểm tra lại.', status: 'warning', icon: 'upload' }
];
const settings = { tab:'providers', taskTimeout:10, logPageSize:25 };
const providers = [{id:'provider-demo',name:'LLM Gateway',type:'compatible',baseUrl:'',timeout:60,enabled:true}];
const models = [
  {id:'model-economy',name:'Model tiết kiệm',apiId:'demo-economy',provider:'provider-demo',maxTokens:2048,temperature:0.2,enabled:true},
  {id:'model-balanced',name:'Model cân bằng',apiId:'demo-balanced',provider:'provider-demo',maxTokens:4096,temperature:0.3,enabled:true},
  {id:'model-advanced',name:'Model chất lượng cao',apiId:'demo-advanced',provider:'provider-demo',maxTokens:8192,temperature:0.2,enabled:true}
];
agents.forEach(a=>a.modelId=models.find(m=>m.name===a.model)?.id);
// Catalog IDs stay stable when display names change. Published graph labels are snapshots.
agents.forEach((a,i)=>{a.id='agent-'+(i+1);a.originalName=a.name;a.instructions='Thực hiện công việc theo vai trò và Skill được giao.';a.toolIds=[];});
tools.forEach((t,i)=>{t.id='tool-'+(i+1);t.originalName=t.name;});
skills.forEach(s=>{s.originalName=s.name;s.instructions=s.desc;s.toolIds=tools.filter(t=>s.tools.split(', ').includes(t.name)).map(t=>t.id);});
agents.forEach(a=>{a.skillIds=skills.filter(s=>a.skills.includes(s.name)).map(s=>s.id);a.toolIds=[...new Set(a.skillIds.flatMap(id=>skills.find(s=>s.id===id).toolIds))];});
function graphFor(p) {
  const steps = [
    ['research', 'Collect sources', 'Researcher', 'Market research', 'Web Search, Browser'],
    ['analyze', 'Analyze insights', 'Data Analyst', 'Insight analysis', 'Python, Local Files'],
    ['write', 'Write report', 'Content Writer', 'Report writing', 'Local Files'],
    ['review', 'Quality review', 'Quality Reviewer', 'Quality review', 'Browser, Local Files'],
    ['publish', 'Save report', 'Publisher', 'Report delivery', 'Local Files']
  ];
  return steps.slice(0, p.tasks).map((v, i) => {
    const agent=agents.find(a=>a.originalName===v[2]),skill=skills.find(s=>s.originalName===v[3]),nodeTools=tools.filter(t=>v[4].split(', ').includes(t.originalName));
    return { id:v[0],title:v[1],agent:agent?.name||v[2],agentId:agent?.id,skill:skill?.name||v[3],skillId:skill?.id,skillVersion:skill?.version,skillInstructions:skill?.instructions,expectedOutput:skill?.output,agentModel:agent?.model,agentInstructions:agent?.instructions,tools:nodeTools.map(t=>t.name).join(', '),toolIds:nodeTools.map(t=>t.id),x:40+i*260,y:110+(i%2)*90,instructions:'Thực hiện theo skill và trả output đúng tiêu chuẩn.',timeout:settings.taskTimeout+' phút' };
  });
}
const graphs = Object.fromEntries(processes.map(p => [p.id, graphFor(p)]));
const runs = [
  { id: 'R-1084', process: 'brief', status: 'running', progress: 60, pc: 'PHUONG-PC', source: 'Manual', started: '13/11 · 14:02', version: 4, logs: ['Run được tạo từ v4.', 'Researcher hoàn thành Collect sources.', 'Data Analyst hoàn thành Analyze insights.', 'Content Writer đang viết báo cáo.'] },
  { id: 'R-1083', process: 'blog', status: 'running', progress: 40, pc: 'DESIGN-02', source: 'Schedule', started: '13/11 · 09:00', version: 7, logs: ['Schedule tạo run từ v7.', 'Researcher hoàn thành Collect sources.', 'Data Analyst đang phân tích.'] },
  { id: 'R-1082', process: 'feedback', status: 'succeeded', progress: 100, pc: 'OPS-LAPTOP', source: 'Manual', started: '12/11 · 10:00', version: 3, logs: ['Mọi task đã hoàn thành.', 'Output đã được lưu.'] },
  { id: 'R-1081', process: 'watch', status: 'failed', progress: 25, pc: 'PHUONG-PC', source: 'Manual', started: '12/11 · 08:00', version: 2, logs: ['Researcher đã hoàn thành Collect sources.', 'Data Analyst: task thất bại do timeout. Các task phụ thuộc bị bỏ qua.'] }
];
let nextRunId = 1085;
// Sample timestamps for reviewing the Runs table, not execution telemetry.
[
  ['2026-11-13T14:02:00+07:00',null],
  ['2026-11-13T09:00:00+07:00',null],
  ['2026-11-12T10:00:00+07:00','2026-11-12T10:04:32+07:00'],
  ['2026-11-12T08:00:00+07:00','2026-11-12T08:02:15+07:00']
].forEach(([startedAt,endedAt],i)=>Object.assign(runs[i],{startedAt,endedAt}));
const app = document.getElementById('app');
const modalRoot = document.getElementById('modalRoot');
const titles = { dashboard: 'Overview', projects: 'Projects', project: 'Project', builder: 'Process', agents: 'Agents', skills: 'Skills', tools: 'Robots', runs: 'Runs', runners: 'PC', settings: 'Settings' };
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const formatTokens=n=>new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:2}).format(n);
const projectById = id => projects.find(p => p.id === id);
const processById = id => processes.find(p => p.id === id);
const currentProcess = () => processById(state.process);
function button(label, name, classes = '', attrs = '') { return `<button type="button" class="button ${classes}" ${attrs}>${icon(name)}<span>${label}</span></button>`; }
function badge(status) {
  const names = { running: 'Running', cancelling: 'Cancelling', cancelled: 'Cancelled', succeeded: 'Succeeded', failed: 'Failed', active: 'On track', warning: 'Cần chú ý', online: 'Online', offline: 'Offline', busy: 'Busy', stopped: 'Stopped', enabled: 'Started' };
  return `<span class="badge ${status}">${names[status] || status}</span>`;
}
function heading(title, desc, actions = '') { return `<div class="page-heading"><div class="heading-copy"><h1>${escapeHTML(title)}</h1>${desc?`<p>${escapeHTML(desc)}</p>`:''}</div><div class="heading-actions">${actions}</div></div>`; }
function table(headers, rows) { return `<div class="card table-card"><table class="data-table"><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows || `<tr><td colspan="${headers.length}">Chưa có dữ liệu.</td></tr>`}</tbody></table></div>`; }
function metric(label, value, detail = '') { return `<div class="card summary-tile"><span>${label}</span><strong>${value}</strong><small>${detail}</small></div>`; }
function projectLink(id) { return `data-action="open-project" data-id="${id}"`; }
function scheduleText(p) { return p.frequency === 'manual' ? 'Manual' : `${p.frequency === 'daily' ? 'Hằng ngày' : ['Chủ nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'][Number(p.day)]} · ${p.time}`; }
// Preview dates use the user's timezone; they do not execute scheduled work.
function nextSchedule(p, now = new Date()) {
  if (!p.enabled || p.frequency === 'manual') return null;
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now).map(x => [x.type, x.value]));
  const candidate = new Date(`${parts.year}-${parts.month}-${parts.day}T${p.time}:00+07:00`);
  if (p.frequency === 'weekly') {
    const localDay = new Date(candidate.getTime() + 7 * 3600000).getUTCDay();
    candidate.setTime(candidate.getTime() + ((Number(p.day) - localDay + 7) % 7) * 86400000);
  }
  if (candidate <= now) candidate.setTime(candidate.getTime() + (p.frequency === 'weekly' ? 7 : 1) * 86400000);
  return candidate;
}
function nextLabel(p) { const next = nextSchedule(p); return next ? new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(next) : '—'; }
function dashboardPage(){return overviewPage();}
function projectsPage(){return projectListPage();}
function projectPage(){return projectDetailPage();}
function processTable(list){return compactProcessTable(list);}

const runListView = { project:'all', process:'all', query:'', from:runDateKey(Date.now()-6*86400000), to:runDateKey(Date.now()), page:1, pageSize:25 };
function runDateKey(value) { return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value)); }
function runTime(value) { return value ? new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(value)) : '—'; }
function runDuration(run, now=Date.now()) {
  if(!run.startedAt || (!run.endedAt&&!['running','cancelling'].includes(run.status)))return '—';
  const seconds=Math.max(0,Math.floor(((run.endedAt?Date.parse(run.endedAt):now)-Date.parse(run.startedAt))/1000));
  return `${Math.floor(seconds/3600)}:${String(Math.floor(seconds/60)%60).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;
}
function runTable(list, offset=0) {
  return table(['STT','Run / Process','Project','Status','Progress','Started','Ended','Duration','Actions'],list.map((r,index)=>{
    const p = processById(r.process);
    const nodes=runTaskStates(r), done=nodes.filter(n=>n.status==='succeeded').length, current=nodes.find(n=>['running','cancelling','failed','cancelled'].includes(n.status));
    const progressTitle=current?`${current.title} · ${current.agent}`:r.status==='succeeded'?'Completed':'—';
    return `<tr><td>${offset+index+1}</td><td><button class="entity-link" data-action="open-run" data-id="${r.id}">${escapeHTML(p.name)}</button><small class="cell-note">${r.id} · v${r.version} · ${r.source}</small></td><td><button class="text-button" ${projectLink(p.project)}>${escapeHTML(projectById(p.project).name)}</button></td><td>${badge(r.status)}</td><td><span tabindex="0" title="${escapeHTML(progressTitle)}">${done}/${nodes.length} node</span></td><td class="run-timestamp">${runTime(r.startedAt)}</td><td class="run-timestamp">${runTime(r.endedAt)}</td><td class="run-duration" data-run-duration="${r.id}">${runDuration(r)}</td><td><div class="row-controls">${button('Details','eye','small',`data-action="open-run" data-id="${r.id}"`)}${r.status==='running'?button('Cancel run','close','small danger',`data-action="cancel-run" data-id="${r.id}"`):''}</div></td></tr>`;
  }).join('')).replace('table-card','table-card runs-table');
}
function filteredRuns() {
  const v=runListView;
  return runs.filter(r=>{
    const p=processById(r.process), day=r.startedAt?runDateKey(r.startedAt):'';
    return (v.project==='all'||p.project===v.project)&&(v.process==='all'||r.process===v.process)&&
      (state.runFilter==='all'||(state.runFilter==='running'?['running','cancelling'].includes(r.status):r.status===state.runFilter))&&
      r.id.toLowerCase().includes(v.query.trim().toLowerCase())&&(!v.from||day>=v.from)&&(!v.to||day<=v.to);
  }).sort((a,b)=>Date.parse(b.startedAt)-Date.parse(a.startedAt)||b.id.localeCompare(a.id));
}
function runsPage() {
  const v=runListView, list=filteredRuns(), pages=Math.max(1,Math.ceil(list.length/v.pageSize));
  v.page=Math.min(Math.max(1,v.page),pages);
  const offset=(v.page-1)*v.pageSize, shown=list.slice(offset,offset+v.pageSize);
  const options=(items,selected)=>items.map(x=>`<option value="${x.id}" ${selected===x.id?'selected':''}>${escapeHTML(x.name)}</option>`).join('');
  return heading('Runs','')+`<div class="runs-filters">
    <label>Run ID<input id="run-search" class="input" type="search" placeholder="R-1084" value="${escapeHTML(v.query)}"></label>
    <label>Project<select id="run-project-filter" class="select"><option value="all">All projects</option>${options(projects,v.project)}</select></label>
    <label>Process<select id="run-process-filter" class="select"><option value="all">All processes</option>${options(processes.filter(p=>v.project==='all'||p.project===v.project),v.process)}</select></label>
    <label>Status<select class="select" id="run-status-filter">${[['all','All statuses'],['running','Running'],['succeeded','Succeeded'],['failed','Failed'],['cancelled','Cancelled']].map(([id,label])=>`<option value="${id}" ${state.runFilter===id?'selected':''}>${label}</option>`).join('')}</select></label>
    <label>Started · From<input class="input" id="run-from" type="date" value="${v.from}" ${v.to?`max="${v.to}"`:''}></label>
    <label>To<input class="input" id="run-to" type="date" value="${v.to}" ${v.from?`min="${v.from}"`:''}></label>
    ${button('Reset','refresh','small','data-action="runs-reset"')}</div>
    ${v.from&&v.to&&v.from>v.to?'<p class="runs-date-error" role="alert">Ngày kết thúc phải từ ngày bắt đầu trở đi.</p>':''}
    ${runTable(shown,offset)}<div class="log-pagination runs-pagination" aria-live="polite"><span>${list.length?offset+1:0}–${offset+shown.length} · Total <strong>${list.length}</strong>${list.length!==runs.length?` / ${runs.length} runs`: ' runs'}</span><div><label>Rows <select class="select" id="runs-page-size">${[25,50,100].map(n=>`<option ${n===v.pageSize?'selected':''}>${n}</option>`).join('')}</select></label>${button('Previous','back','small',`data-action="runs-page" data-id="${v.page-1}" ${v.page===1?'disabled':''}`)}<span>Page ${v.page} / ${pages}</span>${button('Next','arrow','small',`data-action="runs-page" data-id="${v.page+1}" ${v.page===pages?'disabled':''}`)}</div></div>`;
}
setInterval(()=>document.querySelectorAll('[data-run-duration]').forEach(el=>{const run=runs.find(r=>r.id===el.dataset.runDuration);if(run)el.textContent=runDuration(run);}),1000);
const resourceLists={agent:agents,skill:skills,tool:tools};
const resourceRoutes={agent:'agents',skill:'skills',tool:'skills'};
const archivedResources={agent:false,skill:false,tool:false};
const resourceNames=(type,ids=[])=>ids.map(id=>resourceLists[type].find(r=>r.id===id)?.name||id).join(', ');
function resourcePageActions(type){return button('New '+type,'plus','primary',`data-action="new-resource" data-type="${type}"`)+button(archivedResources[type]?'Active':'Archived','history','',`data-action="resource-archive-view" data-type="${type}"`);}
function resourceControls(type,item){return `<div class="row-controls">${item.archived?button('Restore','refresh','small',`data-action="restore-resource" data-type="${type}" data-id="${item.id}"`):button('Edit','file','small',`data-action="edit-resource" data-type="${type}" data-id="${item.id}"`)+button('Delete','trash','small danger',`data-action="delete-resource" data-type="${type}" data-id="${item.id}"`)}</div>`;}
function agentTable(list) { return table(['Agent','Role / Model','Skills','Quality','Tokens','Actions'],list.map(a=>`<tr><td><strong>${escapeHTML(a.name)}</strong>${a.archived?'<small class="cell-note">Archived</small>':''}</td><td>${escapeHTML(a.role)}<small class="cell-note">${escapeHTML(a.model)}</small></td><td>${escapeHTML(resourceNames('skill',a.skillIds))||'—'}</td><td>${a.quality===null?'Chưa có dữ liệu':a.quality+'% đạt'}</td><td>${formatTokens(a.tokens)}</td><td>${resourceControls('agent',a)}</td></tr>`).join('')); }
function agentsPage() { return heading('Agents','',resourcePageActions('agent')) + agentTable(agents.filter(a=>!!a.archived===archivedResources.agent)); }
function skillsCatalogPage() { return heading('Skills','Cách làm việc và tiêu chuẩn output. Agent được giao Task chịu trách nhiệm kết quả.',resourcePageActions('skill')) + table(['Skill','Version','Expected output','Tools','Agents sử dụng','Actions'],skills.filter(s=>!!s.archived===archivedResources.skill).map(s=>`<tr><td><strong>${escapeHTML(s.name)}</strong><small class="cell-note">${escapeHTML(s.desc)}</small></td><td>${s.version}</td><td>${escapeHTML(s.output)}</td><td>${escapeHTML(resourceNames('tool',s.toolIds))||'—'}</td><td>${escapeHTML(agents.filter(a=>a.skillIds.includes(s.id)).map(a=>a.name).join(', '))||'—'}</td><td>${resourceControls('skill',s)}</td></tr>`).join('')); }
function skillsPage(){return renderSkillsPage();}
function toolsPage(){return robotsPage();}
const pcById=id=>pcs.find(pc=>pc.id===id);
const pcRuns=pc=>runs.filter(r=>['running','cancelling'].includes(r.status)&&(runTaskStates(r).find(n=>['running','cancelling'].includes(n.status))?.pc||r.pc)===pc.name);
const pcDisplay=name=>pcs.find(pc=>pc.name===name)?.label||name;
const availablePc=pc=>!pc.removed&&!pc.disabled&&['online','busy'].includes(pc.status);
function pcOptions(selected,onlineOnly=false){
  return `<option value="Auto" ${selected==='Auto'?'selected':''}>Auto</option>`+pcs.filter(pc=>(!pc.removed&&(!onlineOnly||availablePc(pc)))||pc.name===selected).map(pc=>`<option value="${escapeHTML(pc.name)}" ${pc.name===selected?'selected':''} ${(pc.disabled||pc.removed||onlineOnly&&!availablePc(pc))?'disabled':''}>${escapeHTML(pc.label)}${pc.disabled?' (Disabled)':pc.removed?' (Removed)':pc.status==='offline'?' (Offline)':''}</option>`).join('');
}
function pcStatus(pc){return pc.removed?'Removed':pc.disabled?'Disabled':pc.status==='offline'?'Offline':pcRuns(pc).length?'Running':'Online';}
function pcStatusBadge(pc){
  const status=pcStatus(pc),active=pcRuns(pc);
  const detail=active.map(run=>{
    const node=runTaskStates(run).find(n=>['running','cancelling'].includes(n.status));
    return `${processById(run.process).name} · ${node?.title||'Đang điều phối'} · ${node?.agent||'—'}`;
  }).join('\n');
  return `<span class="badge ${status==='Running'?'running':status==='Online'?'active':status==='Offline'?'failed':'stopped'}${status==='Running'?' pc-metric pc-running-hint':''}" ${status==='Running'?`tabindex="0" data-tooltip="${escapeHTML(detail)}" aria-label="Running. ${escapeHTML(detail)}"`:''}>${status}</span>`;
}
function pcMetric(percent,detail){return `<span class="pc-metric" tabindex="0" data-tooltip="${escapeHTML(detail)}" aria-label="${percent}%. ${escapeHTML(detail)}">${percent}%</span>`;}
function pcPage(){
  return `<div class="page-heading"><div class="heading-copy"><h1>PC</h1></div><div class="heading-actions">${button('Connect PC','plus','primary','data-action="connect-pc"')}</div></div>`+table(['PC','Status','Current run','CPU','RAM','Last seen','Actions'],pcs.filter(pc=>!pc.removed).map(pc=>`<tr><td><button class="entity-link" data-action="pc-details" data-id="${pc.id}">${escapeHTML(pc.label)}</button><small class="cell-note">${escapeHTML(pc.os)}</small></td><td>${pcStatusBadge(pc)}</td><td>${pcRuns(pc).map(r=>`<button class="text-button" data-action="open-run" data-id="${r.id}">${escapeHTML(processById(r.process).name)}</button>`).join('<br>')||'—'}</td><td>${pc.status==='offline'?'—':pcMetric(pc.cpu,`${pc.cores} nhân · ${pc.threads} luồng · ${pc.ghz} GHz`)}</td><td>${pc.status==='offline'?'—':pcMetric(Math.round(pc.ramUsed/pc.ramTotal*100),`${pc.ramUsed} / ${pc.ramTotal} GB`)}</td><td>${escapeHTML(pc.heartbeat)}</td><td><div class="row-controls">${button('Edit','file','small',`data-action="pc-edit" data-id="${pc.id}"`)}${button(pc.disabled?'Enable':'Disable','shield','small',`data-action="pc-toggle" data-id="${pc.id}"`)}${button('Remove','trash','small danger',`data-action="pc-remove" data-id="${pc.id}"`)}</div></td></tr>`).join(''));
}
function pcDetails(id){
  const pc=pcById(id),active=pcRuns(pc),assigned=processes.filter(p=>p.pc===pc.name||graphs[p.id].some(n=>n.pc===pc.name)||(processDrafts[p.id]||[]).some(n=>n.pc===pc.name));
  showDialog(pc.label,`<div class="run-detail-head">${pcStatusBadge(pc)}<span>${escapeHTML(pc.os)} · Client ${pc.clientVersion}</span></div><dl class="pc-specs"><div><dt>CPU</dt><dd>${pc.cores} nhân · ${pc.threads} luồng · ${pc.ghz} GHz</dd></div><div><dt>RAM</dt><dd>${pc.status==='offline'?'—':pc.ramUsed} / ${pc.ramTotal} GB</dd></div><div><dt>Last seen</dt><dd>${escapeHTML(pc.heartbeat)}</dd></div></dl><h3>Current tasks</h3>${active.length?active.map(r=>{const node=runTaskStates(r).find(n=>['running','cancelling'].includes(n.status));return `<div class="pc-task"><button class="entity-link" data-action="open-run" data-id="${r.id}">${escapeHTML(processById(r.process).name)} · ${r.id}</button><small>${escapeHTML(node?.title||'Đang điều phối')} · ${escapeHTML(node?.agent||'—')}</small></div>`;}).join(''):'<p>—</p>'}<h3>Tools</h3><div class="chip-row">${pc.toolIds.map(id=>`<span class="chip">${escapeHTML(tools.find(t=>t.id===id)?.name||id)}</span>`).join('')}</div><h3>Assigned processes</h3>${assigned.length?`<ul>${assigned.map(p=>`<li>${escapeHTML(p.name)}${p.enabled?' · Scheduled':''}</li>`).join('')}</ul>`:'<p>—</p>'}`);
}
function editPc(id){
  const pc=pcById(id);
  showDialog('Edit PC',`<form id="pc-edit-form" data-id="${id}"><label class="form-field"><span>Name</span><input class="input" name="label" required maxlength="80" value="${escapeHTML(pc.label)}"></label><p class="form-error" id="pc-edit-error" role="alert"></p><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">Save</button></div></form>`);
}
function pcActionDialog(id,remove=false){
  const pc=pcById(id),assigned=processes.filter(p=>p.pc===pc.name||graphs[p.id].some(n=>n.pc===pc.name)||(processDrafts[p.id]||[]).some(n=>n.pc===pc.name)),active=pcRuns(pc);
  if(remove&&active.length){showDialog('PC đang chạy',`<p><strong>${escapeHTML(pc.label)}</strong> còn ${active.length} run hoạt động. Đợi hoàn tất hoặc hủy run trước khi Remove.</p>`,button('Open Runs','arrow','primary','data-action="close-and-runs"'));return;}
  if(!remove&&pc.disabled){pc.disabled=false;render();showToast('Đã Enable PC. Lịch vẫn tắt cho đến khi Start.');return;}
  showDialog(`${remove?'Remove':'Disable'} PC?`,`<p><strong>${escapeHTML(pc.label)}</strong> sẽ không nhận việc mới.${remove?' Cần ghép nối lại nếu muốn kết nối máy sau này.':' Run đang chạy vẫn tiếp tục.'}</p>${assigned.length?`<details open><summary>${assigned.length} process sử dụng PC này</summary><ul class="resource-usage">${assigned.map(p=>`<li>${escapeHTML(p.name)}${p.enabled?' · lịch sẽ tắt':''}</li>`).join('')}</ul></details>`:''}${remove?'<p>Lịch sử Runs và Logs được giữ lại.</p>':''}`,button('Cancel','close','','data-action="close-modal"')+button(remove?'Remove':'Disable',remove?'trash':'shield','danger',`data-action="pc-confirm" data-id="${id}" data-remove="${remove}"`));
}
function confirmPcAction(id,remove){
  const pc=pcById(id);if(remove&&pcRuns(pc).length)return pcActionDialog(id,true);
  pc.disabled=true;if(remove)pc.removed=true;
  processes.filter(p=>p.pc===pc.name||graphs[p.id].some(n=>n.pc===pc.name)||(processDrafts[p.id]||[]).some(n=>n.pc===pc.name)).forEach(p=>p.enabled=false);
  modalRoot.innerHTML='';render();showToast(remove?'Đã Remove PC; giữ lịch sử.':'Đã Disable. Run hiện tại vẫn tiếp tục.');
}
let pairingSequence=1000;
function connectPc(){
  const token='PC-'+(++pairingSequence);
  showDialog('Connect PC',`<div class="pc-connect"><button type="button" class="button" disabled title="Chưa có bộ cài trong prototype">Download client</button><div class="pc-pairing-code"><span>Pairing code · Demo</span><strong>${token}</strong><small>Hết hạn sau 10 phút · dùng một lần</small></div><label class="form-field"><span>Name</span><input class="input" id="pair-pc-name" maxlength="80" value="New PC"></label><p class="pc-pairing-status" role="status">Waiting for PC…</p><p id="pair-pc-error" class="form-error" role="alert"></p>${button('Simulate connection','play-circle','primary','data-action="pc-simulate"')}</div>`);
  modalRoot.querySelector('.pc-connect').dataset.expires=String(Date.now()+600000);
}
function simulatePcConnection(){
  const panel=modalRoot.querySelector('.pc-connect');if(!panel||panel.dataset.used)return;
  const label=panel.querySelector('#pair-pc-name').value.trim(),error=panel.querySelector('#pair-pc-error');
  if(Date.now()>Number(panel.dataset.expires)){error.textContent='Mã đã hết hạn. Tạo mã mới.';return;}
  if(!label||pcs.some(pc=>!pc.removed&&pc.label.toLowerCase()===label.toLowerCase())){error.textContent='Tên bắt buộc và không được trùng.';return;}
  panel.dataset.used='true';panel.querySelector('[data-action=pc-simulate]').disabled=true;panel.querySelector('.pc-pairing-status').textContent='Connecting…';
  setTimeout(()=>{
    if(!panel.isConnected)return;
    pcs.push({id:'pc-'+pairingSequence,name:'DEMO-PC-'+pairingSequence,label,os:'Windows 11',status:'online',heartbeat:'Vừa xong',cpu:8,ramUsed:4,ramTotal:16,cores:8,threads:16,ghz:3.2,clientVersion:'0.4.2',toolIds:tools.filter(t=>!t.archived).map(t=>t.id),disabled:false,removed:false});
    modalRoot.innerHTML='';render();showToast('PC connected · Demo');
  },600);
}
function settingsHelp(text) { return `<button type="button" class="field-help" aria-label="${escapeHTML(text)}" data-tooltip="${escapeHTML(text)}">?</button>`; }
function providerStatus(provider){
  if(!provider.enabled)return '<span class="badge stopped">Disabled</span>';
  if(!provider.baseUrl)return '<span class="badge stopped">Chưa cấu hình</span>';
  if(provider.testResult==='success')return '<span class="badge active" title="Kết quả giả lập, chưa kiểm tra API thật">Demo OK</span>';
  if(provider.testResult==='error')return '<span class="badge failed" title="Kết quả giả lập">Demo Error</span>';
  return '<span class="badge warning">Chưa kiểm tra</span>';
}
function settingsPage() {
  const tabs=[['providers','Providers & API'],['models','Models'],['roles','Roles'],['general','General']];
  let body='';
  if(settings.tab==='providers')body=`<div class="settings-toolbar">${button('Add provider','plus','primary','data-action="provider-edit"')}</div>${table(['Provider','API format','Base URL','Timeout','Status','Actions'],providers.map(p=>`<tr><td><strong>${escapeHTML(p.name)}</strong></td><td>${p.type==='compatible'?'OpenAI-compatible':p.type==='anthropic'?'Anthropic':'Custom'}</td><td><code>${escapeHTML(p.baseUrl)||'Chưa cấu hình'}</code></td><td>${p.timeout}s</td><td>${providerStatus(p)}</td><td>${button('Configure','settings','small',`data-action="provider-edit" data-id="${p.id}"`)}</td></tr>`).join(''))}`;
  else if(settings.tab==='models')body=`<div class="settings-toolbar">${button('Add model','plus','primary','data-action="model-edit"')}</div>${table(['Name','Model ID','Provider','Max output','Temperature','Status','Actions'],models.map(m=>`<tr><td><strong>${escapeHTML(m.name)}</strong><small class="cell-note">${agents.filter(a=>a.modelId===m.id).length} agents</small></td><td><code>${escapeHTML(m.apiId)}</code></td><td>${escapeHTML(providers.find(p=>p.id===m.provider)?.name||'—')}</td><td>${m.maxTokens}</td><td>${m.temperature}</td><td><span class="badge ${m.enabled?'active':'stopped'}">${m.enabled?'Enabled':'Disabled'}</span></td><td>${button('Edit','file','small',`data-action="model-edit" data-id="${m.id}"`)}</td></tr>`).join(''))}`;
  else if(settings.tab==='roles')body=rolesSettingsPage();
  else body=`<form id="general-settings-form" class="card settings-panel"><div class="form-row"><label class="form-field"><span>Task timeout · phút ${settingsHelp('Giới hạn mặc định cho Task mới; không đổi Task đã publish.')}</span><input class="input" name="taskTimeout" type="number" min="1" max="1440" step="1" required value="${settings.taskTimeout}"></label><label class="form-field"><span>Log rows</span><select class="input" name="logPageSize">${[25,50,100].map(n=>`<option ${n===settings.logPageSize?'selected':''}>${n}</option>`).join('')}</select></label></div><p class="form-error" id="settings-error" role="alert"></p><button class="button primary" type="submit">Save</button></form>`;
  return '<div class="page-heading"><div class="heading-copy"><h1>Settings</h1></div></div>'+`<div class="review-tabs">${tabs.map(([id,label])=>`<button class="${settings.tab===id?'active':''}" data-action="settings-tab" data-id="${id}">${label}</button>`).join('')}</div><div class="settings-content">${body}</div>`;
}
window.togglePasswordVisibility = function(btn) {
  const input = btn.previousElementSibling;
  if (!input) return;
  const isPass = input.type === 'password';
  input.type = isPass ? 'text' : 'password';
  btn.title = isPass ? 'Ẩn API key' : 'Xem API key';
  btn.setAttribute('aria-label', btn.title);
  btn.innerHTML = isPass
    ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>'
    : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
};

function integrationDialog(type,id=''){
  const list=type==='provider'?providers:models,item=list.find(x=>x.id===id);
  const field=(name,label,value='',inputType='text',extra='')=>inputType==='password'?`<label class="form-field"><span>${label}</span><div class="password-input-group"><input class="input" name="${name}" type="password" value="${escapeHTML(value)}" ${extra}><button type="button" class="password-toggle-btn" aria-label="Xem API key" title="Xem API key" onclick="togglePasswordVisibility(this)"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg></button></div></label>`:`<label class="form-field"><span>${label}</span><input class="input" name="${name}" type="${inputType}" value="${escapeHTML(value)}" ${extra}></label>`;
  const common=field('name','Name',item?.name||'','text','required maxlength="120"');
  const details=type==='provider'?`<label class="form-field"><span>API format ${settingsHelp('Chuẩn API mà nhà cung cấp hỗ trợ.')}</span><select class="input" name="type">${[['compatible','OpenAI-compatible'],['anthropic','Anthropic'],['custom','Custom']].map(([v,l])=>`<option value="${v}" ${item?.type===v?'selected':''}>${l}</option>`).join('')}</select></label>${field('baseUrl','Base URL '+settingsHelp('URL gốc của API nhà cung cấp.'),item?.baseUrl||'','url','required placeholder="https://api.example.com/v1"')}${field('apiKey','API key','','password','autocomplete="off" placeholder="Không lưu khóa trong bản xem thử"')}<p class="settings-note">Prototype: không lưu API key.</p>${field('timeout','Timeout · giây',item?.timeout||60,'number','required min="1" max="600" step="1"')}`:`${field('apiId','Model ID '+settingsHelp('Mã model do nhà cung cấp quy định.'),item?.apiId||'','text','required maxlength="200"')}<label class="form-field"><span>Provider</span><select class="input" name="provider" required>${providers.map(p=>`<option value="${p.id}" ${item?.provider===p.id?'selected':''}>${escapeHTML(p.name)}${p.enabled?'':' (Disabled)'}</option>`).join('')}</select></label><div class="form-row">${field('maxTokens','Max output '+settingsHelp('Số token tối đa trong một câu trả lời.'),item?.maxTokens||4096,'number','required min="1" step="1"')}${field('temperature','Temperature '+settingsHelp('Mức độ biến thiên của câu trả lời; thấp để ưu tiên nhất quán.'),item?.temperature??0.2,'number','required min="0" max="2" step="0.1"')}</div>`;
  const apiTest=type==='provider'?`<div class="api-test-area">${button('Test API','play-circle','','data-action="test-api"')}<span class="api-test-result" id="api-test-result" role="status" aria-live="polite">Demo · không gọi API thật</span></div><details class="api-demo"><summary>Demo scenario</summary><select class="input" name="testScenario" aria-label="Demo scenario"><option value="success">Success</option><option value="auth">Invalid key</option><option value="timeout">Timeout</option></select></details>`:'';
  showDialog(`${id?'Configure':'Add'} ${type}`,`<form id="integration-form" data-type="${type}" data-id="${id}">${common}${details}<label class="setting-checkbox"><input type="checkbox" name="enabled" ${item?.enabled===false?'':'checked'}> Enabled</label>${apiTest}<p id="integration-error" class="form-error" role="alert"></p><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">Save</button></div></form>`);
}
function resetApiTest(form){
  if(form.dataset.type!=='provider')return;
  form.dataset.testRevision=String(Number(form.dataset.testRevision||0)+1);delete form.dataset.testResult;
  const result=form.querySelector('#api-test-result'),button=form.querySelector('[data-action="test-api"]');
  if(result){result.className='api-test-result';result.textContent='Demo · không gọi API thật';}
  if(button){button.disabled=false;button.querySelector('span').textContent='Test API';}
}
function testApi(){
  const form=document.getElementById('integration-form');if(!form||form.dataset.type!=='provider')return;
  const error=document.getElementById('integration-error');error.textContent='';
  resetApiTest(form);
  let url;try{url=new URL(form.elements.baseUrl.value);}catch{error.textContent='Base URL không hợp lệ.';return;}
  if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash){error.textContent='Base URL phải là HTTP/HTTPS, không kèm credential hoặc query.';return;}
  if(!form.elements.apiKey.value.trim()){error.textContent='Nhập API key mẫu để test.';return;}
  const revision=form.dataset.testRevision,scenario=form.elements.testScenario.value,result=form.querySelector('#api-test-result'),button=form.querySelector('[data-action="test-api"]');
  button.disabled=true;button.querySelector('span').textContent='Testing…';result.className='api-test-result testing';result.textContent='Đang kiểm tra giả lập…';
  setTimeout(()=>{
    if(!form.isConnected||form.dataset.testRevision!==revision)return;
    const success=scenario==='success';form.dataset.testResult=success?'success':'error';
    button.disabled=false;button.querySelector('span').textContent='Test again';result.className='api-test-result '+(success?'success':'error');
    result.textContent=success?'Demo: kết nối thành công.':scenario==='auth'?'Demo: API key không hợp lệ (401).':'Demo: hết thời gian chờ.';
  },700);
}
function saveIntegration(form){
  const type=form.dataset.type,id=form.dataset.id,data=new FormData(form),list=type==='provider'?providers:models;
  const values={name:data.get('name').trim(),enabled:data.has('enabled')},fail=message=>document.getElementById('integration-error').textContent=message;
  if(!values.name||list.some(x=>x.id!==id&&x.name.toLowerCase()===values.name.toLowerCase()))return fail('Tên bắt buộc và không được trùng.');
  if(type==='provider'){
    let url;try{url=new URL(data.get('baseUrl'));}catch{return fail('Base URL không hợp lệ.');}
    if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)return fail('Dùng URL HTTP/HTTPS, không kèm credential hoặc query.');
    Object.assign(values,{type:data.get('type'),baseUrl:url.href.replace(/\/$/,''),timeout:Number(data.get('timeout'))});
    values.testResult=form.dataset.testResult||'';
    if(!Number.isInteger(values.timeout)||values.timeout<1||values.timeout>600)return fail('Request timeout phải từ 1 đến 600 giây.');
    // Deliberately discard apiKey; prototype has no trusted credential store.
  }else{
    Object.assign(values,{apiId:data.get('apiId').trim(),provider:data.get('provider'),maxTokens:Number(data.get('maxTokens')),temperature:Number(data.get('temperature'))});
    if(!values.apiId||!providers.some(p=>p.id===values.provider)||!Number.isInteger(values.maxTokens)||values.maxTokens<1||!Number.isFinite(values.temperature)||values.temperature<0||values.temperature>2)return fail('Kiểm tra Model ID, Provider, Max output và Temperature.');
    if(models.some(m=>m.id!==id&&m.provider===values.provider&&m.apiId===values.apiId))return fail('Model ID đã có trong provider này.');
  }
  if(id)Object.assign(list.find(x=>x.id===id),values);else list.push({id:type+'-'+entitySequence++,...values});
  if(type==='model'&&id)agents.filter(a=>a.modelId===id).forEach(a=>a.model=values.name);
  processes.filter(blockedResources).forEach(p=>p.enabled=false);
  modalRoot.innerHTML='';render();showToast('Đã lưu cấu hình trong phiên xem thử.');
}

function builderPage(){return robotBuilderPage();}
function drawEdges() {
  const svg=app.querySelector('.review-edges'); if(!svg)return;
  const nodes=builderNodes();
  svg.innerHTML=nodes.slice(1).map((n,i)=>{const a=nodes[i], el=app.querySelector(`[data-node="${a.id}"]`), target=app.querySelector(`[data-node="${n.id}"]`);const x=a.x+el.offsetWidth,y=a.y+el.offsetHeight/2, ty=n.y+target.offsetHeight/2;return `<path d="M${x} ${y} C${x+40} ${y},${n.x-40} ${ty},${n.x} ${ty}"/>`;}).join('');
}
function render() {
  closeProcessMenu();
  const pages={dashboard:dashboardPage,projects:projectsPage,project:projectPage,builder:builderPage,agents:agentsPage,skills:skillsPage,tools:toolsPage,runs:runsPage,runners:pcPage,settings:settingsPage};
  app.className=state.route==='builder'?'builder-shell':'';
  app.innerHTML=(pages[state.route]||dashboardPage)();
  const inProject=state.route==='project'||state.route==='builder';
  document.getElementById('breadcrumbs').innerHTML=inProject?`<span>Projects</span><span>/</span><strong>${escapeHTML(projectById(state.project).name)}${state.route==='builder'?' / '+escapeHTML(currentProcess().name):''}</strong>`:`<span>Company</span><span>/</span><strong>${titles[state.route]}</strong>`;
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.dataset.route===(inProject?'projects':state.route)));
  document.getElementById('runningCount').innerHTML=`<i></i>${runs.filter(r=>r.status==='running').length}`;
  const online=pcs.filter(availablePc).length,total=pcs.filter(pc=>!pc.removed).length;
  document.querySelector('.runner-mini-head > span:last-child').textContent=online+'/'+total;
  document.querySelector('.mini-progress > span').style.width=(total?online/total*100:0)+'%';
  document.title=`${titles[state.route]} — Agent CF`;
  requestAnimationFrame(drawEdges);
}
function navigate(route) {
  state.route=titles[route]?route:'projects';
  if(state.route==='builder'&&!currentProcess()){
    const replacement=processes.find(p=>p.project===state.project&&!p.archived);
    if(replacement)state.process=replacement.id;else state.route='projects';
  }
  if(state.route==='project'&&!projectById(state.project))state.route='projects';
  const params=new URLSearchParams({page:state.route});
  if(state.route==='project'||state.route==='builder')params.set('project',state.project);
  if(state.route==='builder')params.set('process',state.process);
  history.replaceState(null,'','#'+params);
  document.body.classList.remove('sidebar-open');
  render(); app.focus({preventScroll:true}); window.scrollTo(0,0);
}
function showToast(message) {
  const toast=document.createElement('div');toast.className='toast';toast.setAttribute('role','status');toast.textContent=message;
  document.getElementById('toastRegion').append(toast);setTimeout(()=>toast.remove(),3500);
}
function showDialog(title,body,footer='') {
  closeProcessMenu();
  modalRoot.innerHTML=`<div class="modal-backdrop" data-action="close-modal"></div><section class="modal review-modal" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><div class="modal-header"><h2 id="dialog-title">${escapeHTML(title)}</h2><button class="icon-button" data-action="close-modal" aria-label="Đóng">${icon('close')}</button></div><div class="modal-body">${body}</div>${footer?`<div class="modal-footer">${footer}</div>`:''}</section>`;
  modalRoot.querySelector('input,select,button')?.focus();
}
let entitySequence = 1;
function resourceDialog(type,id='') {
  if(type==='tool')state.skillsTab='tools';
  const item=resourceLists[type].find(r=>r.id===id), value=(field,fallback='')=>escapeHTML(item?.[field]??fallback);
  const input=(field,label,inputType='text',fallback='')=>`<label class="form-field"><span>${label}</span><input class="input" name="${field}" type="${inputType}" value="${value(field,fallback)}" ${field==='name'?'required maxlength="120"':''} ${inputType==='number'?'min="0" step="0.01"':''}></label>`;
  const text=(field,label,required=false)=>`<label class="form-field"><span>${label}</span><textarea class="textarea" name="${field}" maxlength="4000" ${required?'required':''}>${value(field)}</textarea></label>`;
  const picker=(kind,field,label)=>`<fieldset class="resource-picker"><legend>${label}</legend>${resourceLists[kind].filter(r=>!r.archived||item?.[field]?.includes(r.id)).map(r=>`<label><input type="checkbox" name="${field}" value="${r.id}" ${item?.[field]?.includes(r.id)?'checked':''}>${escapeHTML(r.name)}${r.archived?' (Archived)':''}</label>`).join('')||'<p>Chưa có mục để chọn.</p>'}</fieldset>`;
  const fields=type==='agent'?roleSelect(item)+text('instructions','Base instructions',true)+`<label class="form-field"><span>Model</span><select class="input" name="model">${models.filter(m=>(m.enabled&&providers.find(p=>p.id===m.provider)?.enabled)||m.id===item?.modelId).map(m=>`<option value="${m.id}" ${item?.modelId===m.id?'selected':''}>${escapeHTML(m.name)}${m.enabled?'':' (Disabled)'}</option>`).join('')}</select></label>`+picker('skill','skillIds','Skills')+picker('tool','toolIds','Allowed tools'):type==='skill'?text('desc','Description')+text('instructions','Instructions',true)+text('output','Expected output',true)+picker('tool','toolIds','Tools sử dụng'):text('desc','Description')+`<label class="form-field"><span>Type</span><select class="input" name="icon">${[['globe','Web / API'],['folder','Files'],['code','Script'],['database','Data'],['upload','Publish']].map(([v,l])=>`<option value="${v}" ${item?.icon===v?'selected':''}>${l}</option>`).join('')}</select></label>`;
  showDialog(`${id?'Edit':'New'} ${type}`,`<form id="resource-form" data-type="${type}" data-id="${id}">${input('name','Name')}${fields}${type==='skill'&&id?'<p class="dialog-note">Lưu tạo version Skill mới trong catalog. Nhãn và cấu hình trong Process đã publish vẫn được giữ nguyên.</p>':''}<p class="form-error" id="resource-error" role="alert"></p><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">${id?'Save changes':'Create '+type}</button></div></form>`);
}
function saveResource(form){
  const type=form.dataset.type,id=form.dataset.id,list=resourceLists[type],data=new FormData(form),name=data.get('name').trim();
  const fail=msg=>{document.getElementById('resource-error').textContent=msg;};
  if(!name)return fail('Name không được chỉ chứa khoảng trắng.');
  if(list.some(r=>r.id!==id&&r.name.toLocaleLowerCase('vi')===name.toLocaleLowerCase('vi')))return fail('Tên đã được sử dụng trong danh mục này.');
  const values={name};
  if(type==='agent'){
    Object.assign(values,{roleId:data.get('roleId'),role:roleById(data.get('roleId'))?.name||'',instructions:data.get('instructions').trim(),modelId:data.get('model'),model:models.find(m=>m.id===data.get('model'))?.name||'',skillIds:data.getAll('skillIds'),toolIds:data.getAll('toolIds')});
    if(!values.model||!values.role||!values.instructions)return fail('Cần Role, Model và Instructions.');
    const assignedRole=roleById(values.roleId);
    if(!assignedRole||(assignedRole.archived&&list.find(a=>a.id===id)?.roleId!==assignedRole.id))return fail('Chọn Role đang hoạt động.');
    const requiredTools=values.skillIds.flatMap(skillId=>skills.find(s=>s.id===skillId).toolIds);
    if(requiredTools.some(toolId=>!values.toolIds.includes(toolId)))return fail('Allowed tools phải bao gồm các công cụ Skill đã chọn cần sử dụng.');
  }else if(type==='skill'){
    Object.assign(values,{desc:data.get('desc').trim(),instructions:data.get('instructions').trim(),output:data.get('output').trim(),toolIds:data.getAll('toolIds')});
    if(!values.instructions||!values.output)return fail('Cần Instructions và Expected output.');
  }else Object.assign(values,{desc:data.get('desc').trim(),icon:data.get('icon')});
  if(id){
    const item=list.find(r=>r.id===id),oldName=item.name;
    if(type==='skill'){
      item.versions??=[];
      item.versions.push({version:item.version,name:item.name,desc:item.desc,instructions:item.instructions,output:item.output,toolIds:[...item.toolIds]});
    }
    Object.assign(item,values);
    if(type==='agent')projects.filter(p=>p.pm===oldName).forEach(p=>p.pm=name);
    if(type==='skill')item.version='v'+(Number(item.version.slice(1))+1);
  }else list.push({id:type+'-custom-'+entitySequence++,originalName:name,...values,...(type==='agent'?{tokens:0,quality:null,skills:[]}:type==='skill'?{version:'v1'}:{status:'active'})});
  processes.filter(blockedResources).forEach(p=>p.enabled=false);
  modalRoot.innerHTML='';archivedResources[type]=false;navigate(resourceRoutes[type]);showToast('Đã lưu '+type+' trong phiên xem thử.');
}
function resourceUsage(type,id){
  const item=resourceLists[type].find(r=>r.id===id),usages=[];
  if(type==='agent')projects.filter(p=>p.pm===item.name).forEach(p=>usages.push('PM · '+p.name));
  if(type==='agent')projects.filter(p=>p.memberIds?.includes(id)&&p.pmId!==id).forEach(p=>usages.push('Team · '+p.name));
  if(type==='skill')agents.filter(a=>a.skillIds.includes(id)).forEach(a=>usages.push('Agent · '+a.name));
  if(type==='tool'){
    pcs.filter(pc=>!pc.removed&&pc.toolIds.includes(id)).forEach(pc=>usages.push('PC · '+pc.label));
    agents.filter(a=>a.toolIds.includes(id)).forEach(a=>usages.push('Agent · '+a.name));
    skills.filter(s=>s.toolIds.includes(id)).forEach(s=>usages.push('Skill · '+s.name));
  }
  processes.forEach(p=>{if(graphs[p.id].some(n=>type==='agent'?n.agentId===id:type==='skill'?n.skillId===id:n.toolIds.includes(id)))usages.push('Process · '+p.name);});
  return usages;
}
function deleteResourceDialog(type,id){
  const item=resourceLists[type].find(r=>r.id===id),used=resourceUsage(type,id),archive=used.length>0||(item.tokens||0)>0;
  showDialog(`${archive?'Archive':'Delete'} ${type}?`,`<p>Bạn sắp ${archive?'archive':'xóa'} <strong>${escapeHTML(item.name)}</strong>.</p>${archive?`<p>Mục này có liên kết hoặc dữ liệu sử dụng nên sẽ giữ lại để truy vết. Lịch các Process liên quan sẽ tắt; run đang chạy không bị hủy. Không dùng cho lượt chạy mới cho đến khi Restore.</p>${used.length?`<details open><summary>Đang được sử dụng (${used.length})</summary><ul class="resource-usage">${used.map(x=>`<li>${escapeHTML(x)}</li>`).join('')}</ul></details>`:''}`:'<p>Mục chưa được sử dụng sẽ bị xóa khỏi danh mục trong phiên hiện tại.</p>'}`,button('Cancel','close','','data-action="close-modal"')+button(archive?'Archive '+type:'Delete '+type,'trash','danger',`data-action="confirm-resource-delete" data-type="${type}" data-id="${id}"`));
}
function blockedResources(p){
  return agents.find(a=>a.name===projectById(p.project).pm)?.archived||graphs[p.id].some(n=>{
    const agent=agents.find(a=>a.id===n.agentId),model=models.find(m=>m.id===agent?.modelId),provider=providers.find(p=>p.id===model?.provider);
    return n.robotId&&(!robotById(n.robotId)||robotById(n.robotId).archived||!pcs.some(pc=>pc.name===n.pc&&!pc.disabled&&!pc.removed))||!model?.enabled||!provider?.enabled||agent?.archived||skills.find(s=>s.id===n.skillId)?.archived||n.toolIds.some(id=>tools.find(t=>t.id===id)?.archived||!agent?.toolIds.includes(id));
  });
}
function deleteResource(type,id){
  const list=resourceLists[type],item=list.find(r=>r.id===id);
  if(resourceUsage(type,id).length||(item.tokens||0)>0){item.archived=true;processes.filter(blockedResources).forEach(p=>p.enabled=false);}
  else list.splice(list.indexOf(item),1);
  modalRoot.innerHTML='';navigate(resourceRoutes[type]);showToast(item.archived?'Đã Archive, giữ tham chiếu và lịch sử.':'Đã xóa '+type+'.');
}
function deleteEntityDialog(type,id) {
  const entity=type==='project'?projectById(id):processById(id);
  const related=type==='project'?processes.filter(p=>p.project===id):[entity];
  const history=runs.filter(r=>related.some(p=>p.id===r.process));
  if(history.some(r=>['running','cancelling'].includes(r.status))){
    showDialog('Chưa thể xóa '+type,`<p><strong>${escapeHTML(entity.name)}</strong> đang có run hoạt động. Hãy hủy run trong Runs hoặc đợi hoàn tất trước khi xóa.</p>`,button('Open Runs','arrow','primary','data-action="close-and-runs"'));return;
  }
  const archive=history.length>0;
  showDialog(archive?'Archive '+type+'?':'Delete '+type+'?',`<p>Bạn sắp ${archive?'archive':'xóa'} <strong>${escapeHTML(entity.name)}</strong>.</p><p>${archive?'Mục này đã có lịch sử chạy nên sẽ được chuyển vào Archived. Lịch chạy sẽ tắt; toàn bộ Runs và Logs được giữ lại. Có thể Restore sau.':`Mục này chưa có lịch sử chạy. Xóa sẽ loại bỏ ${type==='project'?`${related.length} process, sơ đồ và lịch thuộc dự án`:'sơ đồ và lịch của process'} trong phiên hiện tại.`}</p>`,button('Cancel','close','','data-action="close-modal"')+button(archive?'Archive '+type:'Delete '+type,'trash','danger',`data-action="confirm-delete" data-type="${type}" data-id="${id}"`));
}
function deleteEntity(type,id) {
  const entity=type==='project'?projectById(id):processById(id);
  const related=type==='project'?processes.filter(p=>p.project===id):[entity];
  const history=runs.filter(r=>related.some(p=>p.id===r.process));
  if(history.some(r=>['running','cancelling'].includes(r.status)))return deleteEntityDialog(type,id);
  if(history.length){entity.archived=true;related.forEach(p=>{p.enabled=false;if(type==='process')p.archived=true;});}
  else {
    related.forEach(p=>{processes.splice(processes.indexOf(p),1);delete graphs[p.id];delete processDrafts[p.id];delete processVersions[p.id];});
    if(type==='project')projects.splice(projects.indexOf(entity),1);
  }
  modalRoot.innerHTML='';navigate(type==='project'?'projects':'project');showToast(history.length?'Đã Archive và tắt lịch; giữ nguyên lịch sử.':'Đã xóa trong phiên xem thử.');
}
function entityDialog(type,id=''){
  if(type==='project'){projectEntityDialog(id);return;}
  const p=processById(id);
  showDialog(id?'Edit process':'New process',`<form id="entity-form" data-type="process" data-id="${id}"><label class="form-field"><span>Name</span><input class="input" name="name" required maxlength="120" value="${escapeHTML(p?.name||'')}"></label><label class="form-field"><span>Description</span><textarea class="textarea" name="desc" maxlength="1000">${escapeHTML(p?.desc||'')}</textarea></label><p id="entity-error" class="form-error" role="alert"></p><div class="form-actions">${button('Cancel','close','','data-action="close-modal"')}<button class="button primary" type="submit">${id?'Save':'Create process'}</button></div></form>`);
}
function saveEntity(form){
  const data=new FormData(form),name=data.get('name').trim(),id=form.dataset.id;
  if(!name){document.getElementById('entity-error').textContent='Name không được chỉ chứa khoảng trắng.';return;}
  if(id)Object.assign(processById(id),{name,desc:data.get('desc').trim()});
  else{const p={id:'process-'+entitySequence++,project:state.project,name,desc:data.get('desc').trim(),version:0,enabled:false,frequency:'manual',day:'1',time:'09:00',pc:'Auto',tasks:5};processes.push(p);graphs[p.id]=graphFor(p);}
  modalRoot.innerHTML='';navigate('project');
}

function scheduleDialog(id) {
  const p=processById(id);if(!p.version||p.archived||projectById(p.project).archived)return;
  showDialog('Schedule · '+p.name,`<form id="schedule-form" data-id="${p.id}"><p class="dialog-note">${p.enabled?'Lịch đang bật. Lưu thay đổi áp dụng cho lượt kế tiếp.':'Lưu cấu hình rồi bấm Start trong Project để bật lịch.'}</p><label class="form-field"><span>Frequency</span><select class="input" name="frequency">${[['manual','Manual'],['daily','Daily'],['weekly','Weekly']].map(([v,l])=>`<option value="${v}" ${p.frequency===v?'selected':''}>${l}</option>`).join('')}</select></label><label class="form-field" id="schedule-day"><span>Day</span><select class="input" name="day">${['Chủ nhật','Thứ Hai','Thứ Ba','Thứ Tư','Thứ Năm','Thứ Sáu','Thứ Bảy'].map((d,i)=>`<option value="${i}" ${p.day===String(i)?'selected':''}>${d}</option>`).join('')}</select></label><label class="form-field" id="schedule-time"><span>Time · Asia/Ho_Chi_Minh (GMT+7)</span><input class="input" type="time" name="time" required value="${p.time}"></label><label class="form-field"><span>Published version</span><select class="input" name="scheduleVersion">${Object.keys(processVersions[p.id]||{[p.version]:graphs[p.id]}).map(v=>`<option value="${v}" ${Number(v)===(p.scheduleVersion||p.version)?'selected':''}>v${v}</option>`).join('')}</select></label><label class="form-field"><span>PC</span><select class="input" name="pc">${pcOptions(p.pc)}</select></label><div class="schedule-preview" id="schedule-preview"></div><button class="button primary" type="submit">Save schedule</button></form>`);
  updateSchedulePreview();
}
function updateSchedulePreview() {
  const form=document.getElementById('schedule-form');if(!form)return;
  const data=Object.fromEntries(new FormData(form));
  document.getElementById('schedule-day').hidden=data.frequency!=='weekly';
  document.getElementById('schedule-time').hidden=data.frequency==='manual';
  document.getElementById('schedule-preview').textContent=data.frequency==='manual'?`Chạy theo yêu cầu trên ${data.pc}.`:`Chạy ${scheduleText(data)} · giờ Việt Nam · v${data.scheduleVersion||processById(form.dataset.id).version} · ${data.pc}.`;
}
function runDialog(id) {
  const p=processById(id);if(blockedResources(p)){showToast('Check disabled Provider/Model or archived Agent/Skill/Tool before Run.');return;}if(!p.version||p.archived||projectById(p.project).archived)return;
  showDialog('Run · '+p.name,`<form id="run-form" data-id="${id}"><p>${p.version ? `Published v${p.version}` : 'Draft'} · ${escapeHTML(projectById(p.project).name)}</p><label class="form-field"><span>PC</span><select class="input" name="pc">${pcOptions(p.pc,true)}</select></label><label class="form-field"><span>Input · JSON</span><textarea class="textarea" name="input">{"topic":"AI agents"}</textarea></label><p id="run-error" class="form-error" role="alert"></p><button class="button primary" type="submit">Run now</button></form>`);
}
let runLogView = null;
function runTaskStates(run) {
  const nodes = (run.graphSnapshot||graphs[run.process]), completed = Math.floor(run.progress / 100 * nodes.length);
  return nodes.map((node, i) => ({ ...node, status: i < completed ? 'succeeded' : i === completed ? ({ running: 'running', cancelling: 'cancelling', cancelled: 'cancelled', failed: 'failed' }[run.status] || 'pending') : ['failed', 'cancelled', 'cancelling'].includes(run.status) ? 'skipped' : 'pending' }));
}
function runLogEvents(run) {
  // Detailed sample events exercise large log tables; there is no execution engine.
  if (!run.logEvents) {
    const base = { 'R-1084': '2026-11-13T14:02:00+07:00', 'R-1083': '2026-11-13T09:00:00+07:00', 'R-1082': '2026-11-12T10:00:00+07:00', 'R-1081': '2026-11-12T08:00:00+07:00' };
    run.logStartedAt = new Date(run.startedAt || base[run.id] || Date.now()).getTime();
    run.logEvents = [];
    const messages = [
      ['INFO', 'runner', 'Đã nhận quyền thực thi task.'],
      ['INFO', 'agent', 'Nạp hướng dẫn và Skill đã được gán.'],
      ['DEBUG', 'policy', 'Kiểm tra quyền công cụ trong phạm vi task.'],
      ['INFO', 'tool', 'Bắt đầu xử lý dữ liệu đầu vào.'],
      ['DEBUG', 'agent', 'Kiểm tra cấu trúc kết quả trung gian.'],
      ['INFO', 'agent', 'Đã xử lý một phần dữ liệu.']
    ];
    runTaskStates(run).filter(n => !['pending', 'skipped'].includes(n.status)).forEach(node => {
      for (let i = 0; i < 24; i++) {
        const [level, source, message] = messages[i % messages.length];
        run.logEvents.push({ time: run.logStartedAt + run.logEvents.length * 1200, level, node: node.id, agent: node.agent, source, message: `${message} [${Math.floor(i / messages.length) + 1}]` });
      }
      run.logEvents.push({ time: run.logStartedAt + run.logEvents.length * 1200, level: node.status === 'failed' ? 'ERROR' : 'INFO', node: node.id, agent: node.agent, source: 'runner', message: node.status === 'failed' ? 'Task timeout: quá thời gian chờ phản hồi. Downstream tasks bị skipped.' : node.status === 'succeeded' ? 'Task hoàn tất. Output đã được kiểm tra.' : 'Task đang xử lý.' });
    });
  }
  return [...run.logEvents, ...run.logs.map((message, i) => ({ time: run.logStartedAt + (run.logEvents.length + i) * 1200, level: /timeout|thất bại|không phản hồi/i.test(message) ? 'ERROR' : /hủy/i.test(message) ? 'WARN' : 'INFO', node: '', agent: '—', source: 'control plane', message }))];
}
function openRun(id) {
  const run = runs.find(r => r.id === id), p = processById(run.process), nodes = runTaskStates(run);
  runLogView = { id, query: '', level: 'all', node: 'all', page: 1, pageSize: settings.logPageSize };
  showDialog(`${id} · ${escapeHTML(p.name)}`, `<div class="run-detail-head">${badge(run.status)}${run.status==='failed'?button(handledRunAlerts.has(run.id)?'Reopen alert':'Đã xử lý','check','small',`data-action="${handledRunAlerts.has(run.id)?'reopen-run-alert':'handle-run-alert'}" data-id="${run.id}"`):''}<span>${escapeHTML(projectById(p.project).name)} · v${run.version} · ${run.pc} · ${run.source}</span>${run.status === 'running' ? button('Cancel run', 'close', 'small danger', `data-action="cancel-run" data-id="${id}"`) : ''}</div>
    <div class="run-node-strip" aria-label="Task execution order">${nodes.map((n, i) => `${i ? '<span class="run-node-arrow" aria-hidden="true">→</span>' : ''}<button class="run-node-chip ${n.status}" data-action="log-node" data-id="${n.id}" aria-pressed="false" title="${escapeHTML(n.title)} · ${escapeHTML(n.agent)} · ${escapeHTML(pcDisplay(n.pc||run.pc))}"><span class="run-node-order">${i + 1}</span><span><strong>${escapeHTML(n.title)}</strong><span class="run-node-status">${n.status}</span></span></button>`).join('')}</div>
    <details class="run-output"><summary>Output</summary><p>${run.status === 'succeeded' ? 'Kết quả mẫu đã hoàn tất và sẵn sàng review.' : 'Chưa có output hoàn chỉnh của process.'}</p></details>
    <div class="log-heading"><h3>Logs</h3></div>
    <div class="log-filters"><label class="log-search"><span>Search</span><input type="search" class="input" id="log-search" placeholder="Tìm message, agent, source…"></label><label><span>Level</span><select class="select" id="log-level"><option value="all">All levels</option>${['DEBUG', 'INFO', 'WARN', 'ERROR'].map(l => `<option>${l}</option>`).join('')}</select></label><label><span>Node</span><select class="select" id="log-node"><option value="all">All nodes</option>${nodes.map(n => `<option value="${n.id}">${escapeHTML(n.title)}</option>`).join('')}<option value="system">System</option></select></label><label><span>Rows</span><select class="select" id="log-page-size">${[25,50,100].map(n=>`<option ${n===settings.logPageSize?'selected':''}>${n}</option>`).join('')}</select></label>${button('Reset', 'refresh', 'small', 'data-action="log-reset"')}</div>
    <div id="log-results" class="log-results"></div><div id="log-pagination" class="log-pagination" aria-live="polite"></div>`);
  modalRoot.querySelector('.modal').classList.add('run-log-modal');
  renderRunLogs();
}
function renderRunLogs() {
  if (!runLogView || !document.getElementById('log-results')) return;
  const view = runLogView, run = runs.find(r => r.id === view.id), nodes = run.graphSnapshot||graphs[run.process];
  const all = runLogEvents(run);
  const filtered = all.filter(row => (view.level === 'all' || row.level === view.level) && (view.node === 'all' || row.node === (view.node === 'system' ? '' : view.node)) && [row.message, row.agent, row.source, row.level, nodes.find(n => n.id === row.node)?.title || 'System'].join(' ').toLocaleLowerCase('vi').includes(view.query.toLocaleLowerCase('vi')));
  const pages = Math.max(1, Math.ceil(filtered.length / view.pageSize));
  view.page = Math.min(Math.max(1, view.page), pages);
  const start = (view.page - 1) * view.pageSize, rows = filtered.slice(start, start + view.pageSize);
  const clock = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3, hour12: false });
  document.getElementById('log-results').innerHTML = `<table class="log-table"><thead><tr><th>Time</th><th>Level</th><th>Node</th><th>Agent</th><th>Source</th><th>Message</th></tr></thead><tbody>${rows.length ? rows.map(row => `<tr><td class="log-time">${clock.format(row.time)}</td><td><span class="log-level ${row.level.toLowerCase()}">${row.level}</span></td><td>${escapeHTML(nodes.find(n => n.id === row.node)?.title || 'System')}</td><td>${escapeHTML(row.agent)}</td><td>${escapeHTML(row.source)}</td><td class="log-message">${escapeHTML(row.message)}</td></tr>`).join('') : '<tr><td colspan="6" class="log-empty">Không có log khớp bộ lọc.</td></tr>'}</tbody></table>`;
  document.getElementById('log-results').scrollTop = 0;
  document.getElementById('log-pagination').innerHTML = `<span>${filtered.length ? start + 1 : 0}–${start + rows.length} / ${filtered.length} logs${filtered.length !== all.length ? ` · ${all.length} tổng` : ''}</span><div>${button('Previous', 'back', 'small', `data-action="log-page" data-id="${view.page - 1}" ${view.page === 1 ? 'disabled' : ''}`)}<span>Page ${view.page} / ${pages}</span>${button('Next', 'arrow', 'small', `data-action="log-page" data-id="${view.page + 1}" ${view.page === pages ? 'disabled' : ''}`)}</div>`;
  modalRoot.querySelectorAll('[data-action="log-node"]').forEach(el => { const selected = el.dataset.id === view.node; el.classList.toggle('log-selected', selected); el.setAttribute('aria-pressed', selected); });
}
function cancelRun(id) {
  const r=runs.find(x=>x.id===id);if(!r||r.status!=='running')return;
  r.status='cancelling';r.logs.push('Người vận hành yêu cầu hủy. Ngăn task mới bắt đầu.');
  modalRoot.innerHTML='';render();showToast('Đang hủy '+r.id+'…');
  setTimeout(()=>{r.status='cancelled';r.endedAt=new Date().toISOString();r.logs.push('Đã hủy trong bản mô phỏng. Giữ lịch sử và output đã có.');render();showToast(r.id+' đã hủy. Lịch process không thay đổi.');},900);
}
function openPalette() {
  const palette=document.getElementById('commandPalette');palette.classList.add('open');palette.setAttribute('aria-hidden','false');document.getElementById('commandInput').value='';renderPalette('');document.getElementById('commandInput').focus();
}
function closePalette() { const el=document.getElementById('commandPalette');el.classList.remove('open');el.setAttribute('aria-hidden','true'); }
function renderPalette(query) { document.getElementById('paletteContent').innerHTML=Object.entries(titles).filter(([id,label])=>!['project','builder'].includes(id)&&label.toLowerCase().includes(query.toLowerCase())).map(([id,label])=>`<button class="palette-item" data-route="${id}">${icon('arrow')} ${label}</button>`).join('')||'<p>Không có kết quả.</p>'; }

document.addEventListener('click',e=>{
  const action=e.target.closest('[data-action]');
  if(action){
    const id=action.dataset.id;
    switch(action.dataset.action){
      case 'open-project': state.projectRunFilter='all';state.showArchivedProcesses=false;state.project=id;state.tab='processes';navigate('project');return;
      case 'new-project':entityDialog('project');return;
      case 'robot-new':robotDialog();return;
      case 'robot-edit':robotDialog(id);return;
      case 'robot-version':robotDialog(id,true);return;
      case 'robot-delete':robotDeleteDialog(id);return;
      case 'robot-confirm-delete':deleteRobot(id);return;
      case 'robot-restore':robotById(id).archived=false;showArchivedRobots=false;render();return;
      case 'robot-archived':showArchivedRobots=!showArchivedRobots;render();return;
      case 'robot-node-add':robotNodeDialog(id);return;
      case 'robot-node-edit':{const node=builderNodes().find(n=>n.id===id);robotNodeDialog(node.robotId,id);return;}
      case 'skill-tab':state.skillsTab=id;render();return;
      case 'new-resource':resourceDialog(action.dataset.type);return;
      case 'settings-tab':settings.tab=id;render();return;
      case 'role-new':roleDialog();return;
      case 'role-edit':roleDialog(id);return;
      case 'role-delete':roleDeleteDialog(id);return;
      case 'role-confirm-delete':deleteRole(id);return;
      case 'role-archived':showArchivedRoles=!showArchivedRoles;render();return;
      case 'role-restore':roleById(id).archived=false;showArchivedRoles=false;render();return;
      case 'provider-edit':integrationDialog('provider',id);return;
      case 'test-api':testApi();return;
      case 'model-edit':integrationDialog('model',id);return;
      case 'edit-resource':resourceDialog(action.dataset.type,id);return;
      case 'delete-resource':deleteResourceDialog(action.dataset.type,id);return;
      case 'confirm-resource-delete':deleteResource(action.dataset.type,id);return;
      case 'resource-archive-view':archivedResources[action.dataset.type]=!archivedResources[action.dataset.type];render();return;
      case 'restore-resource':resourceLists[action.dataset.type].find(r=>r.id===id).archived=false;archivedResources[action.dataset.type]=false;render();showToast('Đã Restore. Lịch vẫn tắt cho đến khi Start.');return;
      case 'edit-project':entityDialog('project',id);return;
      case 'new-process':entityDialog('process');return;
      case 'edit-process':entityDialog('process',id);return;
      case 'delete-project':deleteEntityDialog('project',id);return;
      case 'delete-process':deleteEntityDialog('process',id);return;
      case 'confirm-delete':deleteEntity(action.dataset.type,id);return;
      case 'close-and-runs':modalRoot.innerHTML='';navigate('runs');return;
      case 'archive-projects':state.showArchivedProjects=!state.showArchivedProjects;render();return;
      case 'archive-processes':state.showArchivedProcesses=!state.showArchivedProcesses;render();return;
      case 'restore-project':projectById(id).archived=false;state.showArchivedProjects=false;render();showToast('Đã Restore. Lịch vẫn tắt cho đến khi Start.');return;
      case 'restore-process':processById(id).archived=false;state.showArchivedProcesses=false;render();showToast('Đã Restore. Lịch vẫn tắt cho đến khi Start.');return;
      case 'publish-process':publishProcessDraft(id);return;
      case 'open-process': state.process=id;state.project=processById(id).project;state.selectedNode=(processDrafts[id]||graphs[id])[0].id;state.zoom=1;navigate('builder');return;
      case 'project-tab':state.tab=id;render();return;
      case 'project-running':state.project=id;state.tab='results';state.projectRunFilter='running';navigate('project');return;
      case 'project-run-filter':state.projectRunFilter=id;render();return;
      case 'agent-token-detail':agentTokenDetail(id);return;
      case 'handle-run-alert':handleRunAlert(id);return;
      case 'reopen-run-alert':handleRunAlert(id,true);return;
      case 'process-menu':openProcessMenu(id,action);return;
      case 'project-team':projectTeamDialog();return;
      case 'project-target-new':projectTargetDialog();return;
      case 'project-target-edit':projectTargetDialog(id);return;
      case 'run-filter':state.runFilter=id;render();return;
      case 'runs-page':runListView.page=Number(id);render();return;
      case 'runs-reset':Object.assign(runListView,{project:'all',process:'all',query:'',from:runDateKey(Date.now()-6*86400000),to:runDateKey(Date.now()),page:1});state.runFilter='all';render();return;
      case 'schedule':scheduleDialog(id);return;
      case 'run-now':runDialog(id);return;
      case 'toggle-process':{const p=processById(id);if(!p.version||p.archived||projectById(p.project).archived||p.frequency==='manual')return;if(blockedResources(p)){showToast('Check disabled Provider/Model or archived Agent/Skill/Tool before Start.');return;}if(p.pc!=='Auto'&&!pcs.some(pc=>pc.name===p.pc&&!pc.disabled&&!pc.removed)){showToast('PC is disabled or removed. Choose another PC.');return;}p.enabled=!p.enabled;render();showToast(p.enabled?'Đã Start: lịch được bật, chờ mốc chạy kế tiếp.':'Đã Stop: tắt lịch. Lượt đang chạy vẫn tiếp tục.');return;}
      case 'open-run':openRun(id);return;
      case 'log-page':if(runLogView){runLogView.page=Number(id);renderRunLogs();}return;
      case 'log-node':if(runLogView){runLogView.node=runLogView.node===id?'all':id;runLogView.page=1;document.getElementById('log-node').value=runLogView.node;renderRunLogs();}return;
      case 'log-reset':if(runLogView){runLogView.query='';runLogView.level='all';runLogView.node='all';runLogView.page=1;document.getElementById('log-search').value='';document.getElementById('log-level').value='all';document.getElementById('log-node').value='all';renderRunLogs();}return;
      case 'cancel-run':cancelRun(id);return;
      case 'close-modal':modalRoot.innerHTML='';return;
      case 'zoom-in':state.zoom=Math.min(1.4,state.zoom+.1);render();return;
      case 'zoom-out':state.zoom=Math.max(.5,state.zoom-.1);render();return;
      case 'zoom-reset':state.zoom=1;render();return;
      case 'connect-pc':connectPc();return;
      case 'pc-details':pcDetails(id);return;
      case 'pc-edit':editPc(id);return;
      case 'pc-toggle':pcActionDialog(id);return;
      case 'pc-remove':pcActionDialog(id,true);return;
      case 'pc-confirm':confirmPcAction(id,action.dataset.remove==='true');return;
      case 'pc-simulate':simulatePcConnection();return;

      case 'close-palette':closePalette();return;
      default:showToast('Agent CF Company · bản xem thử giao diện.');return;
    }
  }
  const route=e.target.closest('[data-route]');if(route){navigate(route.dataset.route);closePalette();}
});
document.addEventListener('submit',e=>{
  if(e.target.id==='role-form'){e.preventDefault();saveRole(e.target);return;}
  if(e.target.id==='project-entity-form'){e.preventDefault();saveProjectEntity(e.target);return;}
  if(e.target.id==='project-target-form'){e.preventDefault();saveProjectTarget(e.target);return;}
  if(e.target.id==='project-team-form'){
    e.preventDefault();const p=projectById(state.project);p.memberIds=[...new Set([p.pmId,...projectAssignedIds(p),...new FormData(e.target).getAll('memberIds')])];modalRoot.innerHTML='';render();return;
  }
  if(e.target.id==='robot-form'){e.preventDefault();saveRobot(e.target);return;}
  if(e.target.id==='robot-node-form'){e.preventDefault();saveRobotNode(e.target);return;}
  if(e.target.id==='pc-edit-form'){
    e.preventDefault();const pc=pcById(e.target.dataset.id),label=new FormData(e.target).get('label').trim();
    if(!label||pcs.some(p=>p.id!==pc.id&&!p.removed&&p.label.toLowerCase()===label.toLowerCase())){document.getElementById('pc-edit-error').textContent='Tên bắt buộc và không được trùng.';return;}
    pc.label=label;modalRoot.innerHTML='';render();showToast('Đã lưu tên PC.');return;
  }
  if(e.target.id==='integration-form'){e.preventDefault();saveIntegration(e.target);return;}
  if(e.target.id==='general-settings-form'){
    e.preventDefault();const data=new FormData(e.target),timeout=Number(data.get('taskTimeout')),rows=Number(data.get('logPageSize'));
    if(!Number.isInteger(timeout)||timeout<1||timeout>1440||![25,50,100].includes(rows)){document.getElementById('settings-error').textContent='Kiểm tra timeout và số dòng Logs.';return;}
    settings.taskTimeout=timeout;settings.logPageSize=rows;showToast('Đã lưu mặc định cho Task và bảng Logs mới.');return;
  }
  if(e.target.id==='resource-form'){e.preventDefault();saveResource(e.target);return;}
  if(e.target.id==='entity-form'){e.preventDefault();saveEntity(e.target);return;}
  if(e.target.id==='schedule-form'){
    e.preventDefault();const data=Object.fromEntries(new FormData(e.target)),p=processById(e.target.dataset.id);
    if(!data.pc||data.pc!=='Auto'&&!pcs.some(pc=>pc.name===data.pc&&!pc.disabled&&!pc.removed)){showToast('Chọn PC khả dụng hoặc Auto.');return;}
    data.scheduleVersion=Number(data.scheduleVersion||p.version);Object.assign(p,data);if(p.frequency==='manual')p.enabled=false;
    modalRoot.innerHTML='';render();showToast('Đã lưu Schedule. '+(p.enabled?'Lịch tiếp tục hoạt động.':'Bấm Start để bật lịch.'));
  }else if(e.target.id==='run-form'){
    e.preventDefault();const data=Object.fromEntries(new FormData(e.target));let input;
    try{input=JSON.parse(data.input);}catch{document.getElementById('run-error').textContent='Input phải là JSON hợp lệ.';return;}
    const p=processById(e.target.dataset.id),pc=data.pc==='Auto'?pcs.find(availablePc)?.name:data.pc;
    if(!pc||!pcs.some(x=>x.name===pc&&availablePc(x))){document.getElementById('run-error').textContent='Không có PC online.';return;}
    runs.unshift({id:'R-'+nextRunId++,process:p.id,status:'running',progress:0,pc,source:'Manual',startedAt:new Date().toISOString(),endedAt:null,started:new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date()),version:p.version,graphSnapshot:structuredClone(graphs[p.id]),input,logs:['Người vận hành tạo run thủ công.','Bắt đầu task đầu tiên trong bản mô phỏng.']});
    modalRoot.innerHTML='';navigate('runs');showToast('Đã tạo run mẫu. Có thể theo dõi và Cancel run.');
  }
});
document.addEventListener('change',e=>{
  const runFilters={'run-project-filter':'project','run-process-filter':'process','run-from':'from','run-to':'to','runs-page-size':'pageSize'};
  if(e.target.id==='run-status-filter'||runFilters[e.target.id]){
    const id=e.target.id;
    if(id==='run-status-filter')state.runFilter=e.target.value;
    else runListView[runFilters[id]]=id==='runs-page-size'?Number(e.target.value):e.target.value;
    if(id==='run-project-filter')runListView.process='all';
    runListView.page=1;render();document.getElementById(id)?.focus();
  }
  if(e.target.closest('#project-target-form')&&e.target.name==='period')document.querySelector('#project-target-form [name=start]').value=defaultPeriod(e.target.value).start;
  if(e.target.closest('#integration-form'))resetApiTest(e.target.closest('#integration-form'));
  if(e.target.closest('#schedule-form'))updateSchedulePreview();
  if(runLogView && ['log-level','log-node','log-page-size'].includes(e.target.id)){
    if(e.target.id==='log-level')runLogView.level=e.target.value;
    if(e.target.id==='log-node')runLogView.node=e.target.value;
    if(e.target.id==='log-page-size')runLogView.pageSize=Number(e.target.value);
    runLogView.page=1;renderRunLogs();
  }
});
document.addEventListener('input',e=>{
  if(e.target.id==='run-search'){const start=e.target.selectionStart;runListView.query=e.target.value;runListView.page=1;render();const field=document.getElementById('run-search');field.focus();field.setSelectionRange(start,start);}
  if(e.target.id==='project-search'){const start=e.target.selectionStart;projectSearch=e.target.value;render();const field=document.getElementById('project-search');field.focus();field.setSelectionRange(start,start);}
  if(e.target.id==='robot-search'){const start=e.target.selectionStart;robotSearch=e.target.value;render();const input=document.getElementById('robot-search');input.focus();input.setSelectionRange(start,start);}
  if(e.target.closest('#integration-form'))resetApiTest(e.target.closest('#integration-form'));
  if(e.target.closest('#schedule-form'))updateSchedulePreview();
  if(e.target.id==='log-search'&&runLogView){runLogView.query=e.target.value;runLogView.page=1;renderRunLogs();}
});
// Keep PC hints outside scrollable tables so long node/hardware details are not clipped.
const pcTooltip=document.createElement('div');pcTooltip.id='pc-tooltip';pcTooltip.className='pc-tooltip';pcTooltip.setAttribute('role','tooltip');pcTooltip.hidden=true;document.body.append(pcTooltip);
let pcTooltipTarget=null;
function hidePcTooltip(){pcTooltipTarget?.removeAttribute('aria-describedby');pcTooltipTarget=null;pcTooltip.hidden=true;}
function showPcTooltip(target){
  if(!target)return;hidePcTooltip();pcTooltipTarget=target;target.setAttribute('aria-describedby','pc-tooltip');pcTooltip.textContent=target.dataset.tooltip;pcTooltip.hidden=false;
  const rect=target.getBoundingClientRect(),width=pcTooltip.offsetWidth,height=pcTooltip.offsetHeight;
  pcTooltip.style.left=Math.max(12,Math.min(rect.left,innerWidth-width-12))+'px';
  pcTooltip.style.top=Math.max(12,Math.min(rect.top>height+16?rect.top-height-8:rect.bottom+8,innerHeight-height-12))+'px';
}
document.addEventListener('pointerover',e=>{const target=e.target.closest('.pc-metric');if(target&&!target.contains(e.relatedTarget))showPcTooltip(target);});
document.addEventListener('pointerout',e=>{if(pcTooltipTarget&&!pcTooltipTarget.contains(e.relatedTarget))hidePcTooltip();});
document.addEventListener('focusin',e=>{const target=e.target.closest('.pc-metric');if(target)showPcTooltip(target);});
document.addEventListener('focusout',e=>{if(e.target===pcTooltipTarget)hidePcTooltip();});
document.addEventListener('scroll',hidePcTooltip,true);window.addEventListener('resize',hidePcTooltip);
document.addEventListener('keydown',e=>{if(e.key==='Escape')hidePcTooltip();});
let drag=null;
document.addEventListener('click',e=>{if(!e.target.closest('.process-action-menu,.process-menu-trigger'))closeProcessMenu();});
document.addEventListener('scroll',closeProcessMenu,true);window.addEventListener('resize',closeProcessMenu);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeProcessMenu();});
app.addEventListener('dragstart',e=>{const source=e.target.closest('.robot-source');if(source)e.dataTransfer.setData('application/agentcf-robot',source.dataset.robot);});
app.addEventListener('dragover',e=>{if(e.target.closest('.canvas')&&[...e.dataTransfer.types].includes('application/agentcf-robot'))e.preventDefault();});
app.addEventListener('drop',e=>{
  const robot=e.dataTransfer.getData('application/agentcf-robot');if(!robot||!e.target.closest('.canvas'))return;e.preventDefault();
  const area=app.querySelector('.review-flow'),rect=area.getBoundingClientRect();
  robotNodeDialog(robot,'',{x:Math.max(10,Math.min(area.clientWidth-230,(e.clientX-rect.left)/state.zoom)),y:Math.max(10,Math.min(400,(e.clientY-rect.top)/state.zoom))});
});
app.addEventListener('pointerdown',e=>{
  const el=e.target.closest('.review-node');if(!el||e.button!==0)return;
  const n=builderNodes().find(x=>x.id===el.dataset.node);
  drag={el,n,startX:e.clientX,startY:e.clientY,x:n.x,y:n.y,moved:false};el.setPointerCapture(e.pointerId);
});
app.addEventListener('pointermove',e=>{
  if(!drag)return;const dx=(e.clientX-drag.startX)/state.zoom,dy=(e.clientY-drag.startY)/state.zoom;
  if(Math.abs(dx)+Math.abs(dy)<4&&!drag.moved)return;drag.moved=true;
  const area=drag.el.closest('.review-flow');drag.n.x=Math.max(10,Math.min(area.clientWidth-drag.el.offsetWidth-10,drag.x+dx));drag.n.y=Math.max(10,Math.min(550-drag.el.offsetHeight,drag.y+dy));
  drag.el.style.left=drag.n.x+'px';drag.el.style.top=drag.n.y+'px';drawEdges();
});
app.addEventListener('pointerup',()=>{if(!drag)return;state.selectedNode=drag.n.id;drag=null;render();});
app.addEventListener('pointercancel',()=>{drag=null;});
app.addEventListener('keydown',e=>{const node=e.target.closest('.review-node');if(node&&(e.key==='Enter'||e.key===' ')){e.preventDefault();state.selectedNode=node.dataset.node;render();}});
document.getElementById('menuButton').onclick=()=>document.body.classList.add('sidebar-open');
document.getElementById('sidebarClose').onclick=()=>document.body.classList.remove('sidebar-open');
document.getElementById('sidebarScrim').onclick=()=>document.body.classList.remove('sidebar-open');
document.getElementById('searchTrigger').onclick=openPalette;
document.getElementById('commandInput').oninput=e=>renderPalette(e.target.value);
document.getElementById('commandInput').onkeydown=e=>{if(e.key==='Enter')document.querySelector('#paletteContent [data-route]')?.click();};
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openPalette();}if(e.key==='Escape'){modalRoot.innerHTML='';closePalette();document.body.classList.remove('sidebar-open');}});
document.querySelectorAll('[data-icon]').forEach(el=>{el.innerHTML=icon(el.dataset.icon);});
const initial=new URLSearchParams(location.hash.slice(1));
if(titles[initial.get('page')])state.route=initial.get('page');
else if(titles[location.hash.slice(1)])state.route=location.hash.slice(1);
if(projectById(initial.get('project')))state.project=initial.get('project');
if(processById(initial.get('process'))){state.process=initial.get('process');state.project=currentProcess().project;}
initializeRoles();
initializeRobotUI();
initializeProjectUI();
render();

