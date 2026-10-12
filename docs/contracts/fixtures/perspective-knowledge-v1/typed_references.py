"""Declared PK-01 wire edges only. This fixture utility grants no lookup API."""
import copy

EDGES={
 'origin':{}, 'source':{'origin':'origin'}, 'prefix':{'origin':'origin'},
 'evidence':{'origin':'origin','source':'source','prefix':'prefix'},
 'certificate':{'source':'source','witnesses.*':'evidence'},
 'fact':{'evidence.*':'evidence','certificate':'certificate'},
 'starting':{'origin':'origin','source':'source','parent':'starting','facts.*':'fact','crosswalk.*.certificate':'certificate'},
 'current':{'origin':'origin','prefix':'prefix','parent':'current','facts.*':'fact'},
 'request':{'origin':'origin','source':'source','prefix':'prefix','facts.*':'fact'},
 'knowledge':{'origin':'origin','starting':'starting','current':'current','request':'request'},
 'profile':{}, 'verdict':{'knowledge':'knowledge','profile':'profile'},
 'boundary':{'origin':'origin','parent':'boundary','restored_from':'boundary','bindings.*.knowledge':'knowledge','bindings.*.verdict':'verdict'},
 'binding':{'origin':'origin','input_knowledge':'knowledge','successor_knowledge':'knowledge'},
 'audit':{'origin':'origin','required_profile':'profile','target_boundary':'boundary'},
 'projection':{},
}
EXTERNAL={
 'boundary':['bindings.*.observation_id','bindings.*.belief_id','bindings.*.actor_record_id'],
 'binding':['input_observation','successor_observation','input_belief','successor_belief','transition','actor_record'],
 'projection':['required_profile'],
}


def map_edges(row,transform):
    result=copy.deepcopy(row)
    def descend(node,parts,target):
        key=parts[0]
        if key=='*':
            for index in range(len(node)):
                if len(parts)==1:
                    if node[index] is not None: node[index]=transform(node[index],target)
                else: descend(node[index],parts[1:],target)
        elif key in node:
            if len(parts)==1:
                if node[key] is not None: node[key]=transform(node[key],target)
            else: descend(node[key],parts[1:],target)
    for path,target in EDGES[row['kind']].items(): descend(result,path.split('.'),target)
    return result


def declared_edges(row):
    found=[]
    map_edges(row,lambda ident,kind: found.append((ident,kind)) or ident)
    return found
