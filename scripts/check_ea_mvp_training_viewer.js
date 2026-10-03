// Lightweight offline interaction check. It does not open a browser.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const html = fs.readFileSync('visualization/ea-mvp-training-playback.html', 'utf8');
const data = html.match(/<script type="application\/json" id="ea-data">([\s\S]*?)<\/script>/);
const code = html.match(/<script>([\s\S]*?)<\/script>/);
assert(data && code);

const noop = () => {};
const context2d = new Proxy({}, {get: (obj, key) => obj[key] ?? noop});
const elements = new Map();
for (const id of ['ea-data', 'field', 'weightChart', 'stage', 'arm', 'speed', 'play',
                   'trialBox', 'trialLabel', 'trial', 'firstPress', 'sceneTitle',
                   'clock', 'weightRows', 'headline', 'description', 'judgement',
                   'keyAction', 'teaching', 'progress', 'receipt']) {
  elements.set(id, {
    id, textContent: id === 'ea-data' ? data[1] : '', innerHTML: '',
    value: id === 'speed' ? '1' : '', clientWidth: 410, clientHeight: id === 'field' ? 435 : 150,
    listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; },
    getContext() { return context2d; },
  });
}
const raf = [];
const sandbox = {
  document: {getElementById: id => elements.get(id)},
  window: {devicePixelRatio: 1, addEventListener: noop},
  performance: {now: () => 0},
  requestAnimationFrame: callback => raf.push(callback),
  console,
};
vm.runInNewContext(code[1], sandbox, {filename: 'fly_training_playback.html'});
assert.equal(elements.get('headline').textContent, 'Training trial 1 of 500');
assert.equal(elements.get('judgement').textContent, 'Pending');
elements.get('firstPress').listeners.click();
assert.equal(elements.get('headline').textContent, 'Training trial 359 of 500');
elements.get('play').listeners.click();
let stamp = 0;
for (let i = 0; i < 6; i++) {
  stamp += 100;
  raf.shift()(stamp);
}
assert.equal(elements.get('judgement').textContent, 'PERFECT');
assert.equal(elements.get('teaching').textContent, 'Silent after PERFECT');
elements.get('trial').listeners.input({target: {value: '1'}});
elements.get('play').listeners.click();
for (let i = 0; i < 6; i++) {
  stamp += 100;
  raf.shift()(stamp);
}
stamp += 50;
raf.shift()(stamp);
assert.equal(elements.get('judgement').textContent, 'MISS');
assert.equal(elements.get('teaching').textContent, '3 DAN spikes; 7 weights changed');
elements.get('stage').listeners.change({target: {value: 'new_chord_lane_sets'}});
assert.equal(elements.get('headline').textContent, 'Frozen evaluation · Chords');
assert.equal(elements.get('teaching').textContent, 'OFF · weights frozen');
elements.get('arm').listeners.change({target: {value: 'untrained'}});
assert.equal(elements.get('keyAction').textContent, 'None yet');
elements.get('stage').listeners.change({target: {value: 'new_sequential_hold_lengths'}});
assert.equal(elements.get('headline').textContent, 'Frozen evaluation · Hold notes');
console.log('viewer interaction PASS: MISS update, first press, chords, holds, control arm');
