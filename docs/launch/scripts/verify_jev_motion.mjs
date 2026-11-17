// Verify the scoring hold and cursor handoff on the scene's paused timeline.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

const project = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const source = await readFile(join(project, 'compositions/jev.html'), 'utf8');
const example = JSON.parse(await readFile(join(project, 'assets/desktop/jev-example.json'), 'utf8'));
const scene = source.replace(/^<template>/, '').replace(/<\/template>\s*$/, '');
const temporary = await mkdtemp(join(tmpdir(), 'nudge-motion-'));
const pageFile = join(temporary, 'motion.html');
await writeFile(pageFile, '<!doctype html><html><head><base href="' + pathToFileURL(project + '/').href + '"><link rel="stylesheet" href="assets/film.css"><script src="assets/vendor/gsap.min.js"></script><script src="assets/motion.js"></script></head><body><script>window.__timelines={};</script>' + scene + '</body></html>');
const browser = await chromium.launch({ channel: 'chrome', args: ['--allow-file-access-from-files'] });
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(pathToFileURL(pageFile).href);
  await page.evaluate(() => document.fonts.ready);
  assert.deepEqual(errors, []);
  const sample = async time => page.evaluate(time => {
    window.__timelines.jev.seek(time, false);
    const opacity = id => Number(gsap.getProperty('#' + id, 'opacity'));
    const names = ['labels', 'views', 'projects', 'milestones'];
    return {
      time,
      bars: names.map(name => Number(gsap.getProperty('#jev-bar-' + name, 'scaleX'))),
      values: names.map(name => Number(document.querySelector('#jev-prob-' + name).textContent)),
      rows: names.map(name => opacity('jev-score-' + name)),
      winner: Number(gsap.getProperty('#jev-score-labels .row-fill', 'opacity')),
      selected: opacity('jev-score-selected'),
      target: opacity('jev-score-target'),
      dash: Number(gsap.getProperty('#jev-score-connector', 'strokeDashoffset')),
      cursor: { x: Number(gsap.getProperty('#jev-action-cursor', 'x')), y: Number(gsap.getProperty('#jev-action-cursor', 'y')), opacity: opacity('jev-action-cursor'), scale: Number(gsap.getProperty('#jev-action-cursor', 'scaleX')) },
      card: (() => {const r=document.querySelector('#jev-score-card').getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom};})(),
    };
  }, time);
  assert(!source.includes('jev-peek-detail'), 'Peek stays in the full Nudge bar.');
  const peek = await page.evaluate(() => {
    const tl=window.__timelines.jev;
    tl.seek(.2,false);
    const before=Number(gsap.getProperty('#jev-enable-stage','scaleX'));
    tl.seek(1.6,false);
    return {before,after:Number(gsap.getProperty('#jev-enable-stage','scaleX')),x:Number(gsap.getProperty('#peek-human','x')),y:Number(gsap.getProperty('#peek-human','y'))};
  });
  assert(peek.after > peek.before && Math.abs(peek.after-1.55)<.001, 'Camera zooms into Peek.');
  assert(Math.abs(peek.x-1223.5)<.01 && Math.abs(peek.y-57.8)<.01, 'Cursor clicks Peek in the same window.');
  const timing = await page.evaluate(() => {
    const tweens=window.__timelines.jev.getChildren(true,true,false);
    const find=(id,predicate)=>tweens.find(t=>t.targets().includes(document.getElementById(id)) && predicate(t.vars));
    const bar=find('jev-bar-labels',v=>v.scaleX>0);
    const move=find('jev-action-cursor',v=>typeof v.x==='number' && Math.abs(v.x-137.062)<.01 && v.duration>0);
    const launch=find('jev-action-cursor',v=>v.opacity===1 && v.x===860);
    const hold=document.getElementById('jev-scoring').dataset.scoreHold.split(',').map(Number);
    const video=document.getElementById('jev-action-video');
    return {
      barStart:bar.startTime(),barEnd:bar.endTime(),holdStart:hold[0],holdEnd:hold[1],
      moveStart:launch.startTime(),click:move.endTime(),sourceStart:Number(video.dataset.start),
      goal:document.querySelector('#jev-score-goal strong').textContent.trim(),
    };
  });
  assert(timing.goal.length>0, 'The scoring card shows a goal.');
  assert(timing.barEnd<timing.holdStart && timing.holdStart<timing.holdEnd);
  assert(timing.holdEnd<timing.moveStart && timing.moveStart<timing.click, 'The cursor waits until scoring and its reading hold finish.');
  const barTimes=[0,.25,.5,.75,1].map(f=>timing.barStart+(timing.barEnd-timing.barStart)*f);
  const samples=[];
  for (const time of [...barTimes,timing.holdStart,(timing.holdStart+timing.holdEnd)/2,timing.holdEnd-.01,timing.moveStart,timing.moveStart+(timing.click-timing.moveStart)/2,timing.click,timing.click+.07]) samples.push(await sample(time));
  const at=time=>samples.find(s=>Math.abs(s.time-time)<.00001);
  const percentages=example.ranked.map(row=>Math.round(row.probability*100));
  for (let i=0;i<4;i++) {
    assert.equal(at(barTimes[0]).bars[i],0,'Bars start empty.');
    for(let j=1;j<barTimes.length;j++) assert(at(barTimes[j-1]).bars[i]<at(barTimes[j]).bars[i],'Every candidate bar grows.');
    assert(Math.abs(at(timing.barEnd).bars[i]-percentages[i]/100)<.0001);
  }
  assert.deepEqual(at(timing.barEnd).values,percentages);
  const held=at(timing.holdStart);
  assert.equal(at(timing.barEnd).winner,0,'Scoring finishes before selection.');
  assert.equal(held.winner,1);
  assert.equal(held.rows[0],1);
  assert(held.rows.slice(1).every(v=>v<.5),'Other choices dim.');
  assert.equal(held.dash,0,'The connector finishes before the reading hold.');
  assert.equal(held.target,1);
  for(const time of [timing.holdStart,(timing.holdStart+timing.holdEnd)/2,timing.holdEnd-.01]) {
    assert.equal(at(time).selected,1);
    assert.equal(at(time).cursor.opacity,0,'The cursor stays hidden during the reading hold.');
    assert.deepEqual(at(time).bars,held.bars);
  }
  const rect=held.card;
  assert(rect.x>=96 && rect.y>=54 && rect.right<=1824 && rect.bottom<=1026,'Scoring stays within action-safe bounds.');
  assert(at(timing.moveStart+(timing.click-timing.moveStart)/2).cursor.x<at(timing.moveStart).cursor.x,'The cursor resumes after the hold.');
  assert(Math.abs(at(timing.click).cursor.x-137.062)<.01 && Math.abs(at(timing.click).cursor.y-534.275)<.01);
  assert(at(timing.click+.07).cursor.scale<1,'The click has visible feedback.');
  const reverse=await sample(barTimes[2]);
  assert.deepEqual(reverse.bars,at(barTimes[2]).bars,'Seeking backward preserves the scoring animation.');
  assert.deepEqual(reverse.values,at(barTimes[2]).values);
  const root=await readFile(join(project,'index.html'),'utf8');
  const sceneStart=Number(root.match(/id="jev"[^>]*data-start="([0-9.]+)"/)[1]);
  const cue=Number(root.match(/id="cue-19"[^>]*data-start="([0-9.]+)"/)[1]);
  assert(Math.abs(cue-sceneStart-timing.click)<.001,'Click audio follows the cursor click.');
  assert(Math.abs(timing.click-timing.sourceStart-3.27)<.001,'The recorded click retains its source offset.');
  const out=join(project,'.hyperframes/artifacts');
  await mkdir(out,{recursive:true});
  await writeFile(join(out,'jev-motion-check.json'),JSON.stringify({ok:true,timing,samples},null,2)+'\n');
  console.log('Jev motion passed: growing scores, mint selection, connector, reading hold, delayed click and reverse seeking.');
} finally {
  await browser.close();
  await rm(temporary,{recursive:true,force:true});
}
