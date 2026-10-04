// Render the existing, saved-event EA-MVP viewer to a deterministic showcase MP4.
// This does not run the simulator or update any synapses.
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const SOURCE = path.join(ROOT, 'visualization', 'ea-mvp-training-playback.html');
const OUTPUT = path.join(ROOT, 'visualization', 'ea-mvp-training-showcase.mp4');
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const FPS = 12;
const WIDTH = 1280;
const HEIGHT = 960;

const training = (from, to, speed, caption) => ({
  kind: 'training', from, to, speed, caption,
  seconds: (to - from) * 0.7 / speed,
});
const test = (stage, arm, durationMs, caption) => ({
  kind: 'test', stage, arm, durationMs, caption, seconds: durationMs / 1000,
});
const still = (seconds, state, caption) => ({ kind: 'still', seconds, state, caption });

const segments = [
  still(2, { stage: 'training', trial: 1, timeMs: 0, speed: 20 },
    'EA-MVP • recorded training and frozen pattern tests'),
  training(1, 351, 20, 'Trials 1–350 • 20× • repeated misses and local synaptic changes'),
  training(351, 359, 5, 'Trials 351–358 • 5× • approaching the first press'),
  training(359, 363, 1, 'Trial 359: first press • 1× • later trials now succeed'),
  still(1, { stage: 'training', trial: 359, timeMs: 560, speed: 1 },
    'First press at trial 359 • seed 907 saved receipt'),
  training(363, 501, 20, 'Trials 363–500 • 20× • saved training finishes'),
  still(1.5, { stage: 'training', trial: 500, timeMs: 680, speed: 20 },
    '500 repeated lane-0 training trials complete • weights now frozen'),
];

const patterns = [
  ['dense_lane_switch_taps', 'Lane switches', 4850],
  ['new_chord_lane_sets', 'Chords', 2100],
  ['new_sequential_hold_lengths', 'Hold notes', 7200],
];
const arms = [
  ['learning_on', 'learned weights'],
  ['shuffled_teaching', 'shuffled-teaching weights'],
  ['untrained', 'initial weights'],
];
for (const [stage, label, durationMs] of patterns) {
  for (const [arm, armLabel] of arms) {
    const caption = `${label} • ${armLabel} • frozen test, 1×`;
    segments.push(still(0.5, { stage, arm, timeMs: 0, speed: 1 }, caption));
    segments.push(test(stage, arm, durationMs, caption));
  }
}
segments.push(still(2, {
  stage: 'new_sequential_hold_lengths', arm: 'untrained', timeMs: 7200, speed: 1,
}, 'Saved-event playback only • shuffled teaching matched learned actions'));

function stateAt(segment, timeSeconds) {
  if (segment.kind === 'still') return segment.state;
  if (segment.kind === 'test') return {
    stage: segment.stage, arm: segment.arm, speed: 1,
    timeMs: Math.min(segment.durationMs, Math.floor(timeSeconds * 1000)),
  };
  const elapsed = Math.min((segment.to - segment.from) * 700 - 1,
    Math.floor(timeSeconds * 1000 * segment.speed));
  return {
    stage: 'training', trial: segment.from + Math.floor(elapsed / 700),
    timeMs: elapsed % 700, speed: segment.speed,
  };
}

async function main() {
  const preview = process.argv.includes('--preview');
  let html = fs.readFileSync(SOURCE, 'utf8');
  const hook = `
    window.__eaShowcase = (state, caption) => {
      stage = state.stage;
      arm = state.arm || 'learning_on';
      timeMs = state.timeMs;
      if (state.trial) trialIndex = state.trial - 1;
      el('stage').value = stage;
      el('arm').value = arm;
      el('speed').value = String(state.speed);
      setPlaying(false);
      render();
      el('play').textContent = 'Pause';
      document.getElementById('showcaseCaption').textContent = caption;
    };
  `;
  const marker = '    render(); requestAnimationFrame(tick);';
  if (!html.includes(marker)) throw new Error('Viewer hook point changed');
  html = html.replace(marker, `${hook}\n${marker}`);
  html = html.replace('</body>', `<div id="showcaseCaption"></div>
  <style>
    #showcaseCaption { position: fixed; left: 0; right: 0; bottom: 0; z-index: 10;
      min-height: 58px; display: flex; align-items: center; justify-content: center;
      padding: 8px 20px; color: #eef3fc; background: rgba(4, 11, 22, .96);
      border-top: 2px solid #79b9fa; font: 600 22px/1.25 system-ui, sans-serif;
      text-align: center; }
  </style></body>`);

  const browser = await chromium.launch({ executablePath: EDGE, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT },
      deviceScaleFactor: 1, reducedMotion: 'reduce' });
    await page.setContent(html, { waitUntil: 'load' });
    if (preview) {
      await page.evaluate(() => window.__eaShowcase(
        { stage: 'training', trial: 359, timeMs: 560, speed: 1 },
        'First press at trial 359 • seed 907 saved receipt'));
      const output = path.join(ROOT, 'work', 'ea-mvp-training-showcase-preview.png');
      await page.screenshot({ path: output });
      console.log(output);
      return;
    }

    const ffmpeg = spawn('ffmpeg', [
      '-y', '-hide_banner', '-loglevel', 'error', '-f', 'image2pipe',
      '-vcodec', 'mjpeg', '-r', String(FPS), '-i', 'pipe:0', '-an',
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25',
      '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUTPUT,
    ], { stdio: ['pipe', 'ignore', 'pipe'] });
    let ffmpegError = '';
    ffmpeg.stderr.on('data', chunk => { ffmpegError += chunk.toString(); });
    const exit = new Promise((resolve, reject) => {
      ffmpeg.on('error', reject);
      ffmpeg.on('close', code => code === 0 ? resolve() : reject(
        new Error(`ffmpeg exited ${code}: ${ffmpegError}`)));
    });
    let frames = 0;
    for (const segment of segments) {
      const count = Math.max(1, Math.round(segment.seconds * FPS));
      for (let frame = 0; frame < count; frame++) {
        const state = stateAt(segment, frame / FPS);
        await page.evaluate(({ state, caption }) =>
          window.__eaShowcase(state, caption), { state, caption: segment.caption });
        const jpeg = await page.screenshot({ type: 'jpeg', quality: 80 });
        if (!ffmpeg.stdin.write(jpeg)) await new Promise(resolve => ffmpeg.stdin.once('drain', resolve));
        frames++;
      }
      console.log(`${segment.caption}: ${count} frames`);
    }
    ffmpeg.stdin.end();
    await exit;
    console.log(`${OUTPUT} (${frames} frames, ${(frames / FPS).toFixed(1)} s)`);
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
