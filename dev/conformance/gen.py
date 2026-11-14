import sys, os, json, re, shutil, uuid, copy
CORE=os.path.abspath(os.environ.get("CORE","../w/libraries_105/Lib_PY/Core")); sys.path.insert(0,CORE)
import lib_bejson_Core_bejson_validator as V
import lib_bejson_Core_mfdb_core as M
import lib_bejson_Core_mfdb_validator as MV
OUT=os.path.abspath(os.environ.get("CORPUS","corpus")); shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT+"/validate"); os.makedirs(OUT+"/mfdb")
U4=lambda:str(uuid.uuid4())
H={"Format":"BEJSON","Format_Creator":"Elton Boehnen"}
def d105(version="105",types=("T",),fields=None,values=None):
    fields=fields or [("name","string"),("age","integer")]
    fl=[{"name":n,"type":t,"field_uuid":U4()} for n,t in fields]
    return {**H,"Format_Version":version,"Records_Type":list(types),"Fields":fl,"Values":values if values is not None else [[U4(),"a",1]]}
def d105db():
    fl=[{"name":"Record_Type_Parent","type":"string","field_uuid":U4()},
        {"name":"dept","type":"string","Record_Type_Parent":"D","field_uuid":U4()},
        {"name":"emp","type":"string","Record_Type_Parent":"E","field_uuid":U4()}]
    return {**H,"Format_Version":"105db","Records_Type":["D","E"],"Fields":fl,"Values":[["D",U4(),"eng",None],["E",U4(),None,"al"]]}
def d104(version="104",types=("T",),fields=None,values=None):
    fields=fields or [("name","string"),("age","integer")]
    return {**H,"Format_Version":version,"Records_Type":list(types),"Fields":[{"name":n,"type":t} for n,t in fields],"Values":values if values is not None else [["a",1]]}
C={}
C["105_ok"]=d105(); C["105a_ok"]=d105("105a"); C["105db_ok"]=d105db()
C["104_ok"]=d104(); C["104a_ok"]=d104("104a"); 
C["104db_ok"]={**H,"Format_Version":"104db","Records_Type":["D","E"],"Fields":[{"name":"Record_Type_Parent","type":"string"},{"name":"x","type":"string","Record_Type_Parent":"D"}],"Values":[["D","v"]]}
for i,bad in enumerate(([U4(),"a"],[U4(),"a",1,9],["a",1])): C[f"105_len_{i}"]=d105(values=[bad])
C["105_type_str_in_int"]=d105(values=[[U4(),"a","x"]])
C["105_type_bool_in_int"]=d105(values=[[U4(),"a",True]])
C["105_type_bool_in_number"]=d105(fields=[("x","number")],values=[[U4(),True]])
C["105_null_ok"]=d105(values=[[U4(),None,None]])
f=[("s","string"),("i","integer"),("n","number"),("b","boolean"),("a","array"),("o","object")]
good=[U4(),"x",1,1.5,True,[1],{"k":1}]
C["105_six_ok"]=d105(fields=f,values=[good])
for col,badv in ((1,5),(2,"s"),(3,"s"),(4,"s"),(5,"s"),(6,[1])):
    b=list(good); b[col]=badv; C[f"105_six_bad_col{col}"]=d105(fields=f,values=[b])
C["105_rt_two"]=d105(types=("A","B")); C["105a_rt_two"]=d105("105a",types=("A","B")); C["105_rt_empty"]=d105(types=())
x=d105db(); x["Records_Type"]=["D"]; C["105db_rt_one"]=x
C["105a_array"]=d105("105a",fields=[("tags","array")],values=[[U4(),[1]]])
C["105a_object"]=d105("105a",fields=[("o","object")],values=[[U4(),{}]])
C["105_array_ok"]=d105(fields=[("tags","array")],values=[[U4(),[1]]])
x=d105db(); x["Fields"][1].pop("Record_Type_Parent"); C["105db_no_owner"]=x
x=d105db(); x["Fields"][0]["name"]="oops"; C["105db_first_field"]=x
x=d105db(); x["Values"][0][0]="Nope"; C["105db_bad_discriminator"]=x
x=d105db(); x["Values"][0]=[x["Values"][0][1],"D","eng",None]; C["105db_uuid_col0"]=x
x=d105db(); x["Values"][0]=["D",U4(),"eng"]; C["105db_short"]=x
x=d105db(); x["Values"][1][3]=5; C["105db_bad_type"]=x
x=d105(values=[["not-a-uuid","a",1]]); x["Fields"][0]["field_uuid"]="abc"; C["105_uuid_format_warn"]=x
C["105_dup_record_uuid"]=d105(values=[["u1","a",1],["u1","b",2]])
x=d105(); x["Fields"][1]["field_uuid"]=x["Fields"][0]["field_uuid"]; C["105_dup_field_uuid"]=x
x=d105(); x["Fields"][0].pop("field_uuid"); C["105_no_field_uuid"]=x
x=d105(); x["Fields"][1]["name"]=x["Fields"][0]["name"]; C["105_dup_name"]=x
x=d105(); x["Fields"][0]["type"]="timestamp"; C["105_bad_type"]=x
x=d105(); x["Custom"]=1; C["105_custom_header"]=x
x=d105("105a"); x["Custom"]=1; C["105a_custom_ok"]=x
x=d105(); x["_x"]=1; C["105_underscore_key"]=x
x=d105(); x["Format_Creator"]="Nobody"; C["105_bad_creator"]=x
x=d105(); x["Format_Version"]="106"; C["bad_version"]=x
C["104_len_short"]=d104(values=[["a"]]); C["104_type_bad"]=d104(values=[["a","x"]])
C["104a_array"]=d104("104a",fields=[("t","array")],values=[[[1]]])
C["104_rt_two"]=d104(types=("A","B"))
# 104 doc with 105-style row shape wrongly
C["104_with_uuid_row"]=d104(values=[[U4(),"a",1]])
flood=d105(values=[[U4(),"a","bad"] for _ in range(300)]); C["105_flood"]=flood

