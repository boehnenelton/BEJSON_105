// usage: node drv_ts.js <compiledDir> <corpus> [104]
const fs=require('fs'),path=require('path');
const dir=process.argv[2],corpus=process.argv[3],only104=process.argv[4]==='104';
const V=require(path.join(dir,'lib_bejson_Core_bejson_validators.js'));
const MV=require(path.join(dir,'lib_bejson_Core_mfdb_validators.js'));
const keep=k=>!only104||k.startsWith('104')||k==='bad_version';
let bad=0,n=0;
const exp=JSON.parse(fs.readFileSync(corpus+'/validate_expected.json'));
for(const k of Object.keys(exp)){ if(!keep(k))continue; n++;
  const doc=JSON.parse(fs.readFileSync(`${corpus}/validate/${k}.json`));
  const r=V.validateDocument(doc); const e=exp[k]; const p=[];
  if(r.valid!==e.valid)p.push(`valid ${r.valid} != ${e.valid}`);
  if(!e.valid===false && (r.warnings.length>0)!==(e.warnings>0))p.push(`warnings ${r.warnings.length} vs ${e.warnings}`);
  if(p.length){bad++;console.log('DIFF validate',k,p.join('; '),'|',(r.errors[0]||{}).message);}
}
const mexp=JSON.parse(fs.readFileSync(corpus+'/mfdb_expected.json'));
for(const k of Object.keys(mexp)){ if(!keep(k))continue; n++;
  const root=path.join(corpus,'mfdb',k); const mp=path.join(root,'104a.mfdb.bejson');
  const man=JSON.parse(fs.readFileSync(mp)); const names=man.Fields.map(f=>f.name);
  const ents=new Map(); const resolved=new Set();
  for(const row of man.Values){ const fp=row[names.indexOf('file_path')]; if(!fp) continue;
    const ep=path.join(root,fp); if(fs.existsSync(ep)){ents.set(fp,JSON.parse(fs.readFileSync(ep)));resolved.add(fp);} }
  const r=MV.validateDatabase(man,ents,{resolvedPaths:resolved,manifestRelativePath:path.basename(mp)}); const e=mexp[k]; const p=[];
  if(r.valid!==e.valid)p.push(`valid ${r.valid} != ${e.valid}`);
  if((r.warnings.length>0)!==(e.warnings>0))p.push(`warnings ${r.warnings.length} vs ${e.warnings}`);
  { const codes=[...new Set(r.errors.map(x=>String(x.code)))].sort(); if(!e.valid&&e.codes.length&&JSON.stringify(codes)!==JSON.stringify(e.codes))p.push(`codes ${codes} vs ${e.codes}`); }
  if(p.length){bad++;console.log('DIFF mfdb',k,p.join('; '),'|',(r.errors[0]||{}).message);}
}
console.log(`${n} cases, ${bad} differences`);
