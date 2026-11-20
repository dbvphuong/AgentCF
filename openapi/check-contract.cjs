const fs = require('fs');
const path = require('path');
const modules = path.resolve(process.argv[2] || 'runtime/design-review/node/node_modules');
const YAML = require(path.join(modules, 'yaml'));
const Parser = require(path.join(modules, '@apidevtools/swagger-parser'));
const Ajv = require(path.join(modules, 'ajv/dist/2020'));
const formats = require(path.join(modules, 'ajv-formats'));

(async () => {
  const doc = YAML.parse(fs.readFileSync('openapi/openapi.yaml', 'utf8'));
  await Parser.validate('openapi/openapi.yaml');
  const ajv = new Ajv({ strict: false, allErrors: true });
  formats(ajv);
  const root = { $id: 'urn:agent-cf:contract', components: doc.components };
  ajv.addSchema(root);
  for (const name of Object.keys(doc.components.schemas)) {
    ajv.compile({ $ref: `urn:agent-cf:contract#/components/schemas/${name}` });
  }
  let count = 0;
  const examples = JSON.parse(fs.readFileSync('openapi/examples/foundation-cases.json', 'utf8'));
  for (const c of examples.schema_cases) {
    const validate = ajv.compile({ $ref: `urn:agent-cf:contract#/components/schemas/${c.schema}` });
    const valid = validate(c.value);
    if (valid !== c.valid) throw Error(`${c.name}: ${JSON.stringify(validate.errors)}`);
    count++;
  }
  // Structural review assertions only, not a production graph validator.
  let graphCount = 0;
  for (const c of examples.graph_cases) {
    const ids = new Set(c.definition.tasks.map(x => x.id));
    const indeg = new Map([...ids].map(x => [x, 0]));
    let valid = ids.size === c.definition.tasks.length;
    for (const e of c.definition.dependencies) {
      if (!ids.has(e.source_task_id) || !ids.has(e.target_task_id)) { valid=false; break; }
      indeg.set(e.target_task_id, indeg.get(e.target_task_id)+1);
    }
    const q=[...ids].filter(x=>indeg.get(x)===0); let visited=0;
    while(q.length) {const v=q.shift();visited++; for(const e of c.definition.dependencies.filter(e=>e.source_task_id===v)) {indeg.set(e.target_task_id,indeg.get(e.target_task_id)-1);if(indeg.get(e.target_task_id)===0)q.push(e.target_task_id);}}
    valid=valid && visited===ids.size;
    if(valid!==c.valid)throw Error(`${c.name}: unexpected graph review result`);
    graphCount++;
  }
  const ids = new Set();
  for (const [p, methods] of Object.entries(doc.paths)) for (const [method, op] of Object.entries(methods)) {
    if (ids.has(op.operationId)) throw Error('Duplicate operationId'); ids.add(op.operationId);
    if (p.startsWith('/internal/') && op['x-required-scope']!=='engine') throw Error('Internal scope missing');
    if (['post','put','delete'].includes(method) && op['x-required-scope']!=='pairing_code' && !op.parameters.some(x=>x.name==='Idempotency-Key')) throw Error('Mutation key missing');
  }
  console.log(JSON.stringify({openapi:'passed',schemas_compiled:Object.keys(doc.components.schemas).length,schema_cases:count,graph_review_cases:graphCount,paths:Object.keys(doc.paths).length,operations:ids.size}));
})().catch(e => {console.error(e); process.exit(1);});
