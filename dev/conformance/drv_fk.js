const fs=require('fs'),path=require('path');
const [core,corpus]=process.argv.slice(2); const MV=require(path.join(core,'lib_bejson_Core_mfdb_validator.js'));
const exp=JSON.parse(fs.readFileSync(corpus+'/fk_expected.json')); let bad=0;
for(const [k,e] of Object.entries(exp)){ const m=path.join(corpus,'fk',k,'104a.mfdb.bejson');
  const a=MV.mfdb_validator_check_referential_integrity(m).map(x=>x.code+'|'+x.entity).sort();
  const v=MV.validate_mfdb_database(m,true).valid;
  if(JSON.stringify(a)!==JSON.stringify(e.audit)||v!==e.strict_valid){bad++;console.log('DIFF fk',k,JSON.stringify(a),v,'vs',JSON.stringify(e));} }
console.log(Object.keys(exp).length+' fk cases, '+bad+' differences');
