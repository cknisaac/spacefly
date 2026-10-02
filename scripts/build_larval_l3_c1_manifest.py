"""Build the immutable anatomy-only Candidate L3 subgraph manifest."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'data/raw/larval_l1em/candidate_l3_c1_audit.json'
OUT=ROOT/'configs/larval_l3_c1_subgraph_manifest_v1.json'
a=json.loads(AUDIT.read_text(encoding='utf-8'))
archive_sha=a['archive_sha256']
roles={**{i:'DAN-c1' for i in a['ids_by_role']['DAN-c1']},**{i:'MBON-c1' for i in a['ids_by_role']['MBON-c1']}}
for e in a['KC_to_MBONc1_edges']: roles[e['pre_id']]='KC'
dn_edges=[]
for pre,rows in a['MBONc1_direct_descending_edges'].items():
 for e in rows:
  if e['celltype']=='DN-VNC' and e['label']=='CN-28; PL-17':
   roles[e['post_id']]='DN-VNC CN-28/PL-17'
   dn_edges.append({'pre_id':int(pre),'post_id':e['post_id'],'contacts':e['contacts']})
nodes=[]
for sid,role in sorted(roles.items()):
 if sid in a['ids_by_role']['DAN-c1']: label='DAN-c1'
 elif sid in a['ids_by_role']['MBON-c1']: label='MBON-c1; CN-59'
 else: label=None
 nodes.append({'source_id':sid,'role':role,'annotation':label or role,'transmitter':('dopamine' if role=='DAN-c1' else 'acetylcholine' if role=='MBON-c1' else 'UNKNOWN'),'transmitter_evidence':('LITERATURE-CONSTRAINED; transmitter class does not determine postsynaptic effect' if role in ('DAN-c1','MBON-c1') else 'UNKNOWN'),'physiological_output_sign':'UNKNOWN','evidence_source':'Winding et al. 2023 S1 annotations; MBON-c1 identity also cross-referenced to FlyBase FBbt:00047967'})
edges=[]
for e in a['KC_to_MBONc1_edges']:
 edges.append({'pre_id':e['pre_id'],'post_id':e['post_id'],'contacts':e['contacts'],'direction':'KC_to_MBON-c1','anatomical_status':'MEASURED','plasticity_candidate':'INFERRED: whole-cell KC→MBON-c1 pairs; LP-specific plastic contacts are not resolved in S1','physiological_sign':'UNKNOWN','source':'Supplementary-Data-S1/ad_connectivity_matrix.csv'})
for e in a['DANc1_to_MBON_edges']:
 if e['post_role']=='MBON-c1': edges.append({'pre_id':e['pre_id'],'post_id':e['post_id'],'contacts':e['contacts'],'direction':'DAN-c1_to_MBON-c1','anatomical_status':'MEASURED','plasticity_candidate':'fixed/modulatory pathway; not modeled as ordinary chemical current','physiological_sign':'UNKNOWN','source':'Supplementary-Data-S1/ad_connectivity_matrix.csv'})
for e in dn_edges:
 edges.append({'pre_id':e['pre_id'],'post_id':e['post_id'],'contacts':e['contacts'],'direction':'MBON-c1_to_DN-VNC-CN28-PL17','anatomical_status':'MEASURED','plasticity_candidate':'fixed downstream','physiological_sign':'UNKNOWN','source':'Supplementary-Data-S1/ad_connectivity_matrix.csv'})
manifest={'manifest_id':'larval_l3_dan-c1_mbon-c1_v1','candidate_status':'anatomy_pass_model_design_candidate','dataset':'L1 Larval CNS / Winding et al. 2023 Supplementary Data S1','source_stage':'first-instar connectome; functional DAN-c1 study third-instar','source_inputs':{'data/raw/larval_l1em/supplementary_data_s1.zip':archive_sha,'data/raw/larval_l1em/candidate_l3_c1_audit.json':hashlib.sha256(AUDIT.read_bytes()).hexdigest().upper()},'nodes':nodes,'edges':edges,'boundary_overlays':[{'name':'current_visible_position_to_KC','category':'ENGINEERING ASSUMPTION','topology_edit':False,'description':'Fixed causal position-bin input; no future note timestamp or time-to-contact.'},{'name':'DN-VNC-CN28-PL17_to_KEY_DOWN','category':'ENGINEERING OVERLAY','topology_edit':False,'description':'Candidate direct descending cell is mapped to an action by a fixed readout; this is not a measured fly-to-key correspondence.'},{'name':'task_outcome_to_DAN-c1_teaching','category':'ENGINEERING ASSUMPTION','topology_edit':False,'description':'Artificial task teaching interface; reward and DAN activity remain separately logged.'}],'limits':['The original L1 γ1pedc/MBON-m1 pairing is rejected; L3 uses the lower-peduncle DAN-c1 / MBON-c1 anatomical pairing.','KC→MBON-c1 memory storage remains an INFERRED hypothesis, not a direct physiological measurement.','Whole-cell S1 partners do not localize each KC contact to LP.','All physiological output signs/effects remain UNKNOWN unless explicitly constrained in a later sourced model.','First-instar anatomy and third-instar behavior are not stage matched.','The DN-VNC-to-action interface is an engineering overlay.']}
OUT.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(f'{OUT.relative_to(ROOT)}: {len(nodes)} nodes, {len(edges)} edge rows; sha256 {hashlib.sha256(OUT.read_bytes()).hexdigest()}')