exp={}
for k,d in C.items():
    json.dump(d,open(f"{OUT}/validate/{k}.json","w"))
    r=V.validate_bejson(d,is_file=False)
    exp[k]={"valid":r.valid,"errors":len(r.errors),"warnings":len(r.warnings),
            "codes":sorted(set(re.findall(r"E_[A-Z_]+",' '.join(r.errors))))}
json.dump(exp,open(OUT+"/validate_expected.json","w"),indent=1)

# ---- MFDB corpus
S=lambda n:{"name":n,"type":"string"}
def jl(p): return json.load(open(p))
def jd(d,p): json.dump(d,open(p,"w"))
def make(root,fmt):
    m=M.mfdb_core_create_database(root,"Shop",[{"name":"Customer","fields":[S("cust_name")],"format_version":fmt},{"name":"Order","fields":[S("code")],"format_version":fmt}],mfdb_version="1.40")
    add=M.mfdb_core_add_entity_record_105 if fmt=="105" else M.mfdb_core_add_entity_record
    add(m,"Customer",["ann"]); add(m,"Order",["O1"]); return m
mexp={}
def case(name,fmt,mut=None):
    root=f"{OUT}/mfdb/{name}"; m=make(root,fmt)
    ent=M._get_entity_path(m,"Order")
    if mut: mut(m,ent,root)
    r=MV.validate_mfdb_database(m)
    mexp[name]={"fmt":fmt,"valid":r.valid,"warnings":len(r.warnings),"codes":sorted(set(re.findall(r"\[(\d+)\]",' '.join(r.errors))))}
def mut_rt(v):
    def f(m,e,root): d=jl(e); d["Records_Type"]=v; jd(d,e)
    return f
def mut_ph(v):
    def f(m,e,root): d=jl(e); d["Parent_Hierarchy"]=v; jd(d,e)
    return f
def mut_noph(m,e,root): d=jl(e); d.pop("Parent_Hierarchy"); jd(d,e)
def mut_other(m,e,root):
    o=make(root+"_other","105" if jl(e)["Format_Version"]=="105" else "104")
    d=jl(e); d["Parent_Hierarchy"]=os.path.relpath(o,os.path.dirname(e)); jd(d,e)
def mut_count(m,e,root):
    mf=jl(m); n=[f["name"] for f in mf["Fields"]]; mf["Values"][1][n.index("record_count")]=99; jd(mf,m)
def mut_man(kind):
    def f(m,e,root):
        mf=jl(m); n=[x["name"] for x in mf["Fields"]]; i=n.index("entity_name")
        if kind=="dup": mf["Values"][1][i]=mf["Values"][0][i]
        elif kind=="null": mf["Values"][0][i]=None
        elif kind=="missing": mf["Values"][0][n.index("file_path")]="data/missing.bejson"
        elif kind=="rt": mf["Records_Type"]=["other"]
        elif kind=="traversal": mf["Values"][0][n.index("file_path")]="../x.bejson"
        jd(mf,m)
    return f
def mut_ver(v):
    def f(m,e,root): d=jl(e); d["Format_Version"]=v; jd(d,e)
    return f
for fmt in ("104","105"):
    case(f"{fmt}_clean",fmt)
    case(f"{fmt}_rt_wrong",fmt,mut_rt(["WrongName"])); case(f"{fmt}_rt_case",fmt,mut_rt(["order"]))
    case(f"{fmt}_rt_two",fmt,mut_rt(["Order","Extra"])); case(f"{fmt}_rt_empty",fmt,mut_rt([]))
    case(f"{fmt}_no_ph",fmt,mut_noph); case(f"{fmt}_orphan",fmt,mut_ph("../nope.mfdb.bejson"))
    case(f"{fmt}_other_manifest",fmt,mut_other); case(f"{fmt}_count_drift",fmt,mut_count)
    for k in ("dup","null","missing","rt","traversal"): case(f"{fmt}_man_{k}",fmt,mut_man(k))
    case(f"{fmt}_entity_105db",fmt,mut_ver("105db")); case(f"{fmt}_entity_104a",fmt,mut_ver("104a"))
