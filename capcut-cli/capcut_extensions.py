"""Three bounded native editing extensions with durable mutation receipts."""
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import time
import uuid

ROOT = Path(__file__).resolve().parent
ACTIONS = ('add-audio', 'captions-import', 'set-clip')


def caption_timing_matches(actual, cue):
    """Native fractional-frame timestamps can round by one microsecond."""
    expected={'start':cue['startUs'],'duration':cue['endUs']-cue['startUs']}
    return set(actual)==set(expected) and all(
        isinstance(actual[key],int) and not isinstance(actual[key],bool)
        and abs(actual[key]-value)<=1 for key,value in expected.items())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def file_digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def content_literal(text):
    # gen_patch has its own string grammar after argv parsing: escape-next-char,
    # not JSON escapes. Keep LF/tab literal; quote and escape backslashes/quotes.
    return '"'+text.replace('\\','\\\\').replace('"','\\"')+'"'


def read_json(path, limit=16384):
    from capcut_clip_properties import _unique_object, _invalid_constant
    with Path(path).open('rb') as stream: raw=stream.read(limit+1)
    if len(raw) > limit:
        raise ValueError('JSON input exceeds the size limit')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)


def segment(doc, identity):
    matches = [(t, s) for t in doc['tracks'] for s in t['segments'] if s['id'].lower() == identity.lower()]
    if len(matches) != 1:
        raise ValueError('Requested segment is not uniquely present in this timeline')
    return matches[0]


def prepare(args, doc):
    """Validate all static fields before the worker can write anything."""
    from capcut_captions import load_captions, normalize_style
    from capcut_clip_properties import load_patch_file, normalize_patch
    request_id = args.request_id or uuid.uuid4().hex
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', request_id):
        raise ValueError('--request-id must be 1..96 ASCII letters, digits, dots, hyphens or underscores')
    if request_id.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'{p}{n}' for p in ('COM','LPT') for n in range(1,10)]}:
        raise ValueError('--request-id cannot be a Windows device name')
    data = {'request_id': request_id}
    if args.editor_action == 'add-audio':
        from capcut_media import _local_path
        source = _local_path(args.input, 'Audio input')
        if not source.is_file():
            raise ValueError('Audio input does not exist')
        for key in ('start_us', 'source_in_us'):
            value = getattr(args, key)
            if not 0 <= value < 2**53:
                raise ValueError(key+' must be a nonnegative safe integer')
        if args.duration_us <= 0 or args.duration_us + args.start_us > doc['duration']:
            raise ValueError('Audio target range must fit within the existing timeline')
        patch = {}
        for name, key in [('volume_linear','volumeLinear'),('gain_db','gainDb'),('fade_in_us','fadeInUs'),('fade_out_us','fadeOutUs')]:
            value = getattr(args, name)
            if value is not None: patch[key] = value
        if patch: patch = normalize_patch(patch, 'audio')
        if patch.get('fadeInUs', 0) + patch.get('fadeOutUs', 0) > args.duration_us:
            raise ValueError('Audio fades exceed duration')
        data.update(input=str(source), input_sha256=file_digest(source),
                    start_us=args.start_us, duration_us=args.duration_us, source_in_us=args.source_in_us, patch=patch)
    elif args.editor_action == 'captions-import':
        cues = load_captions(args.input, args.format, args.offset_us, doc['duration'], doc['fps'])
        # Native typography uses a CapCut size number, not pixels. Lower third defaults.
        style = {'size': 8, 'color': '0xFFFFFF', 'outlineColor': '0x000000', 'outlineWidth': 0.04}
        incoming = read_json(args.style) if args.style else {}
        if not isinstance(incoming,dict):raise ValueError('Caption style must be a JSON object')
        position = {key: incoming.pop(key) for key in ('xRatio','yRatio') if key in incoming}
        for key, value in position.items():
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not -1 <= value <= 1 or not math.isfinite(value):
                raise ValueError('Caption positions must be finite normalized coordinates in [-1,1]')
        if 'font' in incoming:
            raise ValueError('Font resource selection is not verified; this release uses the native default font')
        style.update(normalize_style(incoming))
        data.update(cues=cues, style=style, position={'xRatio': position.get('xRatio',0), 'yRatio':position.get('yRatio',-0.75)})
    else:
        track, clip = segment(doc, str(uuid.UUID(args.segment)))
        data.update(segment_id=clip['id'], patch=load_patch_file(args.patch, track['type']))
    return data


class MutationError(ValueError):
    def __init__(self, message, details, preserve=False):
        super().__init__(message)
        self.details = details
        self.preserve_pid_lock = preserve


