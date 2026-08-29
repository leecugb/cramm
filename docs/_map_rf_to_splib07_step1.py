# Map every rf.json reference spectrum (splib06b record) to splib07 records.
# Step 1: dump splib06b rec# -> title for all rf.json rules.
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cramm.classifier import MicaClassifier

d = json.load(open(r"d:\CRAMM\cramm\data\rf.json"))
rules = d["rf"]

c = MicaClassifier.from_paths()
dic = c.dic3.set_index("irecno")

for name in rules:
    rec = rules[name]["reference"]["reflectance_record"]
    wav = rules[name]["reference"]["wavelength_record"]
    title = dic.loc[rec, "ititl"].strip() if rec in dic.index else "?? NOT IN dic3 ??"
    wtitle = dic.loc[wav, "ititl"].strip() if wav in dic.index else "??"
    print(f"{name:38s} rec={str(rec):<7s} wav={str(wav):<5s} | {title}  [wav: {wtitle}]")
