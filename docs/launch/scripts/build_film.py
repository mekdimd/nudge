"""Assemble editable v2 scenes from the verified browser recordings."""
from pathlib import Path
import json
import subprocess

P = Path(__file__).resolve().parents[1]
A = P / 'assets' / 'browser'
SCALE = 1680 / 1280


def trim(case, name, start, duration):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(start), '-i', str(A / (case + '.webm')),
                    '-t', str(duration), '-vf', 'fps=60', '-an', '-c:v', 'libx264', '-crf', '16',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(A / (name + '.mp4'))], check=True)


def clip(id, start, duration, contents, track=1, beat=''):
    return f'<div id="{id}" class="clip" data-start="{start}" data-duration="{duration}" data-track-index="{track}" data-track-kind="graphics"'+(f' data-beat="{beat}"' if beat else '')+f'>{contents}</div>'


def video(id, src, start, duration):
    return f'<video id="{id}" class="clip screen-media" src="assets/browser/{src}.mp4" muted playsinline data-start="{start}" data-duration="{duration}" data-track-index="1" data-hf-media-start-basis="local"></video>'


def image(name, cls='screen-media'):
    return f'<img class="{cls}" src="assets/browser/{name}.png" alt="">'


def cursor(id, dark=False):
    return f'<img id="{id}" class="actor'+(' human' if dark else '')+'" src="assets/'+('human-cursor.svg' if dark else 'pointer.png')+'" alt="" data-layout-ignore>'


def ring(id, miss=False):
    return f'<div id="{id}" class="ring'+(' miss' if miss else '')+'" data-layout-ignore></div>'


def move(id, first, last, at, duration=.28):
    x,y=first;tx,ty=last
    return f'launchMove(tl,"#{id}",[{x*SCALE},{y*SCALE}],[{tx*SCALE},{ty*SCALE}],{at},{duration});'


def click(id, rid, position, at):
    x,y=position
    return f'launchClick(tl,"#{id}","#{rid}",[{x*SCALE},{y*SCALE}],{at});'


def scene(name, duration, body, js, styles=''):
    (P / 'compositions' / (name+'.html')).write_text(f'''<template>
<style>#root{{position:absolute;inset:0}}{styles}</style>
<div id="root" class="scene" data-composition-id="{name}" data-width="1920" data-height="1080" data-duration="{duration}">{body}</div>
<script>{{const tl=gsap.timeline({{paused:true}});{js}window.__timelines["{name}"]=tl;}}</script>
</template>
''')


def title(name, text, goal=None):
    return '<h1 id="'+name+'-title" class="headline">'+text+'</h1>'+('<img class="goal-bar" src="assets/browser/'+goal+'-idle.png" alt="Nudge task request">' if goal else '')