def write_record(path, value):
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf8') as out:
        out.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False));out.flush()
        import os
        os.fsync(out.fileno())
    temp.replace(path)


def signature(doc):
    from capcut_export import export_content_signature
    return hashlib.sha256(canonical(export_content_signature(doc)).encode()).hexdigest()


def replay_signature(doc, identities):
    """Bind receipts to affected objects while tolerating native identity-cache fills."""
    materials={m['id']:(kind,m) for kind,values in doc['materials'].items() if isinstance(values,list)
               for m in values if isinstance(m,dict) and 'id' in m}
    records=[]
    for identity in identities:
        track,clip=segment(doc,identity)
        bound={'track':{k:v for k,v in track.items() if k not in ('segments','track_render_index')},
               'clip':{k:v for k,v in clip.items() if k!='track_render_index'},'materials':{}}
        for ref in [clip['material_id'],*clip.get('extra_material_refs',[])]:
            if ref not in materials:continue
            kind,value=materials[ref];value=copy.deepcopy(value)
            if kind in ('videos','audios'):value.pop('unique_id',None)
            if kind=='sound_channel_mappings' and value.get('type')=='':value['type']='none'
            bound['materials'][ref]=value
        records.append(bound)
    return hashlib.sha256(canonical(records).encode()).hexdigest()


def close_number(actual, expected):
    return isinstance(actual,(int,float)) and abs(actual-expected) <= max(1e-5,abs(expected)*1e-5)


def property_expected(patch, old):
    expected = copy.deepcopy(old)
    if 'crop' in patch: expected.pop('cropCorners',None)
    for key,value in patch.items():
        if key == 'gainDb': expected['volumeLinear'] = 10 ** (value/20)
        elif key == 'transform': expected.setdefault(key,{}).update(value)
        else: expected[key] = value
    return expected


def require_properties(actual, expected, label='properties'):
    if not isinstance(actual,dict):raise ValueError(f'{label} is missing or has the wrong type')
    for key,value in expected.items():
        if key not in actual: raise ValueError(f'Missing {label}.{key}')
        if isinstance(value,dict): require_properties(actual[key],value,label+'.'+key)
        elif isinstance(value,(int,float)):
            if not close_number(actual[key],value): raise ValueError(f'{label}.{key}: expected {value}, saved {actual[key]}')
        elif actual[key] != value: raise ValueError(f'{label}.{key} did not match')


def verify_target_preserved(before_doc,after_doc,identity,patch):
    """Protect target content outside the explicit setter paths as well as neighbors."""
    before_track,before=segment(before_doc,identity);after_track,after=segment(after_doc,identity)
    track_metadata=lambda t:{k:v for k,v in t.items() if k not in ('segments','track_render_index')}
    if track_metadata(before_track)!=track_metadata(after_track):raise ValueError('Native setter changed the target track or its metadata')
    left,right=copy.deepcopy(before),copy.deepcopy(after)
    def remove_path(value,path):
        for key in path[:-1]:
            value=value.get(key,{}) or {}
        value.pop(path[-1],None)
    allowed=[]
    if 'volumeLinear' in patch or 'gainDb' in patch:allowed += [('volume',),('last_nonzero_volume',)]
    if 'opacity' in patch:allowed += [('clip','alpha')]
    for key in patch.get('transform',{}):
        mapping={'scaleX':('clip','scale','x'),'scaleY':('clip','scale','y'),'rotationDeg':('clip','rotation'),
                 'xRatio':('clip','transform','x'),'yRatio':('clip','transform','y')}
        allowed.append(mapping[key])
    if any(k in patch.get('transform',{}) for k in ('scaleX','scaleY')):allowed.append(('uniform_scale',))
    if 'speed' in patch:allowed += [('speed',),('target_timerange','duration')]
    material_maps=[]
    for doc in (before_doc,after_doc):
        material_maps.append({m['id']:m for values in doc['materials'].values() if isinstance(values,list) for m in values if isinstance(m,dict) and 'id' in m})
    old,new=material_maps
    fade_change=any(k in patch for k in ('fadeInUs','fadeOutUs'))
    if fade_change:
        for value,index in ((left,old),(right,new)):
            value['extra_material_refs']=[ref for ref in value.get('extra_material_refs',[]) if index.get(ref,{}).get('type')!='audio_fade']
    for path in allowed:
        remove_path(left,path);remove_path(right,path)
    if left!=right:raise ValueError('Native setter changed an unrequested target segment field')
    for ref in [before['material_id'],*before.get('extra_material_refs',[])]:
        a,b=copy.deepcopy(old.get(ref)),copy.deepcopy(new.get(ref))
        if fade_change and a and a.get('type')=='audio_fade':continue
        if a is None or b is None:
            if a!=b:raise ValueError('Target resource reference changed')
            continue
        if 'crop' in patch and ref==before['material_id']:
            for key in ('crop','crop_ratio','crop_scale'):a.pop(key,None);b.pop(key,None)
        if 'speed' in patch and a.get('type')=='speed':
            for key in ('speed','curve_speed'):a.pop(key,None);b.pop(key,None)
        if a!=b:raise ValueError('Native setter changed an unrequested target material field')


