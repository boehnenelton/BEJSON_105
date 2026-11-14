const fs=require('fs'),path=require('path');
const [dir,corpus]=process.argv.slice(2); const MV=require(path.join(dir,'lib_bejson_Core_mfdb_validators.js'));
const exp=JSON.parse(fs.readFileSync(corpus+'/fk_expected.json')); let bad=0;
const NAMES={39:'E_MFDB_FK_UNRESOLVED',33:'E_MFDB_ENTITY_NOT_FOUND',43:'E_MFDB_FK_TARGET_ENTITY_UNKNOWN',47:'E_MFDB_FK_INVALID_ON_DELETE'};
for(const [k,e0] of Object.entries(exp)){ const e={...e0,audit:e0.audit.filter(x=>!x.startsWith('E_MFDB_ENTITY_NOT_FOUND'))}; const root=path.join(corpus,'fk',k); const mp=path.join(root,'104a.mfdb.bejson');
  const man=JSON.parse(fs.readFileSync(mp)); const names=man.Fields.map(f=>f.name); const ents=new Map(); const resolved=new Set();
  for(const row of man.Values){const fp=row[names.indexOf('file_path')]; const ep=path.join(root,fp); if(fs.existsSync(ep)){ents.set(fp,JSON.parse(fs.readFileSync(ep)));resolved.add(fp);}}
  const a=MV.checkReferentialIntegrity(man,ents).filter(x=>x.code!==33).map(x=>(NAMES[x.code]||x.code)+'|'+x.entity).sort();
  const v=MV.validateDatabase(man,ents,{resolvedPaths:resolved,manifestRelativePath:'104a.mfdb.bejson',strict:true}).valid;
  if(JSON.stringify(a)!==JSON.stringify(e.audit)||v!==e.strict_valid){bad++;console.log('DIFF fk',k,JSON.stringify(a),v,'vs',JSON.stringify(e));} }
console.log(Object.keys(exp).length+' fk cases, '+bad+' differences');
