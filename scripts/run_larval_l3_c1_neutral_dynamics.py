"""Deterministic no-learning neutral check for larval L3 electrical v1."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_b.neurons import LIFParameters
from project_b.synapses import SparseGraph,Synapse
from project_b.simulation import SpikingSimulator
mp=ROOT/'configs/larval_l3_c1_subgraph_manifest_v1.json';cp=ROOT/'configs/larval_l3_c1_electrical_v1.json'
m=json.loads(mp.read_text());c=json.loads(cp.read_text());ids=[n['source_id'] for n in m['nodes']];ix={v:i for i,v in enumerate(ids)}
allowed=set(c['chemical_effects']['included_directions']); w=c['chemical_effects']['weight_mV_per_contact'];delay=c['chemical_effects']['delay_us']
edges=[Synapse(ix[e['pre_id']],ix[e['post_id']],w*e['contacts'],delay) for e in m['edges'] if e['direction'] in allowed]
graph=SparseGraph(len(ids),edges);p=c['neuron_model'];pars=[LIFParameters(tau_m_us=p['tau_m_us'],tau_syn_us=p['tau_syn_us'],refractory_us=p['refractory_us']) for _ in ids]
kcs=sorted(n['source_id'] for n in m['nodes'] if n['role']=='KC');q,r=divmod(len(kcs),8);groups=[];st=0
for i in range(8):
 size=q+(i<r);groups.append(kcs[st:st+size]);st+=size
rows=[]
for state in ['baseline']+list(range(8)):
 drive=[0.0]*len(ids)
 if state!='baseline':
  for sid in groups[state]:drive[ix[sid]]=c['sensory_boundary']['drive_mV_equivalent']
 sim=SpikingSimulator(pars,graph,drive,dt_us=c['integration']['dt_us'],record_spikes=True)
 if state!='baseline':
  sim.run_until(c['sensory_boundary']['pulse_duration_us']);sim.set_external_drive_mv([0.0]*len(ids))
 sim.run_until(100000);ss=sim.snapshot();roles={role:sum(ss.spike_counts[ix[n['source_id']]] for n in m['nodes'] if n['role'].startswith(role)) for role in ['KC','MBON-c1','DN-VNC']}
 dn={str(sid):ss.spike_counts[ix[sid]] for sid in c['action_boundary']['readout_nodes']}
 rows.append({'state':state,'spikes_by_role':roles,'dn_spikes':dn,'action':sum(dn.values())>0,'total_spikes':sum(ss.spike_counts),'queue_at_end':ss.queued_arrivals,'finite':all(__import__('math').isfinite(x) for x in (*ss.voltage_mv,*ss.synaptic_drive_mv))})
out={'experiment_id':'larval_l3_c1_neutral_dynamics_v1','manifest_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),'model_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'plasticity_enabled':False,'teaching_enabled':False,'states':rows,'interpretation':'Engineering-assumption reference only; not biology or learning.'}
op=ROOT/'runs/larval_l3_c1_neutral_dynamics_v1.json';op.parent.mkdir(exist_ok=True);op.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));print('result_sha256',hashlib.sha256(op.read_bytes()).hexdigest())