def main():
    for source,name,box in [('mail-draft','mail-subject','650:144:24:250'),('mail-draft-edited','mail-subject-edited','650:144:24:250'),('mail-draft','mail-type-focus','470:105:430:670'),('mail-confirm','mail-confirm-focus','656:236:0:0')]:
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(A/(source+'.png')),'-vf','crop='+box,'-frames:v','1',str(A/(name+'.png'))],check=True)
    info={case:json.loads((A/(case+'-actions.json')).read_text()) for case in ('bank','youtube','mail')}
    # These points follow decoded screen changes, including the recording pre-roll.
    points=json.loads((A/'edit-points.json').read_text())
    bank_onsets=[next(v['at'] for v in points['bank'] if v['state']==i) for i in (1,2,3)]
    for name,point,duration in zip(('bank-nav','bank-statement','bank-download'),bank_onsets,(2.15,2.15,2.433333)):
        trim('bank',name,point-.8,duration)
    yt_type=next(v['at'] for v in points['youtube'] if v['state']==1)
    yt_click=info['youtube']['recordingOffset']+info['youtube']['actions'][1]['at']-.7
    trim('youtube','youtube-type',yt_type-.35,1.5)
    trim('youtube','youtube-search',yt_click-.6,2.5)
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(A/'youtube-result-closeup.webm')]))
    trim('youtube-result-closeup','youtube-results',duration-2.5,2.5)
    mail_onsets={i:next(v['at'] for v in points['mail'] if v['state']==i) for i in (1,4,5)}
    trim('mail','mail-compose',mail_onsets[1]-.6,1.15)
    trim('mail','mail-fill',mail_onsets[4]-.25,1.6)
    trim('mail','mail-send',mail_onsets[5]-.45,2.116667)

    # The hook shows only a website and ordinary cursor misses.
    misses=[(206,258),(1220,340),(770,214)]
    h=title('hook','Small targets add up.')
    inner=image('bank-page-idle')+cursor('hook-cursor',True)+''.join(ring('miss-'+str(i),True) for i in range(3))
    h+='<div class="screen"><div id="hook-stage" class="screen-stage" data-layout-allow-overflow>'+inner+'</div></div>'
    js='tl.set("#hook-cursor",{x:750,y:210,opacity:1});'
    source=(570,160)
    for i,target in enumerate(misses):
        at=.4+i*.78
        js+=move('hook-cursor',source,target,at,.24)+click('hook-cursor','miss-'+str(i),target,at+.25)
        source=target
    js+='tl.to("#hook-stage",{scale:1.045,x:-15,y:-15,duration:.32,ease:"power2.inOut"},2.72);'
    scene('hook',202/60,h,js)

    body='<h1 id="reveal-word" class="wordmark">Nudge</h1>'+cursor('reveal-cursor')
    js='tl.fromTo("#reveal-word",{y:65,opacity:0},{y:0,opacity:1,duration:.22,ease:"power3.out"},0);tl.fromTo("#reveal-cursor",{x:1590,y:670,scale:1.8,rotation:18},{x:1240,y:335,scale:2.3,rotation:0,opacity:1,duration:.34,ease:"power3.out"},.06);'
    scene('reveal',67/60,body,js,'.wordmark{left:300px;top:325px;font-size:250px}')

    body=title('bank','Download a statement.','bank')
    inner=video('bank-nav-video','bank-nav',0,2.15)+video('bank-statement-video','bank-statement',2.15,2.15)+video('bank-download-video','bank-download',4.30,2.433333)
    inner+=cursor('bank-cursor')+''.join(ring('bank-click-'+str(i)) for i in range(3))
    body+='<div class="screen"><div id="bank-stage" class="screen-stage" data-layout-allow-overflow>'+inner+'</div></div>'
    js='tl.fromTo("#bank-title",{x:-36,opacity:0},{x:0,opacity:1,duration:.24,ease:"power3.out"},0);'
    source=(940,70)
    for i,action in enumerate(info['bank']['actions']):
        target=action['center'];at=[.52,2.67,4.82][i]
        js+=move('bank-cursor',source,target,at)+click('bank-cursor','bank-click-'+str(i),target,at+.28)
        source=target
    js+='tl.to("#bank-stage",{scale:1.10,x:-20,y:-40,duration:.3,ease:"power2.inOut"},2.15);'
    body+=clip('bank-download-result',5.7,1.03,'',5,'downloaded')
    scene('bank',404/60,body,js)

    body=title('search','Find a how-to.','youtube')
    inner=clip('youtube-idle',0,1,image('youtube-page-idle'))+video('youtube-type-video','youtube-type',1,1.5)+video('youtube-search-video','youtube-search',2.5,2.5)+video('youtube-result-video','youtube-results',5,1.733333)
    inner+=cursor('search-cursor')+ring('search-type-ring')+ring('search-click-ring')
    body+='<div class="screen"><div id="search-stage" class="screen-stage" data-layout-allow-overflow>'+inner+'</div></div>'
    query=info['youtube']['actions'][0]['center'];suggestion=info['youtube']['actions'][1]['center']
    js=move('search-cursor',(850,170),query,.57)+click('search-cursor','search-type-ring',query,1.30)+move('search-cursor',query,suggestion,2.77)+click('search-cursor','search-click-ring',suggestion,3.10)
    js+='tl.fromTo("#search-title",{x:-36,opacity:0},{x:0,opacity:1,duration:.24,ease:"power3.out"},0);tl.to("#search-stage",{scale:1,transformOrigin:"50% 0%",x:0,y:0,duration:.3,ease:"power2.inOut"},4.95);'
    body+=clip('search-results-beat',5.0,1.73,'',5,'results')
    js+='tl.to("#search-cursor",{opacity:0,duration:.15},4.8);'
    scene('search',404/60,body,js)

    body=title('mail','Draft an email.','mail')
    inner=video('mail-compose-video','mail-compose',0,1.15)+clip('mail-empty-hold',1.15,2.75,image('mail-state-1'))+video('mail-fill-video','mail-fill',3.90,1.35)+clip('mail-filled-hold',5.25,1.6,image('mail-state-4'))+video('mail-send-video','mail-send',6.85,2.116667)
    inner+=clip('mail-compose-cursor',0,1.15,cursor('compose-cursor')+ring('compose-ring'),3)+clip('mail-send-cursor',6.85,2.116667,cursor('send-cursor')+ring('send-ring'),3)
    body+='<div class="screen"><div id="mail-stage" class="screen-stage" data-layout-allow-overflow>'+inner+'</div></div>'
    body+=clip('draft-original',1.15,.45,'<div class="draft-plate">'+image('mail-draft','panel-image')+'</div>',3,'draft')
    body+=clip('draft-subject',1.60,.60,'<div class="subject-plate">'+image('mail-subject','panel-image')+'</div>',3,'before-edit')
    body+=clip('draft-edited',2.20,1.0,'<div class="subject-plate">'+image('mail-subject-edited','panel-image')+'</div>',3,'edit')
    body+=clip('draft-type',3.20,.70,'<div class="type-plate">'+image('mail-type-focus','panel-image')+'</div>',3,'type-it')
    body+=clip('draft-approval-pointer',3.2,.70,cursor('draft-cursor',True)+ring('draft-ring'),4)
    body+=clip('send-confirmation',5.25,1.6,'<div class="confirm-plate">'+image('mail-confirm-focus','panel-image')+'</div>'+cursor('confirm-cursor',True)+ring('confirm-ring'),3,'approval')
    compose=info['mail']['actions'][0]['center'];send=info['mail']['actions'][-1]['center']
    js=move('compose-cursor',(760,100),compose,.26)+click('compose-cursor','compose-ring',compose,.60)
    js+='launchMove(tl,"#draft-cursor",[1500,570],[960,615],3.21,.24);launchClick(tl,"#draft-cursor","#draft-ring",[960,615],3.55);'
    js+='launchMove(tl,"#confirm-cursor",[1430,690],[990,744],6.13,.25);launchClick(tl,"#confirm-cursor","#confirm-ring",[990,744],6.56);'
    js+=move('send-cursor',(440,450),send,6.94)+click('send-cursor','send-ring',send,7.30)
    js+='tl.to("#mail-stage",{scale:1.1,x:-60,y:-150,duration:.28,ease:"power2.inOut"},3.90);tl.fromTo("#mail-title",{x:-36,opacity:0},{x:0,opacity:1,duration:.24,ease:"power3.out"},0);'
    body+=clip('mail-sent-result',8.0,.966667,'',5,'sent')
    scene('mail',538/60,body,js)

    body='<h1 id="outro-word" class="wordmark">Nudge</h1><p id="outro-line" class="closing-line" data-var-text="tagline" data-hold>Fewer precise clicks.</p><p id="outro-repo" class="repository" data-var-text="repository" data-hold>github.com/mekdimd/nudge</p>'+cursor('outro-cursor')
    js='tl.fromTo("#outro-word",{x:-55,opacity:0},{x:0,opacity:1,duration:.23,ease:"power3.out"},0);tl.fromTo("#outro-line",{y:20,opacity:0},{y:0,opacity:1,duration:.25,ease:"power3.out"},.12);tl.fromTo("#outro-cursor",{x:1510,y:710,scale:1.8,rotation:14},{x:1360,y:390,scale:2.3,rotation:0,opacity:1,duration:.3,ease:"power3.out"},.04);'
    scene('outro',185/60,body,js)

    slots=[('hook',0,202),('reveal',202,67),('bank',269,404),('search',673,404),('mail',1077,538),('outro',1615,185)]
    hosts=''.join(f'<div id="{name}" class="clip" data-composition-id="{name}" data-composition-src="compositions/{name}.html" data-start="{start/60}" data-duration="{frames/60}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>' for name,start,frames in slots)
    (P/'index.html').write_text('''<!doctype html>
<html lang="en" data-composition-variables='[{"id":"tagline","type":"string","label":"Closing line","default":"Fewer precise clicks."},{"id":"repository","type":"string","label":"Repository","default":"github.com/mekdimd/nudge"}]'>
<head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>Nudge launch film</title><link rel="stylesheet" href="assets/film.css"><script src="assets/vendor/gsap.min.js"></script><script src="assets/motion.js"></script><style>html,body{width:1920px;height:1080px;overflow:hidden}#root{position:relative;width:1920px;height:1080px}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="30" data-width="1920" data-height="1080" data-fps="60">'''+hosts+'''<audio id="music" class="clip" src="assets/cloud-dancer.mp3" data-start="0" data-duration="30" data-track-index="2" data-volume="1"></audio></div><script>window.__timelines=window.__timelines||{};window.__timelines.main=gsap.timeline({paused:true});</script></body></html>
''')


if __name__=='__main__':
    main()
