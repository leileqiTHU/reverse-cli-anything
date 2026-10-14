"""Validate the documented JSON Schema subset used by the tool argument catalog."""
import math
import re

def validate(value, schema, path='$'):
    def fail(message):raise ValueError(path+': '+message)
    if 'const' in schema and value!=schema['const']:fail('unexpected constant')
    if 'enum' in schema and value not in schema['enum']:fail('value is not in enum')
    if 'type' in schema:
        matches={'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),
                 'boolean':type(value) is bool,'integer':type(value) is int,'number':type(value) in (int,float),'null':value is None}
        if not matches[schema['type']]:fail('expected '+schema['type'])
    if type(value) in (int,float):
        if not math.isfinite(value):fail('number must be finite')
        if 'minimum' in schema and value<schema['minimum']:fail('below minimum')
        if 'maximum' in schema and value>schema['maximum']:fail('above maximum')
    if isinstance(value,str) and 'pattern' in schema and not re.search(schema['pattern'],value):fail('pattern mismatch')
    if isinstance(value,dict):
        for k in schema.get('required',[]):
            if k not in value:fail('missing '+k)
        props=schema.get('properties',{})
        for k,v in value.items():
            if k in props:validate(v,props[k],path+'.'+k)
            elif schema.get('additionalProperties') is False:fail('unknown property '+k)
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',float('inf')):fail('invalid array length')
        for i,v in enumerate(value):validate(v,schema.get('items',{}),path+f'[{i}]')
    def accepts(branch):
        try:validate(value,branch,path);return True
        except ValueError:return False
    for branch in schema.get('allOf',[]):validate(value,branch,path)
    if 'anyOf' in schema and not any(accepts(b) for b in schema['anyOf']):fail('no anyOf alternative matches')
    if 'oneOf' in schema and sum(accepts(b) for b in schema['oneOf'])!=1:fail('expected exactly one alternative')
    if 'not' in schema and accepts(schema['not']):fail('forbidden combination')
