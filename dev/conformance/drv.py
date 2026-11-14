import sys,os,json,re
core=os.path.abspath(sys.argv[1]); corpus=os.path.abspath(sys.argv[2]); only104=len(sys.argv)>3 and sys.argv[3]=="104"
sys.path.insert(0,core)
import lib_bejson_Core_bejson_validator as V
import lib_bejson_Core_mfdb_validator as MV
exp=json.load(open(corpus+"/validate_expected.json")); bad=0;n=0
for k,e in exp.items():
    if only104 and not k.startswith("104") and k not in("bad_version",): continue
    d=json.load(open(f"{corpus}/validate/{k}.json")); r=V.validate_bejson(d,is_file=False); n+=1
    codes=sorted(set(re.findall(r"E_[A-Z_]+",' '.join(r.errors))))
    p=[]
    if r.valid!=e["valid"]: p.append(f"valid {r.valid}!={e['valid']}")
    if (len(r.warnings)>0)!=(e["warnings"]>0): p.append("warnings")
    if p: bad+=1; print("DIFF validate",k,p)
mexp=json.load(open(corpus+"/mfdb_expected.json"))
for k,e in mexp.items():
    if only104 and not k.startswith("104"): continue
    m=f"{corpus}/mfdb/{k}/104a.mfdb.bejson"; r=MV.validate_mfdb_database(m); n+=1
    codes=sorted(set(re.findall(r"Message: \[(\d+)\]",' '.join(r.errors))))
    p=[]
    if r.valid!=e["valid"]: p.append(f"valid {r.valid}!={e['valid']}")
    if (len(r.warnings)>0)!=(e["warnings"]>0): p.append(f"warnings {len(r.warnings)} vs {e['warnings']}")
    if not e["valid"] and e["codes"] and codes!=e["codes"]: p.append(f"codes {codes} vs {e['codes']}")
    if p: bad+=1; print("DIFF mfdb",k,p)
print(n,"cases,",bad,"differences")
