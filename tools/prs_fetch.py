import json,re,html,time,sys,pathlib,urllib.request
ROOT=pathlib.Path("documents/finance")
STATES={"AP":"andhra-pradesh","AR":"arunachal-pradesh","AS":"assam","BR":"bihar","CG":"chhattisgarh","DL":"delhi","GA":"goa","GJ":"gujarat","HR":"haryana","HP":"himachal-pradesh","JK":"jammu-and-kashmir","JH":"jharkhand","KA":"karnataka","KL":"kerala","MP":"madhya-pradesh","MH":"maharashtra","MN":"manipur","ML":"meghalaya","MZ":"mizoram","NL":"nagaland","OD":"odisha","PY":"puducherry","PB":"punjab","RJ":"rajasthan","SK":"sikkim","TN":"tamil-nadu","TS":"telangana","TR":"tripura","UP":"uttar-pradesh","UK":"uttarakhand","WB":"west-bengal"}
res={}
for st,slug in STATES.items():
    url=f"https://prsindia.org/budgets/states/{slug}-budget-analysis-2026-27"
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
        raw=urllib.request.urlopen(req,timeout=30).read().decode("utf8","replace")
    except Exception as e:
        res[st]=f"FAILED {type(e).__name__} {e}"[:90]; continue
    body=re.sub(r"(?is)<(script|style|nav|footer|header)\b.*?</\1>"," ",raw)
    a=body.find("Budget Analysis"); 
    body=re.sub(r"(?i)</(p|div|li|h\d|tr)>","\n",body); body=re.sub(r"(?i)</t[dh]>"," | ",body); body=re.sub(r"<[^>]+>"," ",body)
    lines=[re.sub(r"[ \t\xa0]+"," ",html.unescape(l)).strip() for l in body.split("\n")]
    lines=[l for l in lines if l and l!="|"]
    s=next((n for n,l in enumerate(lines) if re.match(r"(?i)(the )?finance minister|.*presented the budget|^highlights|budget highlights",l)),0)
    e=next((n for n,l in enumerate(lines) if n>s and re.match(r"(?i)^(sources?:|disclaimer|download)",l) and n>len(lines)//2),len(lines))
    text="\n".join(lines[s:e])
    d=ROOT/st; d.mkdir(parents=True,exist_ok=True)
    (d/f"prs-{slug}-budget-analysis-2026-27.txt").write_text(text,encoding="utf8")
    res[st]=len(text); time.sleep(2)
print(res)