def execute_extension(req, script, saved_matching):
    from capcut_state import items_from_doc, assert_unrelated
    from capcut_clip_properties import normalize_patch, build_property_commands, validate_fade_window
    base = script.exports_sync.run({**req,'action':'inspect'})
    before_doc = saved_matching(req,base['summary'])
    before_items = items_from_doc(before_doc)
    # Hash only semantic request fields, excluding per-run transport/deadline values.
    keys = ('action','project_id','timeline_id','input','input_sha256','start_us','duration_us','source_in_us','patch','segment_id','cues','style','position')
    request_digest = hashlib.sha256(canonical({k:req[k] for k in keys if k in req}).encode()).hexdigest()
    folder = ROOT/'.runtime/mutations';folder.mkdir(exist_ok=True)
    journal = folder/(req['request_id']+'.json')
    previous_failures=[]
    if journal.exists():
        previous = read_json(journal,64*1024*1024)
        if previous['requestDigest'] != request_digest: raise ValueError('request-id was already used with different parameters')
        if previous['outcome']=='success':
            recorded=previous['result']['items']
            current_by_id={x['id']:x for x in before_items}
            expected_replay=previous.get('replaySignature')
            raw_matches=(replay_signature(before_doc,[x['id'] for x in recorded])==expected_replay if expected_replay
                         else signature(before_doc)==previous['afterSignature'])
            if raw_matches and all(current_by_id.get(x['id'])==x for x in recorded):
                return {**previous['result'],'replayed':True,
                        'replayVerification':'Recorded affected items match current native IDs/timing and autosaved properties; no command re-executed',
                        'otherSavedStateChanged':signature(before_doc)!=previous['afterSignature']}
        if previous['outcome']=='not-applied' and signature(before_doc)==previous['beforeSignature']:
            previous_failures=previous.get('previousFailures',[])+[{'outcome':'not-applied','error':previous.get('error')}]
        else:
            raise MutationError('Existing request has changed or incomplete state; inspect its receipt before retrying',
                                {'outcome':previous['outcome'],'recoveryFile':str(journal),'retryAllowed':False})
    changed=[]
    record={'operationId':req['request_id'],'requestDigest':request_digest,'projectPath':req['project'],'request':{k:req[k] for k in keys if k in req},
            'pid':req['pid'],'sid':base['sid'],'outcome':'not-applied','before':before_items,
            'beforeSignature':signature(before_doc),'completedSteps':[],'createdIds':[],'previousFailures':previous_failures}
    current_doc=before_doc; current=base; pending=False
    frame_us=1e6/before_doc.get('fps',30)

    def refresh():
        nonlocal current,current_doc
        current=script.exports_sync.run({**req,'action':'inspect'})
        current_doc=saved_matching(req,current['summary'])
        return items_from_doc(current_doc)

    def step(argv, expected_check=None):
        nonlocal current,current_doc,pending
        if time.monotonic() > req['deadline_monotonic'] - 8: raise TimeoutError('Insufficient time for another native mutation')
        prior_signature=signature(current_doc)
        record.update(outcome='unknown',pendingStep=argv)
        write_record(journal,record);pending=True
        # JS JSON.stringify uses compact separators; the same observed summary is bound to each step.
        current=script.exports_sync.run({**req,'action':'extension-step','argv_bytes':[list(x.encode('utf8')) for x in argv],
                    'expected_sid':base['sid'],'expected_summary':json.dumps(current['summary'],ensure_ascii=False,separators=(',',':'))})
        if current.get('nativeError'):
            current_doc=saved_matching(req,current['summary'])
            if signature(current_doc)==prior_signature:pending=False
            raise ValueError(current['nativeError'])
        pending=False
        receipt={'argv':argv,'native':current['native']}
        record['completedSteps'].append(receipt)
        for sid in current['native'].get('segment_ids',[]):
            if sid not in record['createdIds']:record['createdIds'].append(sid)
        record.update(outcome='partially-applied',pendingStep=None);write_record(journal,record)
        deadline=min(time.monotonic()+10,req['deadline_monotonic']-3)
        last_error=None
        while True:
            try:
                current_doc=saved_matching(req,current['summary'])
                if expected_check:expected_check(items_from_doc(current_doc))
                return current
            except (ValueError,KeyError) as error:
                last_error=error
                if time.monotonic()>=deadline:raise ValueError('Saved postcondition did not converge: '+str(last_error))
                time.sleep(.15)

    def item(identity):
        return next(x for x in items_from_doc(current_doc) if x['id']==identity)

    def update_properties(identity,patch):
        old=item(identity); expected=property_expected(patch,old['properties'])
        # Complete paired axes/fades so omitted native defaults cannot reset them.
        expanded=copy.deepcopy(patch)
        if 'transform' in expanded:
            for pair in (('scaleX','scaleY'),('xRatio','yRatio')):
                if any(k in expanded['transform'] for k in pair):
                    for k in pair:expanded['transform'].setdefault(k,old['properties']['transform'][k])
        if old['type']=='audio' and any(k in expanded for k in ('fadeInUs','fadeOutUs')):
            expanded.update(validate_fade_window(expanded,old['targetUs']['duration'],
                current_fade_in_us=old['properties'].get('fadeInUs',0),current_fade_out_us=old['properties'].get('fadeOutUs',0)))
        for plan in build_property_commands(expanded,old['type'],identity,allow_speed=True):
            step(plan['argv'])
        # Wait for all changed properties; timing-only saved_matching is insufficient here.
        until=min(time.monotonic()+10,req['deadline_monotonic']-2)
        while True:
            try:
                require_properties(item(identity)['properties'],expected);break
            except ValueError:
                if time.monotonic()>=until:raise
                time.sleep(.15);refresh()

    try:
        action=req['action']
        if not before_doc.get('render_index_track_mode_on'): raise ValueError('Unsupported native track mode')
        if action=='add-audio':
            source=Path(req['input'])
            if file_digest(source)!=req['input_sha256']:raise ValueError('Audio source changed since validation')
            start,duration,source_in=req['start_us'],req['duration_us'],req['source_in_us']
            if start+duration>before_doc['duration'] or duration<frame_us:raise ValueError('Audio target exceeds timeline or is shorter than one frame')
            if source_in+duration>req['source_duration_us']:raise ValueError('Audio source window exceeds media duration')
            # Native auto-placement makes a compatible track; report actual track ID, never pretend --track creates one.
            initial_start=0 if source_in else start
            r=step(['draft','audio','add','--resource','local:///'+source.as_posix(),'--start',f'{initial_start}us','--duration',f'{source_in+duration}us'])
            ids=r['native'].get('segment_ids',[])
            if len(ids)!=1:raise ValueError('Audio add did not identify exactly one segment')
            identity=ids[0];changed.append(identity)
            if source_in:
                step(['draft','segment','time-range','--seg-id',identity,'--in',f'{source_in}us','--out',f'{source_in+duration}us'])
                step(['draft','segment','move','--seg-id',identity,'--start',f'{start}us'])
            if req['patch']:update_properties(identity,req['patch'])
            added=item(identity)
            if added['type']!='audio' or Path(added['sourcePath']).resolve()!=source.resolve():raise ValueError('Audio material linkage mismatch')
            if added['sourceUs']!={'start':source_in,'duration':duration} or added['targetUs']!={'start':start,'duration':duration}:
                raise ValueError('Audio source/target timing mismatch')
        elif action=='captions-import':
            if any(c['endUs']>before_doc['duration'] for c in req['cues']):raise ValueError('Caption extends past the current timeline')
            mappings=[]
            style_flags={'size':'--size','color':'--color','outlineColor':'--outline-color','outlineWidth':'--outline-width'}
            for cue in req['cues']:
                # Equals binds arbitrary text, even text starting with a native option, to one value.
                r=step(['draft','subtitle','add','--content='+content_literal(cue['text']),'--start',f'{cue["startUs"]}us','--duration',f'{cue["endUs"]-cue["startUs"]}us'])
                ids=r['native'].get('segment_ids',[])
                if len(ids)!=1:raise ValueError('Caption add did not identify exactly one segment')
                identity=ids[0];changed.append(identity);mappings.append({'cueId':cue['id'],'segmentId':identity})
                argv=['draft','text','style','--seg-id',identity]
                for key,value in req['style'].items():argv.extend([style_flags[key],str(value)])
                step(argv)
                position=req['position']
                step(['draft','text','translate','--seg-id',identity,'--x',str(position['xRatio']*100)+'%','--y',str(position['yRatio']*100)+'%'])
                def check_caption(rows):
                    row=next(x for x in rows if x['id']==identity)
                    if row['properties']['text']!=cue['text']:raise ValueError('Caption literal changed during native parsing')
                    require_properties(row['properties']['style'],req['style'],'style')
                    require_properties(row['properties']['transform'],position,'position')
                    if not caption_timing_matches(row['targetUs'],cue):raise ValueError('Caption timing mismatch')
                until=min(time.monotonic()+10,req['deadline_monotonic']-2)
                while True:
                    try:check_caption(refresh());break
                    except ValueError:
                        if time.monotonic()>=until:raise
                        time.sleep(.15)
                record['cueMappings']=mappings;write_record(journal,record)
        else:
            track,clip=segment(before_doc,req['segment_id']);identity=clip['id']
            patch=normalize_patch(req['patch'],track['type'])
            if clip.get('common_keyframes') or clip.get('keyframe_refs'):
                raise ValueError('This release refuses properties on keyframed clips')
            if 'speed' in patch:
                video_items=[x for x in before_items if x['type']=='video']
                if len(video_items)!=1 or len(before_items)!=1 or clip.get('speed',1)!=1 or clip['target_timerange']['start']!=0:
                    raise ValueError('Constant speed currently requires a sole, ordinary speed-1 video at time zero on a dedicated timeline')
                if clip['source_timerange']['duration']/patch['speed']<frame_us:raise ValueError('Speed result is shorter than one frame')
                if any(m.get('curve_speed') for m in before_doc['materials'].get('speeds',[]) if m['id'] in clip.get('extra_material_refs',[])):
                    raise ValueError('Curve-speed material is not supported')
            # Detect shared media objects before crop, which edits the video material.
            if 'crop' in patch and sum(x['materialId']==clip['material_id'] for x in before_items)>1:
                raise ValueError('Crop of a material shared by multiple segments is not yet supported')
            changed.append(identity)
            update_properties(identity,patch)
            final=item(identity);old=next(x for x in before_items if x['id']==identity)
            if final['sourceUs']!=old['sourceUs'] or final['targetUs']['start']!=old['targetUs']['start']:
                raise ValueError('Property edit changed the source window or target start')
            expected_duration=old['sourceUs']['duration']/patch['speed'] if 'speed' in patch else old['targetUs']['duration']
            if abs(final['targetUs']['duration']-expected_duration)>1:raise ValueError('Property edit duration mismatch')
            verify_target_preserved(before_doc,current_doc,identity,patch)
        refresh()
        assert_unrelated(before_doc,current_doc,changed)
        for key in ('fps','canvas_config','color_space','keyframes','keyframe_graph_list','retouch_cover'):
            if before_doc.get(key)!=current_doc.get(key):raise ValueError('Operation changed global rendering state: '+key)
        if 'speed' not in req.get('patch',{}) and current_doc['duration']!=before_doc['duration']:
            raise ValueError('Operation changed the timeline duration')
        after_items=items_from_doc(current_doc)
        if {x['id'] for x in after_items}!={x['id'] for x in before_items}|set(record['createdIds']):
            raise ValueError('Unexpected segment creation or deletion during operation')
        result={'backend':'capcut-native-editor','pid':req['pid'],'sid':base['sid'],'timelineId':req['timeline_id'],
                'operationId':req['request_id'],'changedIds':changed,'items':[x for x in after_items if x['id'] in changed],
                'before':[x for x in before_items if x['id'] in changed],'after':[x for x in after_items if x['id'] in changed],
                'verification':{'nativeIdentityAndTiming':True,'autosavedProperties':True,'unrelatedItemsPreserved':True},
                'propertyReadback':'CapCut-autosaved draft; native summary does not expose all audio/text attributes',
                'persistenceVerified':True,'recoveryFile':str(journal),'replayed':False}
        if 'cueMappings' in record:result['cueMappings']=record['cueMappings']
        record.update(outcome='success',afterSignature=signature(current_doc),replaySignature=replay_signature(current_doc,changed),result=result);write_record(journal,record)
        return result
    except Exception as error:
        outcome='unknown' if pending else ('partially-applied' if record['completedSteps'] else 'not-applied')
        record.update(outcome=outcome,error=str(error));write_record(journal,record)
        details={'outcome':outcome,'operationId':req['request_id'],'completedSteps':len(record['completedSteps']),
                 'createdIds':record['createdIds'],'recoveryFile':str(journal),'retryAllowed':outcome=='not-applied'}
        raise MutationError(str(error),details,preserve=pending) from error