json.dump(mexp,open(OUT+"/mfdb_expected.json","w"),indent=1)

# ---- extra manifest edge cases (empty strings, nested/absolute escapes)
def mut_man2(kind):
    def f(m,e,root):
        mf=jl(m); n=[x["name"] for x in mf["Fields"]]; i=n.index("entity_name"); j=n.index("file_path")
        if kind=="empty_name": mf["Values"][0][i]=""
        elif kind=="empty_path": mf["Values"][0][j]=""
        elif kind=="nested_escape": mf["Values"][0][j]="data/../../x.bejson"
        elif kind=="absolute": mf["Values"][0][j]="/etc/x.bejson"
        elif kind=="dup_path": mf["Values"][1][j]=mf["Values"][0][j]
        elif kind=="bad_role": mf["Network_Role"]="Overlord"
        elif kind=="ok_role": mf["Network_Role"]="Standalone"
        elif kind=="abs_existing":
            ext=root+"_ext"; os.makedirs(ext,exist_ok=True); outp=os.path.join(ext,"outside.bejson")
            d=jl(e); d["Parent_Hierarchy"]=os.path.relpath(m,ext); jd(d,outp)
            mf["Values"][1][j]=outp
        jd(mf,m)
    return f
for fmt in ("104","105"):
    for k in ("empty_name","empty_path","nested_escape","absolute","abs_existing","dup_path","bad_role","ok_role"):
        case(f"{fmt}_man2_{k}",fmt,mut_man2(k))
json.dump(mexp,open(OUT+"/mfdb_expected.json","w"),indent=1)

# ---- FK audit corpus (105 only). expected = Python audit result + strict validate result
import uuid as _u
os.makedirs(OUT+"/fk",exist_ok=True); fkexp={}
def fkcase(name,mut,cust_fmt="105"):
    root=f"{OUT}/fk/{name}"
    m=M.mfdb_core_create_database(root,"Shop",[{"name":"Customer","fields":[S("cust_name")],"format_version":cust_fmt},{"name":"Order","fields":[S("code")],"format_version":"105"}],mfdb_version="1.40")
    addc=M.mfdb_core_add_entity_record_105 if cust_fmt=="105" else M.mfdb_core_add_entity_record
    addc(m,"Customer",["ann"]); addc(m,"Customer",["bob"]); M.mfdb_core_add_entity_record_105(m,"Order",["O1"]); M.mfdb_core_add_entity_record_105(m,"Order",["O2"])
    ce=jl(M._get_entity_path(m,"Customer")); oe_p=M._get_entity_path(m,"Order"); oe=jl(oe_p)
    cu=[r[0] for r in ce["Values"]] if cust_fmt=="105" else [None,None]
    oe["Fields"].append({"name":"cust_ref","type":"string","field_uuid":str(_u.uuid4()),"fk_target_entity":"Customer","fk_on_delete":"restrict"})
    for r,v in zip(oe["Values"],mut.get("vals",lambda cu:[cu[0],cu[1]])(cu)): r.append(v)
    if "field" in mut: oe["Fields"][-1].update(mut["field"])
    jd(oe,oe_p)
    if "manifest" in mut: mut["manifest"](m)
    a=MV.mfdb_validator_check_referential_integrity(m)
    r=MV.validate_mfdb_database(m,strict_fk=True)
    fkexp[name]={"audit":sorted([x["code"]+"|"+str(x["entity"]) for x in a]),"strict_valid":r.valid}
fkcase("ok",{})
fkcase("null_ok",{"vals":lambda cu:[None,None]})
fkcase("one_dangling",{"vals":lambda cu:[cu[0],"ffffffff-0000-4000-8000-000000000000"]})
fkcase("two_dangling",{"vals":lambda cu:["ffffffff-0000-4000-8000-000000000001","ffffffff-0000-4000-8000-000000000002"]})
fkcase("target_unknown",{"field":{"fk_target_entity":"Nope"}})
fkcase("bad_on_delete",{"field":{"fk_on_delete":"explode"}})
fkcase("cascade_ok",{"field":{"fk_on_delete":"cascade"}})
fkcase("null_policy_ok",{"field":{"fk_on_delete":"null"}})
fkcase("no_on_delete_defaults",{"field":{"fk_on_delete":None}})
fkcase("target_is_104",{"vals":lambda cu:["x","y"]},cust_fmt="104")
def _missing(m):
    mf=jl(m); n=[x["name"] for x in mf["Fields"]]; mf["Values"][0][n.index("file_path")]="data/missing.bejson"; jd(mf,m)
fkcase("entity_file_missing",{"manifest":_missing})
json.dump(fkexp,open(OUT+"/fk_expected.json","w"),indent=1)
print(len(fkexp),"fk cases")
print(len(exp),"validate cases;",len(mexp),"mfdb cases")
for k,v in mexp.items(): print(k,v["valid"],v["codes"],v["warnings"])
