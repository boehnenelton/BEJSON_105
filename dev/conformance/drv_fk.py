import sys,json
core,corpus=sys.argv[1],sys.argv[2]; sys.path.insert(0,core)
import lib_bejson_Core_mfdb_validator as MV
exp=json.load(open(corpus+"/fk_expected.json")); bad=0
for k,e in exp.items():
    m=f"{corpus}/fk/{k}/104a.mfdb.bejson"
    a=sorted(x["code"]+"|"+str(x["entity"]) for x in MV.mfdb_validator_check_referential_integrity(m))
    v=MV.validate_mfdb_database(m,strict_fk=True).valid
    if a!=e["audit"] or v!=e["strict_valid"]: bad+=1; print("DIFF fk",k,a,v,"vs",e)
print(len(exp),"fk cases,",bad,"differences")
