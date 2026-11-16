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
assert(source.includes(example.goal), 'The goal matches the README reference.');
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
  const samples = [];
  for (const time of [17.7, 18.7, 19.1, 19.5, 19.9, 20.3, 20.95, 21.95, 22.9, 24.95, 25.87, 26.02, 26.17, 26.24]) samples.push(await sample(time));
  const at = time => samples.find(s => s.time === time);
  const percentages = example.ranked.map(row => Math.round(row.probability * 100));
  for (let i=0;i<4;i++) {
    assert.equal(at(18.7).bars[i], 0, 'Bars start empty.');
    for (const [a,b] of [[19.1,19.5],[19.5,19.9],[19.9,20.3]]) assert(at(a).bars[i] < at(b).bars[i], 'Every candidate bar grows.');
    assert(Math.abs(at(20.3).bars[i] - percentages[i]/100) < .0001);
  }
  assert.deepEqual(at(20.3).values, percentages);
  assert.equal(at(20.3).winner, 0, 'Scoring finishes before selection.');
  assert.equal(at(20.95).winner, 1);
  assert.equal(at(20.95).rows[0], 1);
  assert(at(20.95).rows.slice(1).every(v => v < .5), 'Other choices dim.');
  assert.equal(at(21.95).dash, 0, 'Connector finishes before the reading hold.');
  assert.equal(at(21.95).target, 1);
  for (const time of [21.95,22.9,24.95]) {
    assert.equal(at(time).selected, 1);
    assert.equal(at(time).cursor.opacity, 0, 'Cursor stays hidden throughout scoring and the reading hold.');
  }
  assert.deepEqual(at(21.95).bars, at(24.95).bars);
  const rect=at(21.95).card;
  assert(rect.x>=96 && rect.y>=54 && rect.right<=1824 && rect.bottom<=1026, 'Scoring stays within action-safe bounds.');
  assert(at(26.02).cursor.x < at(25.87).cursor.x, 'Cursor resumes only after the hold.');
  assert(Math.abs(at(26.17).cursor.x-137.062)<.01 && Math.abs(at(26.17).cursor.y-534.275)<.01);
  assert(at(26.24).cursor.scale < 1, 'The click has visible feedback.');
  const reverse = await sample(19.5);
  assert.deepEqual(reverse.bars, at(19.5).bars, 'Seeking backward preserves the scoring animation.');
  assert.deepEqual(reverse.values, at(19.5).values);
  const root = await readFile(join(project, 'index.html'), 'utf8');
  assert(root.includes('data-start="72.07"'), 'Click audio follows the delayed click.');
  assert(source.includes('data-start="22.9" data-duration="6.1"'), 'Recorded action source retains its click offset.');
  const out=join(project,'.hyperframes/artifacts');
  await mkdir(out,{recursive:true});
  await writeFile(join(out,'jev-motion-check.json'),JSON.stringify({ok:true,samples},null,2)+'\n');
  console.log('Jev motion passed: growing scores, mint selection, connector, reading hold, delayed click and reverse seeking.');
} finally {
  await browser.close();
  await rm(temporary,{recursive:true,force:true});
}
