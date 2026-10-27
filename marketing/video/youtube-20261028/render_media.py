"""Render composed, signal-captioned MP4 demos from private Godot captures."""
from __future__ import annotations
import argparse, hashlib, json, math, sys, wave
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterator
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RATE, FPS = 48000, 30
H_SIZE, V_SIZE = (1920,1080), (1080,1920)
EVENTS = ["button_click","button_hover","toggle_on","toggle_off","menu_confirm","menu_back","error","notification","panel_open","panel_close","transition","coin_pickup","reward","level_up"]
PREVIEW = "https://bigshadex.github.io/pulselite-previewer/"
PRODUCT = {
 "Menu Kit":{"link":"https://bigshadex.itch.io/pulselite-ui-sfx","accent":"#c4825c","soft":"#88a995","bg":"#101b24"},
 "Sci-Fi":{"link":"https://bigshadex.itch.io/pulselite-scifi-ui","accent":"#58c4d3","soft":"#91d6c3","bg":"#071b2a"},
 "Horror":{"link":"https://bigshadex.itch.io/pulselite-horror-ui","accent":"#c97059","soft":"#d7ac88","bg":"#1d1018"},
}
@dataclass
class Capture:
 label:str; root:Path; receipt:dict; frames:list[Path]; trace:list[dict]; audio:np.ndarray

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def read_audio(path:Path)->np.ndarray:
 with wave.open(str(path),'rb') as w:
  n, width, rate, count=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes(); raw=w.readframes(count)
 if width==2: a=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
 elif width==4: a=np.frombuffer(raw,dtype='<i4').astype(np.float32)/2147483648
 else: raise SystemExit(f'Unsupported PCM width {width}')
 a=a.reshape(-1,n)
 if n==1: a=np.repeat(a,2,axis=1)
 elif n>2: a=a[:,:2]
 if rate!=RATE:
  from scipy.signal import resample_poly
  g=math.gcd(rate,RATE); a=resample_poly(a,RATE//g,rate//g,axis=0)
 return np.ascontiguousarray(a,dtype=np.float32)

def staged_source(c:Capture,row:dict)->tuple[Path,str,str]:
 raw=str(row.get('path','')); base=str(c.receipt['pack_contract']['base_path'])
 if not raw.startswith(base): raise SystemExit(f'Signal source is outside the declared pack base: {raw}')
 relative=raw.removeprefix('res://'); project=(c.root/'project').resolve(strict=True)
 path=(project/Path(relative)).resolve(strict=True)
 if not path.is_relative_to(project): raise SystemExit(f'Signal source escaped the disposable project: {raw}')
 key=raw[len(base):]; expected=c.receipt.get('staged_recordings_sha256',{}).get(key)
 if not expected: raise SystemExit(f'No capture receipt hash for staged source: {key}')
 digest=sha(path)
 if digest!=expected: raise SystemExit(f'Staged source hash mismatch: {key}')
 return path,relative,digest

def decode_ogg(path:Path,pyav)->np.ndarray:
 container=pyav.open(str(path),'r'); streams=[s for s in container.streams if s.type=='audio']
 if len(streams)!=1: raise SystemExit(f'Expected one audio stream in {path.name}')
 resampler=pyav.AudioResampler(format='fltp',layout='stereo',rate=RATE); pieces=[]
 for frame in container.decode(streams[0]):
  for converted in resampler.resample(frame): pieces.append(converted.to_ndarray().T.astype(np.float32,copy=True))
 for converted in resampler.resample(None): pieces.append(converted.to_ndarray().T.astype(np.float32,copy=True))
 container.close()
 if not pieces: raise SystemExit(f'No decoded audio frames in staged source {path.name}')
 return np.ascontiguousarray(np.concatenate(pieces,axis=0),dtype=np.float32)

def mix_trace_events(events:list[tuple[Capture,dict,float,float]],total:int,pyav):
 """Place exact played-signal source files on the captured wall-clock timeline."""
 out=np.zeros((total*RATE,2),np.float32); base_gain=.55; fade_n=round(.008*RATE); cache={}; rows=[]
 for capture,row,start_seconds,segment_end_seconds in events:
  path,relative,digest=staged_source(capture,row)
  if digest not in cache: cache[digest]=decode_ogg(path,pyav)
  clip=cache[digest].copy(); samples=len(clip)
  fade=min(fade_n,max(1,samples//3))
  clip[:fade]*=np.linspace(0,1,fade,dtype=np.float32)[:,None]
  clip[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)[:,None]
  start=round(start_seconds*RATE); end=start+samples; limit=round(segment_end_seconds*RATE)
  if start<0 or end>limit or end>len(out):
   raise SystemExit(f"Source tail would be cut for {row['event']} at {start_seconds:.3f}s")
  out[start:end]+=clip*base_gain
  rows.append({'pack_label':capture.label,'event':row['event'],'source_path':row['path'],
   'source_project_relative_path':relative,'source_sha256':digest,'trace_elapsed_ms':int(row['elapsed_ms']),
   'output_start_seconds':start_seconds,'output_event_seconds':start_seconds,
   'decoded_source_samples':samples,'decoded_source_seconds':samples/RATE,
   'base_gain':base_gain,'fade_in_samples':fade,'fade_out_samples':fade})
 peak_before=float(np.max(np.abs(out))); peak_gain=min(1.0,.90/peak_before) if peak_before>.90 else 1.0
 out*=peak_gain; peak_after=float(np.max(np.abs(out)))
 return out,{'method':'trace-timed mix of the exact staged source OGG paths; captured Godot WAV retained as QA evidence only',
  'sample_rate':RATE,'channels':2,'base_event_gain':base_gain,'global_peak_limit_gain':peak_gain,
  'peak_before_global_gain':peak_before,'peak_after_global_gain':peak_after,
  'pcm_sha256':hashlib.sha256(out.astype('<f4',copy=False).tobytes()).hexdigest(),'events':rows}

def load_capture(label:str,root:Path)->Capture:
 r=json.loads((root/'capture-receipt.json').read_text(encoding='utf-8'))
 if r.get('pack_label')!=label or r.get('audio_driver')!='Godot Dummy driver with AudioEffectRecord on Master bus': raise SystemExit(f'Capture identity mismatch: {label}')
 wav=root/r['audio_recording']['name']
 if sha(wav)!=r['audio_recording']['sha256']: raise SystemExit(f'Audio WAV hash mismatch: {label}')
 trace_path=root/'played-events.jsonl'
 if sha(trace_path)!=r['played_signal_trace']['sha256']: raise SystemExit(f'Trace hash mismatch: {label}')
 rows=[json.loads(s) for s in trace_path.read_text(encoding='utf-8').splitlines() if s.strip()]
 if not rows or any(not x.get('resource_exists') or not x.get('path','').startswith(r['pack_contract']['base_path']) for x in rows): raise SystemExit(f'Invalid played trace: {label}')
 frames=sorted((root/'frames').glob('frame-*.png'))
 if len(frames)!=r['viewport_frames']['count']: raise SystemExit(f'Viewport frame count mismatch: {label}')
 return Capture(label,root,r,frames,rows,read_audio(wav))

def face(size:int,bold:bool=False,path:Path|None=None):
 choices=[str(path)] if path else []
 choices += ['C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf','C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf','DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf']
 for c in choices:
  try:
   if Path(c).is_file() or c.startswith('DejaVu'): return ImageFont.truetype(c,size=size)
  except OSError: pass
 return ImageFont.load_default(size=size)

def textw(d,s,f):
 b=d.textbbox((0,0),s,font=f); return b[2]-b[0]

def wrap(d,s,f,maxw):
 out=[]; line=''
 for word in s.split():
  test=(line+' '+word).strip()
  if line and textw(d,test,f)>maxw: out.append(line); line=word
  else: line=test
 if line: out.append(line)
 return out

def wtext(d,xy,s,f,color,maxw,gap=6,limit=None):
 x,y=xy; lines=wrap(d,s,f,maxw)
 if limit and len(lines)>limit: lines=lines[:limit]; lines[-1]=lines[-1].rstrip(' .')+'...'
 for line in lines: d.text((x,y),line,font=f,fill=color); y+=f.size+gap
 return y

def pill(d,box,fill,outline=None,r=16,w=1): d.rounded_rectangle(box,radius=r,fill=fill,outline=outline,width=w)

def event_at(c:Capture,t:float):
 rows=[r for r in c.trace if int(r['elapsed_ms'])<=t*1000]
 return rows[-1] if rows else None

def frame_at(c:Capture,t:float):
 if not c.frames: raise SystemExit(f'No viewport frames for {c.label}')
 p=c.frames[min(max(round(t*8),0),len(c.frames)-1)]
 with Image.open(p) as im:
  if im.size!=(1280,720): raise SystemExit(f'Bad Godot frame size {im.size}')
  return im.convert('RGB')

def frame_names(c): return list(dict.fromkeys(str(r['event']) for r in c.trace))

def backdrop(size,p,title):
 im=Image.new('RGB',size,p['bg']); d=ImageDraw.Draw(im); w,h=size
 for x in range(-h,w,180): d.line((x,0,x+h,h),fill='#182a33',width=1)
 d.ellipse((w-410,-250,w+90,250),outline='#25363d',width=2)
 d.text((54,32),title,font=face(19,True),fill='#dce7df'); d.line((54,76,w-54,76),fill='#38505a',width=1)
 return im

def horizontal(c:Capture,t:float,fontpath:Path|None=None,override:str|None=None):
 p=PRODUCT[c.label]; im=backdrop(H_SIZE,p,'PULSELITE / SIGNAL STUDIO'); d=ImageDraw.Draw(im); row=event_at(c,t); event=override or (str(row['event']) if row else 'WAITING FOR INPUT'); source=str(row['path']) if row else 'Awaiting played(event, path)'
 d.text((54,98),c.label.upper(),font=face(16,True,fontpath),fill=p['accent'])
 title='14 MAPPED UI EVENTS' if c.label=='Menu Kit' else f'{c.label.upper()} UI SOUND IN A LIVE MENU'
 d.text((54,128),title,font=face(38,True,fontpath),fill='#f5f0e5')
 d.text((56,180),'SCRIPTED GODOT UI REPLAY  /  TRACE-TIMED SOURCE MIX  /  LIVE SIGNAL CAPTIONS',font=face(16,False,fontpath),fill='#aab8b3')
 pill(d,(45,230,1337,966),'#263a43','#52656a',20,2); im.paste(frame_at(c,t),(51,236))
 pill(d,(1367,230,1874,966),'#14242c','#43545c',20,2)
 d.text((1395,258),'PLAYED SIGNAL',font=face(16,True,fontpath),fill=p['soft'])
 wtext(d,(1395,292),event.replace('_',' ').upper(),face(26,True,fontpath),'#f5f0e5',445,4,2)
 d.text((1395,374),'RESOLVED SOURCE FILE',font=face(14,True,fontpath),fill='#91a19e')
 wtext(d,(1395,402),source,face(15,False,fontpath),'#c7d1ca',440,5,3); d.line((1395,490,1845,490),fill='#354850',width=1)
 if c.label=='Menu Kit':
  d.text((1395,512),'14 EVENT MAP',font=face(16,True,fontpath),fill=p['accent'])
  for i,name in enumerate(EVENTS):
   col,rowi=i//7,i%7; x,y=1395+col*225,548+rowi*42; active=name==event
   if active: pill(d,(x-5,y-4,x+210,y+31),'#263b41',p['soft'],8)
   d.ellipse((x,y+7,x+9,y+16),fill=p['accent'] if active else '#71817e')
   d.text((x+17,y+3),name,font=face(14,active,fontpath),fill='#f5f0e5' if active else '#adbbb5')
  d.text((1395,861),'Each line is a mapped addon event key.',font=face(14,False,fontpath),fill='#91a19e')
 else:
  d.text((1395,512),'CAPTURED INTERACTIONS',font=face(16,True,fontpath),fill=p['accent'])
  for i,name in enumerate(frame_names(c)[:8]):
   y=556+i*39; active=name==event
   if active: pill(d,(1390,y-5,1849,y+28),'#263b41',p['soft'],8)
   d.ellipse((1400,y+5,1409,y+14),fill=p['accent'] if active else '#71817e')
   d.text((1421,y),name.upper(),font=face(16,active,fontpath),fill='#f5f0e5' if active else '#adbbb5')
  d.text((1395,885),'Illustrative Godot UI scene; not in the pack.',font=face(13,False,fontpath),fill='#91a19e')
 d.line((54,1001,1866,1001),fill='#38505a',width=1)
 d.text((54,1017),'PROCEDURAL DSP SOUND  /  AI-ASSISTED VIDEO  /  UI SCENE NOT INCLUDED',font=face(13,True,fontpath),fill='#aab8b3')
 d.text((1436,1017),'PULSELITE  /  GODOT 4',font=face(13,True,fontpath),fill=p['soft'])
 return im

def horizontal_title(c:Capture,fontpath:Path|None=None):
 p=PRODUCT[c.label]; im=backdrop(H_SIZE,p,'PULSELITE / UI SOUND DEMONSTRATION'); d=ImageDraw.Draw(im)
 screen=frame_at(c,min(2.5,max(0,len(c.frames)/8-.1))).resize((1040,585),Image.Resampling.LANCZOS)
 pill(d,(820,176,1883,777),'#263a43','#56686f',24,2); im.paste(screen,(831,184))
 d.text((74,214),c.label.upper(),font=face(22,True,fontpath),fill=p['accent'])
 title='14 MAPPED UI EVENTS' if c.label=='Menu Kit' else f'{c.label.upper()} UI SOUNDS'
 y=wtext(d,(72,278),title,face(64,True,fontpath),'#f5f0e5',700,3,3)
 wtext(d,(78,y+42),'Real addon signal captions. Source recordings aligned to each signal.',face(27,False,fontpath),'#bcc9c2',670,9,3)
 pill(d,(76,630,705,700),'#172832',p['soft'],16,2); d.text((105,651),'GODOT UI REPLAY  /  PROCEDURAL DSP AUDIO',font=face(17,True,fontpath),fill=p['soft'])
 return im

def horizontal_outro(c:Capture,fontpath:Path|None=None):
 p=PRODUCT[c.label]; im=backdrop(H_SIZE,p,'PULSELITE / FIND YOUR NEXT UI SOUND'); d=ImageDraw.Draw(im)
 title='14 EVENTS. ONE MENU KIT.' if c.label=='Menu Kit' else f'TRY {c.label.upper()} UI SOUNDS'
 wtext(d,(82,150),title,face(64,True,fontpath),'#f5f0e5',1720,7,2)
 d.text((87,320),'Preview the mapped sounds',font=face(28,False,fontpath),fill='#bdc9c2')
 pill(d,(78,378,1840,520),'#172832',p['soft'],22,2); wtext(d,(110,416),p['link'],face(29,True,fontpath),p['soft'],1680,3,2)
 d.text((88,590),'Hear the browser preview',font=face(28,False,fontpath),fill='#bdc9c2')
 pill(d,(78,648,1840,790),'#172832',p['accent'],22,2); wtext(d,(110,686),PREVIEW,face(29,True,fontpath),p['accent'],1680,3,2)
 d.text((88,894),'Procedural DSP source clips. Trace-timed mix. AI-assisted video.',font=face(23,False,fontpath),fill='#bdc9c2')
 d.text((88,942),'Illustrative Godot interface only; it is not included in the sound pack.',font=face(21,False,fontpath),fill='#91a19e')
 return im

def youtube_thumbnail(c:Capture,title:str,fontpath:Path|None=None):
 p=PRODUCT[c.label]; first=float(c.trace[0]['elapsed_ms'])/1000
 im=frame_at(c,first+.2).convert('RGBA'); overlay=Image.new('RGBA',im.size,(0,0,0,0)); d=ImageDraw.Draw(overlay)
 accent=p['accent']; rgb=tuple(int(accent[i:i+2],16) for i in (1,3,5))
 d.rounded_rectangle((28,385,1252,700),radius=26,fill=(8,19,26,228),outline=(*rgb,240),width=3)
 d.rounded_rectangle((28,385,43,700),radius=8,fill=(*rgb,255))
 im=Image.alpha_composite(im,overlay).convert('RGB'); d=ImageDraw.Draw(im)
 d.text((70,414),f'PULSELITE  /  {c.label.upper()} PACK',font=face(34,True,fontpath),fill=accent)
 short_title='14 UI EVENTS · 60s' if c.label=='Menu Kit' else f'{c.label.upper()} UI SOUNDS'
 size=96; title_font=face(size,True,fontpath)
 while textw(d,short_title,title_font)>1110 and size>78:
  size-=2; title_font=face(size,True,fontpath)
 d.text((68,465),short_title,font=title_font,fill='#fff8ec',stroke_width=1,stroke_fill='#14242c')
 d.text((72,600),'Illustrative Godot demo',font=face(30,False,fontpath),fill='#c4d0ca')
 return im

def audio_full(c:Capture,total:int,intro:int,capdur:int,pyav):
 events=[(c,row,intro+float(row['elapsed_ms'])/1000,intro+capdur) for row in c.trace]
 return mix_trace_events(events,total,pyav)

def encode_mp4(path:Path,duration:int,frames:Iterator[Image.Image],audio:np.ndarray,title:str,pyav,size=H_SIZE):
 if path.exists(): raise SystemExit(f'Refuse overwrite: {path}')
 container=pyav.open(str(path),'w',format='mp4',options={'movflags':'+faststart'})
 video=container.add_stream('libx264',rate=FPS); video.width,video.height=size; video.pix_fmt='yuv420p'; video.bit_rate=1_850_000
 video.options={'preset':'veryfast','crf':'20','profile':'high','bf':'0'}
 astream=container.add_stream('aac',rate=RATE); astream.layout='stereo'; astream.bit_rate=112_000
 container.metadata.update({'title':title,'comment':'AI-assisted video; procedural DSP sound effects; scripted Godot UI capture.'})
 packets=[]; expected=duration*FPS
 for i,image in enumerate(frames):
  if i>=expected: break
  if image.size!=size: raise SystemExit(f'Bad compositor output size: {image.size}')
  vf=pyav.VideoFrame.from_image(image.convert('RGB')); vf.pts=i; vf.time_base=Fraction(1,FPS)
  for pk in video.encode(vf): packets.append((float((pk.dts if pk.dts is not None else pk.pts)*pk.time_base),pk))
 if i+1!=expected: raise SystemExit(f'Encoded {i+1} frames; expected {expected}')
 for pk in video.encode(None): packets.append((float((pk.dts if pk.dts is not None else pk.pts)*pk.time_base),pk))
 for start in range(0,len(audio),1024):
  chunk=audio[start:start+1024]
  if len(chunk)<1024:
   padded=np.zeros((1024,2),np.float32); padded[:len(chunk)]=chunk; chunk=padded
  af=pyav.AudioFrame.from_ndarray(np.ascontiguousarray(chunk.T),format='fltp',layout='stereo'); af.sample_rate=RATE; af.pts=start; af.time_base=Fraction(1,RATE)
  for pk in astream.encode(af): packets.append((float((pk.dts if pk.dts is not None else pk.pts)*pk.time_base),pk))
 for pk in astream.encode(None): packets.append((float((pk.dts if pk.dts is not None else pk.pts)*pk.time_base),pk))
 packets.sort(key=lambda x:(x[0],0 if x[1].stream.type=='video' else 1))
 for _,pk in packets: container.mux(pk)
 container.close()
 return {'bytes':path.stat().st_size,'sha256':sha(path),'frames_expected':expected,'audio_samples_expected':len(audio)}

def verify_mp4(path:Path,duration:int,pyav,size=H_SIZE):
 c=pyav.open(str(path),'r'); vs=[s for s in c.streams if s.type=='video']; aus=[s for s in c.streams if s.type=='audio']
 if len(vs)!=1 or len(aus)!=1: raise SystemExit(f'Expected one video and one audio track in {path.name}')
 v,a=vs[0],aus[0]
 if (v.codec_context.name,v.codec_context.width,v.codec_context.height,v.codec_context.format.name)!=('h264',size[0],size[1],'yuv420p') or a.codec_context.name!='aac':
  raise SystemExit(f'Unexpected MP4 tracks: {v.codec_context.name}/{v.codec_context.width}x{v.codec_context.height}/{v.codec_context.format.name} + {a.codec_context.name}')
 resampler=pyav.AudioResampler(format='fltp',layout='stereo',rate=RATE); count=0; peak=0.0; sq=0.0; vals=0; video_count=0
 for packet in c.demux(v,a):
  for fr in packet.decode():
   if packet.stream.type=='video': video_count+=1
   else:
    for converted in resampler.resample(fr):
     x=converted.to_ndarray().astype(np.float32); count+=converted.samples; peak=max(peak,float(np.max(np.abs(x)))); sq+=float(np.sum(x*x)); vals+=x.size
 if video_count!=duration*FPS: raise SystemExit(f'{path.name} decoded {video_count} frames, expected {duration*FPS}')
 rms=math.sqrt(sq/max(vals,1))
 if count<RATE*duration*.97 or peak<.02 or rms<.0001: raise SystemExit(f'{path.name} decoded AAC appears silent/short: n={count}, peak={peak:.6f}, rms={rms:.6f}')
 c.close()
 return {'format':'MP4','video_codec':'H.264','pixel_format':'yuv420p','dimensions':list(size),'video_frames_decoded':video_count,'video_fps':FPS,'video_duration_seconds':video_count/FPS,'audio_codec':'AAC','audio_samples_decoded':count,'audio_sample_rate':RATE,'decoded_pcm_peak':peak,'decoded_pcm_rms':rms,'bytes':path.stat().st_size,'sha256':sha(path)}

def write_metadata(path,title,description,tags):
 path.write_text(f'# YouTube metadata\n\nTitle: {title}\n\nDescription:\n{description}\n\nTags:\n'+', '.join(tags)+'\n',encoding='utf-8')


def vtitle(fontpath=None):
 p=PRODUCT['Menu Kit']; im=Image.new('RGB',V_SIZE,p['bg']); d=ImageDraw.Draw(im); d.text((54,32),'PULSELITE / SHORT DEMO',font=face(19,True,fontpath),fill='#dce7df')
 d.line((54,76,1026,76),fill='#38505a',width=1); d.text((58,180),'THREE PACKS',font=face(23,True,fontpath),fill=p['soft'])
 wtext(d,(56,255),'MENU TO SCI-FI TO HORROR',face(67,True,fontpath),'#f5f0e5',960,10,3)
 d.text((64,620),'Source clips timed to signal trace',font=face(34,False,fontpath),fill='#bdc9c2')
 for i,label in enumerate(('Menu Kit','Sci-Fi','Horror')):
  x=62+i*322; q=PRODUCT[label]; pill(d,(x,800,x+300,870),'#172832',q['accent'],16,2); d.text((x+24,820),label.upper(),font=face(21,True,fontpath),fill=q['accent'])
 d.text((64,1660),'Scripted Godot replay  /  Procedural DSP audio',font=face(20,True,fontpath),fill='#aab8b3')
 d.text((64,1710),'AI-assisted video  /  Illustrative UI, not included',font=face(18,False,fontpath),fill='#91a19e')
 return im

def voutro(fontpath=None):
 p=PRODUCT['Menu Kit']; im=Image.new('RGB',V_SIZE,p['bg']); d=ImageDraw.Draw(im); d.text((54,32),'PULSELITE / FIND YOUR NEXT UI SOUND',font=face(19,True,fontpath),fill='#dce7df'); d.line((54,76,1026,76),fill='#38505a',width=1)
 wtext(d,(60,170),'TRY THE SOUND PREVIEWER',face(56,True,fontpath),'#f5f0e5',950,8,3)
 pill(d,(58,410,1022,580),'#172832',p['soft'],24,2); wtext(d,(88,452),PREVIEW,face(27,True,fontpath),p['soft'],880,6,3)
 y=690
 for label in ('Menu Kit','Sci-Fi','Horror'):
  q=PRODUCT[label]; d.text((62,y),label.upper(),font=face(22,True,fontpath),fill=q['accent']); y+=43; y=wtext(d,(62,y),q['link'],face(25,True,fontpath),'#f5f0e5',920,5,3)+53
 d.text((62,1485),'Procedural DSP sound effects. AI-assisted video.',font=face(21,False,fontpath),fill='#bdc9c2')
 d.text((62,1535),'Illustrative Godot interface; not included in the packs.',font=face(19,False,fontpath),fill='#91a19e')
 return im

def vframe(captures,index,local_seconds,fontpath=None,start_seconds=0):
 label=('Menu Kit','Sci-Fi','Horror')[index]; c=captures[label]; p=PRODUCT[label]
 im=Image.new('RGB',V_SIZE,p['bg']); d=ImageDraw.Draw(im); d.text((54,32),'PULSELITE / UI SOUND SHORT',font=face(19,True,fontpath),fill='#dce7df'); d.line((54,76,1026,76),fill='#38505a',width=1)
 d.text((58,112),f'PACK {index+1} OF 3',font=face(20,True,fontpath),fill=p['accent']); d.text((58,152),label.upper(),font=face(47,True,fontpath),fill='#f5f0e5')
 shot=frame_at(c,start_seconds+local_seconds).resize((960,540),Image.Resampling.LANCZOS); pill(d,(54,254,1026,806),'#263a43','#52656a',20,2); im.paste(shot,(60,260))
 row=event_at(c,start_seconds+local_seconds); event=str(row['event']) if row else 'READY'; source=str(row['path']) if row else 'Awaiting played(event, path)'; pill(d,(56,856,1024,1190),'#14242c','#43545c',20,2)
 d.text((86,886),'PLAYED EVENT',font=face(19,True,fontpath),fill=p['soft']); wtext(d,(86,930),event.upper(),face(38,True,fontpath),'#f5f0e5',880,4,2)
 d.text((86,1035),'RESOLVED PACK FILE',font=face(17,True,fontpath),fill='#91a19e'); wtext(d,(86,1072),source,face(19,False,fontpath),'#c7d1ca',880,5,3)
 for i,name in enumerate(('Menu Kit','Sci-Fi','Horror')):
  x=62+i*322; q=PRODUCT[name]; pill(d,(x,1242,x+298,1308),'#172832',q['accent'],15,2); d.text((x+15,1263),name.upper(),font=face(16,True,fontpath),fill=q['accent'])
 d.line((60,1360,1020,1360),fill='#38505a',width=1); d.text((62,1392),'SIGNAL-CAPTIONED GODOT REPLAY / TRACE-TIMED MIX',font=face(18,True,fontpath),fill='#aab8b3')
 d.text((62,1434),'PROCEDURAL DSP AUDIO  /  AI-ASSISTED VIDEO',font=face(16,True,fontpath),fill='#aab8b3'); d.text((62,1476),'Illustrative UI scene is not part of the sound packs.',font=face(16,False,fontpath),fill='#91a19e')
 return im

def short_audio(captures,pyav):
 labels=('Menu Kit','Sci-Fi','Horror'); names=('button_click','button_hover','menu_confirm'); specs=[]
 for i,(label,name) in enumerate(zip(labels,names)):
  c=captures[label]; row=next((x for x in c.trace if x['event']==name),None)
  if row is None: raise SystemExit(f'Missing {name} in {label} source trace')
  start=2+6*i; specs.append((c,row,start,start+6))
 out,mix=mix_trace_events(specs,25,pyav)
 for row in mix['events']: row['segment_end_seconds']=row['output_start_seconds']+6
 return out,mix

def write_meta(path,title,desc,tags):
 path.write_text(f'# YouTube metadata\n\nTitle: {title}\n\nDescription:\n{desc}\n\nTags:\n'+', '.join(tags)+'\n',encoding='utf-8')

def horizontal_video(c,outdir,fontpath,pyav):
 menu=c.label=='Menu Kit'; intro,capdur,end=(3,52,5) if menu else (4,20,6); total=intro+capdur+end
 title='14 Mapped UI Events in 60 Seconds | PulseLite Menu Kit' if menu else f'{c.label} UI Sound Effects | PulseLite'
 name='pulselite-menu-kit-14-events' if menu else f'pulselite-{c.label.lower()}-ui-sounds'; path=outdir/(name+'.mp4')
 def frames():
  for i in range(total*FPS):
   t=i/FPS
   if t<intro: yield horizontal_title(c,fontpath)
   elif t<intro+capdur: yield horizontal(c,t-intro,fontpath)
   else: yield horizontal_outro(c,fontpath)
 raw,audio_mix=audio_full(c,total,intro,capdur,pyav); enc=encode_mp4(path,total,frames(),raw,title,pyav); check=verify_mp4(path,total,pyav)
 if path.stat().st_size>=20_000_000: raise SystemExit(f'Output over 20 MB: {path.name}')
 thumb=youtube_thumbnail(c,title,fontpath)
 thumb_path=outdir/(name+'.png'); thumb.save(thumb_path,format='PNG',optimize=True)
 if thumb_path.stat().st_size>=3_000_000: raise SystemExit(f'Thumbnail over 3MB: {thumb_path.name}')
 desc=(f'A {c.label} sound demonstration with captions read from the real PulseLiteUI.played(event, path) signal. The Godot interface is illustrative and is not included in the sound pack. This video uses a scripted Godot UI replay. The soundtrack is a postproduction mix: each exact source-pack recording is placed at its signal time. The captured Godot WAV is retained as private QA evidence and is not the final soundtrack. The sounds are procedurally DSP-generated; this video was made with AI assistance.\n\nPreview the mapped sounds: {PREVIEW}\n{c.label} pack: {PRODUCT[c.label]["link"]}')
 tags=['PulseLite','UI sound effects','game UI audio','Godot','game development',f'{c.label} UI sounds','procedural audio','sound design']; meta=outdir/(name+'.metadata.md'); write_meta(meta,title,desc,tags)
 return {'title':title,'video':{**enc,**check},'thumbnail':{'file':thumb_path.name,'bytes':thumb_path.stat().st_size,'sha256':sha(thumb_path),'dimensions':[1280,720]},'metadata':meta.name,'tags':tags,'description':desc,'source_zip_sha256':c.receipt['source_archive']['sha256'],'trace_sha256':c.receipt['played_signal_trace']['sha256'],'audio_mix':audio_mix,'event_timeline':[{'event':x['event'],'source_path':x['path'],'capture_ms':x['elapsed_ms'],'output_seconds':intro+int(x['elapsed_ms'])/1000} for x in c.trace]}

def short_video(captures,outdir,fontpath,pyav,priv):
 path=outdir/'pulselite-menu-scifi-horror-short.mp4'; title='Menu to Sci-Fi to Horror UI Sounds | PulseLite #Shorts'
 def frames():
  for i in range(25*FPS):
   t=i/FPS
   if t<2: yield vtitle(fontpath)
   elif t<20:
    x=t-2; seg=min(int(x//6),2); offset=float(next(r for r in captures[('Menu Kit','Sci-Fi','Horror')[seg]].trace if r['event']==('button_click','button_hover','menu_confirm')[seg])['elapsed_ms'])/1000
    yield vframe(captures,seg,x-seg*6,fontpath,offset)
   else: yield voutro(fontpath)
 audio,audio_mix=short_audio(captures,pyav); (priv/'short-audio-timeline.json').write_text(json.dumps({'duration_seconds':25,'audio_mix':audio_mix},indent=2)+'\n',encoding='utf-8')
 enc=encode_mp4(path,25,frames(),audio,title,pyav,V_SIZE); check=verify_mp4(path,25,pyav,V_SIZE)
 if path.stat().st_size>=20_000_000: raise SystemExit('Short output is over 20 MB')
 desc=('Menu Kit to Sci-Fi to Horror: three source-pack recordings with captions from the addon played(event, path) signal. The Godot UI is illustrative and is not included in the packs. This is a scripted UI replay. The soundtrack is postproduced from the exact trace-mapped source recordings; the captured Godot WAV is private QA evidence, not the final soundtrack. The sounds use procedural DSP; this video was made with AI assistance.\n\n'+f'Previewer: {PREVIEW}\nMenu Kit: {PRODUCT["Menu Kit"]["link"]}\nSci-Fi: {PRODUCT["Sci-Fi"]["link"]}\nHorror: {PRODUCT["Horror"]["link"]}')
 tags=['PulseLite','YouTube Shorts','UI sound effects','game audio','Godot','Menu Kit','Sci-Fi UI sounds','Horror UI sounds']; meta=outdir/'pulselite-menu-scifi-horror-short.metadata.md'; write_meta(meta,title,desc,tags)
 return {'title':title,'video':{**enc,**check},'metadata':meta.name,'tags':tags,'description':desc,'audio_mix':audio_mix}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--menu-capture',type=Path,required=True); p.add_argument('--sci-fi-capture',type=Path,required=True); p.add_argument('--horror-capture',type=Path,required=True)
 p.add_argument('--youtube-output',type=Path,required=True); p.add_argument('--shorts-output',type=Path,required=True); p.add_argument('--pyav-path',type=Path,required=True); p.add_argument('--private-output',type=Path,required=True); p.add_argument('--font',type=Path)
 a=p.parse_args(); sys.path.insert(0,str(a.pyav_path.resolve(strict=True))); import av
 captures={'Menu Kit':load_capture('Menu Kit',a.menu_capture.resolve(strict=True)),'Sci-Fi':load_capture('Sci-Fi',a.sci_fi_capture.resolve(strict=True)),'Horror':load_capture('Horror',a.horror_capture.resolve(strict=True))}
 if set(x['event'] for x in captures['Menu Kit'].trace)!=set(EVENTS): raise SystemExit('Menu trace lacks one of 14 mapped events')
 if not all(c.receipt['source_archive']['sha256']==c.receipt['source_archive']['archive_sha256'] for c in captures.values()): raise SystemExit('Source ZIP hash disagrees with archive inspection')
 a.youtube_output.mkdir(parents=True,exist_ok=True); a.shorts_output.mkdir(parents=True,exist_ok=True); a.private_output.mkdir(parents=True,exist_ok=True)
 fontpath=a.font.resolve(strict=True) if a.font else None
 results=[horizontal_video(c,a.youtube_output,fontpath,av) for c in (captures['Sci-Fi'],captures['Horror'],captures['Menu Kit'])]
 short=short_video(captures,a.shorts_output,fontpath,av,a.private_output)
 thumb=Image.new('RGB',(1280,720),PRODUCT['Menu Kit']['bg']); d=ImageDraw.Draw(thumb)
 d.rectangle((0,0,1280,100),fill='#101b24'); d.text((36,25),'MENU / SCI-FI / HORROR UI SOUNDS',font=face(35,True,fontpath),fill='#f5f0e5')
 for i,label in enumerate(('Menu Kit','Sci-Fi','Horror')):
  c=captures[label]; ev=('button_click','button_hover','menu_confirm')[i]; row=next(x for x in c.trace if x['event']==ev); shot=frame_at(c,float(row['elapsed_ms'])/1000+.2).resize((420,236),Image.Resampling.LANCZOS); x=10+i*426; thumb.paste(shot,(x,112)); d.rectangle((x,112,x+420,348),outline=PRODUCT[label]['accent'],width=3); d.text((x+12,365),label.upper(),font=face(25,True,fontpath),fill=PRODUCT[label]['accent'])
 d.rectangle((0,650,1280,720),fill='#101b24'); d.text((36,668),'PROCEDURAL DSP AUDIO  /  AI-ASSISTED VIDEO',font=face(20,True,fontpath),fill='#bdc9c2')
 th=a.shorts_output/'pulselite-menu-scifi-horror-short.png'; thumb.save(th,format='PNG',optimize=True)
 if th.stat().st_size>=3_000_000: raise SystemExit('Short thumbnail exceeds 3 MB')
 receipt={'pyav_version':av.__version__,'godot_capture_receipts':{k:str(v.root/'capture-receipt.json') for k,v in captures.items()},'source_archives':{k:{'sha256':v.receipt['source_archive']['sha256'],'bytes':v.receipt['source_archive']['bytes']} for k,v in captures.items()},'audio_sources':{k:{'capture_wav_sha256':v.receipt['audio_recording']['sha256'],'trace_sha256':v.receipt['played_signal_trace']['sha256'],'trace_rows':len(v.trace)} for k,v in captures.items()},'final_audio_method':'Postproduction mix of exact staged source OGGs placed at the addon played(event,path) elapsed_ms timestamps; original AudioEffectRecord WAVs are retained as private QA evidence and are not used in final soundtracks.','horizontal':results,'short':short,'short_thumbnail':{'file':th.name,'dimensions':[1280,720],'bytes':th.stat().st_size,'sha256':sha(th)},'acceptance_boundary':'The separate trace-mix-verification.json records bounded source-to-AAC correlation and silent-card checks. Godot UI input was scripted. No physical listening or human-input claim.'}
 receipt_path=a.private_output/'final-media-receipt.json'; receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 contact=Image.new('RGB',(660,740),'#15232a')
 for i,entry in enumerate(results):
  if i>=3: break
  path=a.youtube_output/entry['video'].get('name','')
  thumbpath=a.youtube_output/('pulselite-menu-kit-14-events.png' if i==2 else f'pulselite-{("sci-fi" if i==0 else "horror")}-ui-sounds.png')
  with Image.open(thumbpath) as im: contact.paste(im.resize((320,180)),((i%2)*330,(i//2)*230))
 with Image.open(th) as im: contact.paste(im.resize((320,180)),(330,460))
 (a.private_output/'contact-sheet.png').parent.mkdir(parents=True,exist_ok=True); contact.save(a.private_output/'contact-sheet.png')
 print(f'RENDER_OK PyAV={av.__version__} count=4 receipt={receipt_path}')
 for r in results: print(f"VIDEO {r['title']} bytes={r['video']['bytes']} frames={r['video']['video_frames_decoded']} audio_peak={r['video']['decoded_pcm_peak']:.6f} audio_rms={r['video']['decoded_pcm_rms']:.6f}")
 print(f"SHORT {short['title']} bytes={short['video']['bytes']} frames={short['video']['video_frames_decoded']} audio_peak={short['video']['decoded_pcm_peak']:.6f} audio_rms={short['video']['decoded_pcm_rms']:.6f}")
if __name__=='__main__': main()
