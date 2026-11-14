const fs=require('fs'),path=require('path');
const core=process.argv[2], corpus=process.argv[3];
const V=require(path.join(core,'lib_bejson_Core_bejson_validator.js'));
const MV=require(path.join(core,'lib_bejson_Core_mfdb_validator.js'));
const only104=process.argv[4]==='104';
const keep=k=>!only104||k.startsWith('104')||k==='bad_version';
const exp=JSON.parse(fs.readFileSync(corpus+'/validate_expected.json'));
let bad=0,n=0;
for(const k of Object.keys(exp)){ if(!keep(k)) continue;
  const doc=JSON.parse(fs.readFileSync(`${corpus}/validate/${k}.json`));
  const r=V.bejson_validator_validate_object(doc); n++;
  const codes=[...new Set((r.errors.join(' ').match(/E_[A-Z_]+/g)||[]))].sort();
  const e=exp[k]; const problems=[];
  if(r.valid!==e.valid) problems.push(`valid ${r.valid} != ${e.valid}`);
  if((r.warnings.length>0)!==(e.warnings>0)) problems.push(`warnings ${r.warnings.length} vs ${e.warnings}`);
  if(!e.valid && e.codes.length && JSON.stringify(codes)!==JSON.stringify(e.codes)) problems.push(`codes ${codes} vs ${e.codes}`);
  if(problems.length){bad++;console.log('DIFF validate',k,problems.join('; '),'|',r.errors.slice(0,2).join(' // '));}
}
const mexp=JSON.parse(fs.readFileSync(corpus+'/mfdb_expected.json'));
for(const k of Object.keys(mexp)){ if(!keep(k)) continue;
  const m=path.join(corpus,'mfdb',k,'104a.mfdb.bejson');
  let r; n++;
  if (MV.validate_mfdb_database) r=MV.validate_mfdb_database(m);
  else { let code=null,valid=true; try{MV.mfdb_validator_validate_database(m);}catch(e){valid=false;code=e.code;}
    r={valid,errors:(MV.mfdb_validator_get_errors?MV.mfdb_validator_get_errors():[]).map(x=>String(x)),warnings:MV.mfdb_validator_get_warnings?MV.mfdb_validator_get_warnings():[],thrown:code}; }
  let codes=[...new Set((r.errors.join(' ').match(/Message: \[(\d+)\]/g)||[]).map(s=>s.replace("Message: [","").replace("]","")))].sort();
  if(r.thrown!=null) codes=[String(r.thrown)];
  const e=mexp[k]; const problems=[];
  if(r.valid!==e.valid) problems.push(`valid ${r.valid} != ${e.valid}`);
  if((r.warnings.length>0)!==(e.warnings>0)) problems.push(`warnings ${r.warnings.length} vs ${e.warnings}`);
  if(!e.valid && e.codes.length && JSON.stringify(codes)!==JSON.stringify(e.codes)) problems.push(`codes ${codes} vs ${e.codes}`);
  if(problems.length){bad++;console.log('DIFF mfdb',k,problems.join('; '),'|',r.errors.slice(0,2).join(' // '));}
}
console.log(`${n} cases, ${bad} differences`);
