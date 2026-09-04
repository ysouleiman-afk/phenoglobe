/*
 * PhenoGlobe procedural music engine (Web Audio, no samples, no copyright).
 * Each profile = scale + tempo + instrument voices + drum patterns + generative melody.
 */
const Music = (() => {
  let ctx, master, comp, reverb, wetBus;
  let timer = null, profile = null, running = false;
  let step = 0, nextTime = 0, bar = 0;
  let melodyState = { deg: 0, lastFreq: null };
  let droneNodes = [];
  const LOOKAHEAD = 0.12, TICK = 25;

  // ---------- setup ----------
  function init() {
    if (ctx) return;
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -18; comp.ratio.value = 4;
    master = ctx.createGain(); master.gain.value = 0.7;
    master.connect(comp).connect(ctx.destination);
    reverb = ctx.createConvolver(); reverb.buffer = impulse(2.4, 2.8);
    wetBus = ctx.createGain(); wetBus.gain.value = 0.9;
    reverb.connect(wetBus).connect(master);
  }
  function impulse(sec, decay) {
    const len = Math.floor(ctx.sampleRate * sec);
    const buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
    }
    return buf;
  }
  function out(node, wet = 0.3) {
    node.connect(master);
    if (wet > 0) { const g = ctx.createGain(); g.gain.value = wet; node.connect(g).connect(reverb); }
  }
  function noiseBuffer() {
    if (noiseBuffer.buf) return noiseBuffer.buf;
    const len = ctx.sampleRate * 2, buf = ctx.createBuffer(1, len, ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    return (noiseBuffer.buf = buf);
  }
  function noise(t, dur, { type = 'bandpass', freq = 2000, q = 1, vel = 1, attack = 0.001, wet = 0.2 } = {}) {
    const src = ctx.createBufferSource(); src.buffer = noiseBuffer();
    const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(vel, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f).connect(g); out(g, wet); src.start(t); src.stop(t + dur + 0.05);
  }
  function tone(t, dur, { freq = 440, endFreq = null, type = 'sine', vel = 1, attack = 0.002, wet = 0.2 } = {}) {
    const o = ctx.createOscillator(); o.type = type; o.frequency.setValueAtTime(freq, t);
    if (endFreq) o.frequency.exponentialRampToValueAtTime(endFreq, t + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(vel, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); out(g, wet); o.start(t); o.stop(t + dur + 0.05);
  }

  // ---------- melodic voices: (freq, t, dur, vel, opts) ----------
  function pluck(freq, t, dur, vel, { type = 'triangle', cutoff = 3000, floor = 300, decay = 0.5, detune = 0, wet = 0.3, glide = null } = {}) {
    const o = ctx.createOscillator(); o.type = type; o.detune.value = detune;
    if (glide) { o.frequency.setValueAtTime(glide, t); o.frequency.exponentialRampToValueAtTime(freq, t + 0.06); }
    else o.frequency.value = freq;
    const f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.Q.value = 1.2;
    f.frequency.setValueAtTime(cutoff, t); f.frequency.exponentialRampToValueAtTime(floor, t + decay);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(vel, t + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, t + decay);
    o.connect(f).connect(g); out(g, wet); o.start(t); o.stop(t + decay + 0.05);
  }
  const V = {
    koto: (f, t, d, v) => { pluck(f, t, d, v * 0.55, { type: 'triangle', cutoff: 4500, floor: 400, decay: 0.9 }); pluck(f * 2.003, t, d, v * 0.12, { type: 'sine', cutoff: 5000, decay: 0.35 }); },
    oud: (f, t, d, v) => pluck(f, t, d, v * 0.35, { type: 'sawtooth', cutoff: 2200, floor: 320, decay: 0.55 }),
    nylon: (f, t, d, v) => { pluck(f, t, d, v * 0.4, { type: 'triangle', cutoff: 2600, floor: 350, decay: 0.9 }); pluck(f, t, d, v * 0.18, { type: 'sine', cutoff: 3000, decay: 1.1 }); },
    charango: (f, t, d, v) => { pluck(f, t, d, v * 0.3, { type: 'sawtooth', cutoff: 5000, floor: 900, decay: 0.28 }); pluck(f * 2, t + 0.004, d, v * 0.12, { type: 'triangle', cutoff: 6000, decay: 0.2 }); },
    kalimba: (f, t, d, v) => { pluck(f, t, d, v * 0.5, { type: 'sine', cutoff: 3000, decay: 0.7 }); tone(t, 0.25, { freq: f * 2.02, type: 'sine', vel: v * 0.12 }); tone(t, 0.08, { freq: f * 5.8, type: 'sine', vel: v * 0.05 }); },
    piano: (f, t, d, v) => { pluck(f, t, d, v * 0.35, { type: 'sine', cutoff: 4000, floor: 800, decay: 1.3 }); pluck(f * 2, t, d, v * 0.12, { type: 'triangle', cutoff: 5000, decay: 0.8 }); pluck(f * 3, t, d, v * 0.04, { type: 'sine', cutoff: 6000, decay: 0.4 }); },
    riff: (f, t, d, v) => {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f;
      const fl = ctx.createBiquadFilter(); fl.type = 'lowpass'; fl.frequency.setValueAtTime(1400, t); fl.frequency.exponentialRampToValueAtTime(500, t + 0.4);
      const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(v * 0.28, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + Math.max(d, 0.45));
      const trem = ctx.createOscillator(); trem.frequency.value = 6.5; const tg = ctx.createGain(); tg.gain.value = 0.35;
      const vca = ctx.createGain(); vca.gain.value = 0.7; trem.connect(tg).connect(vca.gain);
      o.connect(fl).connect(g).connect(vca); out(vca, 0.35); o.start(t); trem.start(t); o.stop(t + d + 0.6); trem.stop(t + d + 0.6);
    },
    flute: (f, t, d, v, { breath = 0.08, vib = 5 } = {}) => {
      const o = ctx.createOscillator(); o.type = 'sine';
      const glide = melodyState.lastFreq;
      if (glide && profile.melody.slide) { o.frequency.setValueAtTime(glide, t); o.frequency.exponentialRampToValueAtTime(f, t + 0.09); } else o.frequency.value = f;
      const lfo = ctx.createOscillator(); lfo.frequency.value = vib; const lg = ctx.createGain(); lg.gain.value = f * 0.006; lfo.connect(lg).connect(o.frequency);
      const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(v * 0.32, t + 0.06);
      g.gain.setValueAtTime(v * 0.32, t + d - 0.08); g.gain.exponentialRampToValueAtTime(0.0001, t + d + 0.12);
      o.connect(g); out(g, 0.45); o.start(t); lfo.start(t); o.stop(t + d + 0.2); lfo.stop(t + d + 0.2);
      noise(t, d, { type: 'bandpass', freq: f, q: 12, vel: v * breath, attack: 0.05, wet: 0.3 });
    },
    panflute: (f, t, d, v) => V.flute(f, t, d, v, { breath: 0.22, vib: 4.5 }),
    pad: (f, t, d, v) => {
      [-7, 7].forEach(dt => {
        const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = dt;
        const fl = ctx.createBiquadFilter(); fl.type = 'lowpass'; fl.frequency.value = 900;
        const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(v * 0.07, t + 0.6);
        g.gain.setValueAtTime(v * 0.07, t + d - 0.3); g.gain.linearRampToValueAtTime(0.0001, t + d + 0.8);
        o.connect(fl).connect(g); out(g, 0.6); o.start(t); o.stop(t + d + 1);
      });
    },
    bass: (f, t, d, v) => { pluck(f, t, d, v * 0.55, { type: 'triangle', cutoff: 700, floor: 120, decay: Math.max(0.3, d), wet: 0.05 }); tone(t, Math.max(0.25, d * 0.8), { freq: f, type: 'sine', vel: v * 0.35, wet: 0 }); },
  };

  // ---------- drums ----------
  const D = {
    kick: (t, v) => tone(t, 0.32, { freq: 150, endFreq: 42, vel: v * 0.9, wet: 0.05 }),
    bombo: (t, v) => { tone(t, 0.45, { freq: 110, endFreq: 48, vel: v * 0.9, wet: 0.1 }); noise(t, 0.05, { type: 'lowpass', freq: 400, vel: v * 0.3 }); },
    taiko: (t, v) => { tone(t, 0.5, { freq: 120, endFreq: 55, vel: v, wet: 0.35 }); noise(t, 0.08, { type: 'lowpass', freq: 600, vel: v * 0.4, wet: 0.3 }); },
    snare: (t, v) => { noise(t, 0.16, { type: 'bandpass', freq: 1800, q: 0.8, vel: v * 0.6 }); tone(t, 0.1, { freq: 190, endFreq: 150, vel: v * 0.4 }); },
    hat: (t, v) => noise(t, 0.04, { type: 'highpass', freq: 7000, vel: v * 0.25, wet: 0.05 }),
    ohat: (t, v) => noise(t, 0.22, { type: 'highpass', freq: 6500, vel: v * 0.2 }),
    shaker: (t, v) => noise(t, 0.05, { type: 'bandpass', freq: 5500, q: 2, vel: v * 0.18 * (0.8 + Math.random() * 0.4), wet: 0.05 }),
    tek: (t, v) => { noise(t, 0.05, { type: 'bandpass', freq: 4200, q: 1.5, vel: v * 0.5 }); tone(t, 0.035, { freq: 950, vel: v * 0.35 }); },
    doum: (t, v) => tone(t, 0.3, { freq: 135, endFreq: 58, vel: v * 0.95, wet: 0.15 }),
    dha: (t, v) => { tone(t, 0.28, { freq: 118, endFreq: 82, vel: v * 0.8, wet: 0.15 }); noise(t, 0.03, { type: 'bandpass', freq: 3000, vel: v * 0.3 }); },
    na: (t, v) => { tone(t, 0.09, { freq: 720, endFreq: 640, vel: v * 0.35 }); noise(t, 0.03, { type: 'bandpass', freq: 5000, vel: v * 0.25 }); },
    tin: (t, v) => tone(t, 0.16, { freq: 540, vel: v * 0.3, wet: 0.25 }),
    djbass: (t, v) => tone(t, 0.3, { freq: 95, endFreq: 62, vel: v * 0.9, wet: 0.2 }),
    djtone: (t, v) => { tone(t, 0.15, { freq: 260, endFreq: 230, vel: v * 0.5, wet: 0.2 }); noise(t, 0.02, { type: 'bandpass', freq: 2500, vel: v * 0.2 }); },
    djslap: (t, v) => { noise(t, 0.08, { type: 'highpass', freq: 2200, vel: v * 0.55 }); tone(t, 0.03, { freq: 420, vel: v * 0.3 }); },
    conga: (t, v) => tone(t, 0.2, { freq: 235, endFreq: 195, vel: v * 0.55, wet: 0.2 }),
    congaHi: (t, v) => tone(t, 0.14, { freq: 330, endFreq: 290, vel: v * 0.45, wet: 0.2 }),
    clave: (t, v) => tone(t, 0.06, { freq: 2100, vel: v * 0.35, wet: 0.3 }),
    wood: (t, v) => tone(t, 0.05, { freq: 1250, vel: v * 0.35, wet: 0.3 }),
    clap: (t, v) => [0, 0.012, 0.026].forEach((o, i) => noise(t + o, 0.12 - i * 0.02, { type: 'bandpass', freq: 1300, q: 1.2, vel: v * 0.4, wet: 0.35 })),
    tamb: (t, v) => { noise(t, 0.12, { type: 'highpass', freq: 6000, vel: v * 0.3 }); tone(t, 0.06, { freq: 5200, vel: v * 0.08 }); tone(t, 0.06, { freq: 7300, vel: v * 0.06 }); },
    calabash: (t, v) => { tone(t, 0.25, { freq: 170, endFreq: 70, vel: v * 0.8, wet: 0.2 }); noise(t, 0.03, { type: 'lowpass', freq: 900, vel: v * 0.5 }); },
  };

  // ---------- profiles ----------
  const P = {
    east_asian: {
      title: 'Koto & bamboo flute', search: 'traditional Chinese guzheng Japanese koto music',
      bpm: 82, spb: 16, root: 293.66, scale: [0, 2, 4, 7, 9],
      melody: { voice: 'koto', density: 0.42, rest: 0.25, range: 10, grace: 0.3, octave: 1 },
      bass: { voice: 'koto', octave: -1, pattern: 'x.......x...x...' },
      lead2: { voice: 'flute', every: 2, octave: 1, len: 3 },
      drums: [{ hit: 'taiko', p: 'x.......x.......', v: 0.5 }, { hit: 'wood', p: '....x.....x...x.', v: 0.5 }, { hit: 'shaker', p: '..x...x...x...x.', v: 0.4 }],
    },
    southeast_asian: {
      title: 'Gamelan & bamboo flute', search: 'Indonesian gamelan Filipino kulintang traditional music',
      bpm: 88, spb: 16, root: 261.63, scale: [0, 1, 5, 7, 8],
      melody: { voice: 'flute', density: 0.35, rest: 0.3, range: 7, octave: 1, minLen: 2 },
      ostinato: { voice: 'kalimba', octave: 0, degs: [0, 2, 1, 2, 0, 3, 1, 2, 0, 2, 4, 2, 0, 3, 1, 2], soft: 0.45 },
      bass: { voice: 'kalimba', octave: -1, pattern: 'x.......x.......' },
      drums: [{ hit: 'taiko', p: 'x.......x.......', v: 0.4 }, { hit: 'wood', p: '....x.......x...', v: 0.5 }, { hit: 'shaker', p: '..x...x...x...x.', v: 0.3 }],
    },
    south_asian: {
      title: 'Bansuri, tanpura & tabla', search: 'Indian classical bansuri flute tabla raga',
      bpm: 92, spb: 16, root: 220, scale: [0, 1, 4, 5, 7, 8, 11],
      melody: { voice: 'flute', density: 0.5, rest: 0.18, range: 9, slide: true, octave: 1, minLen: 2 },
      drone: { octave: 0 },
      drums: [{ hit: 'dha', p: 'x...x...x...x...', v: 0.9 }, { hit: 'na', p: '..x...x...x...x.', v: 0.7 }, { hit: 'tin', p: '.x.....x.x.....x', v: 0.5 }],
    },
    west_african: {
      title: 'Kalimba & djembe (12/8)', search: 'West African kora djembe traditional music',
      bpm: 112, spb: 12, root: 261.63, scale: [0, 3, 5, 7, 10],
      melody: { voice: 'kalimba', density: 0.7, rest: 0.1, range: 8, octave: 1 },
      ostinato: { voice: 'kalimba', octave: 0, degs: [0, 2, 4, 2, 3, 2, 4, 2, 0, 2, 4, 3] },
      bass: { voice: 'bass', octave: -1, pattern: 'x.....x..x..' },
      drums: [{ hit: 'djbass', p: 'x.....x.....', v: 1 }, { hit: 'djtone', p: '..xx....x.x.', v: 0.8 }, { hit: 'djslap', p: '.....x...x.x', v: 0.9 }, { hit: 'shaker', p: 'xxxxxxxxxxxx', v: 0.5 }],
    },
    european: {
      title: 'Piano & strings', search: 'European folk orchestral traditional music',
      bpm: 100, spb: 16, root: 261.63, scale: [0, 2, 4, 5, 7, 9, 11],
      chords: [[0, 4, 7, 12], [-5, -1, 2, 7], [-3, 0, 4, 7], [-7, -3, 0, 5]],
      arp: { voice: 'piano', pattern: 'x.x.x.x.x.x.x.x.', octave: 0 },
      pad: { voice: 'pad', octave: -1 },
      melody: { voice: 'piano', density: 0.38, rest: 0.3, range: 9, octave: 1, chordy: true },
      bass: { voice: 'bass', octave: -2, pattern: 'x.......x.......' },
      drums: [{ hit: 'kick', p: 'x.......x.......', v: 0.5 }, { hit: 'hat', p: '..x...x...x...x.', v: 0.4 }],
    },
    mena: {
      title: 'Oud & darbuka (Hijaz)', search: 'Arabic oud darbuka traditional music',
      bpm: 104, spb: 16, root: 293.66, scale: [0, 1, 4, 5, 7, 8, 10],
      melody: { voice: 'oud', density: 0.6, rest: 0.15, range: 9, trem: 0.25, octave: 0 },
      bass: { voice: 'oud', octave: -1, pattern: 'x.......x.....x.' },
      drone: { octave: -1, soft: true },
      drums: [{ hit: 'doum', p: 'x.......x.......', v: 1 }, { hit: 'tek', p: '..x...x.....x...', v: 0.8 }, { hit: 'tek', p: '...............x', v: 0.4 }, { hit: 'tamb', p: '.x.x.x.x.x.x.x.x', v: 0.25 }],
    },
    latin: {
      title: 'Nylon guitar, clave & congas', search: 'Latin American son cumbia traditional music',
      bpm: 114, spb: 16, root: 220, scale: [0, 2, 3, 5, 7, 8, 10],
      chords: [[0, 3, 7, 12], [-2, 2, 5, 10], [-4, 0, 3, 8], [-5, -1, 2, 7]],
      arp: { voice: 'nylon', pattern: 'x.xx.x.xx.x.x.xx', octave: 0 },
      melody: { voice: 'nylon', density: 0.45, rest: 0.25, range: 9, octave: 1, chordy: true },
      bass: { voice: 'bass', octave: -1, pattern: '......x.......x.' },
      drums: [{ hit: 'clave', p: 'x..x..x...x.x...', v: 0.8 }, { hit: 'conga', p: '....x.......x.x.', v: 0.7 }, { hit: 'congaHi', p: '..x.......x.....', v: 0.6 }, { hit: 'shaker', p: 'x.x.x.x.x.x.x.x.', v: 0.5 }],
    },
    andean: {
      title: 'Pan flute & charango', search: 'Andean pan flute charango traditional music',
      bpm: 96, spb: 16, root: 329.63, scale: [0, 3, 5, 7, 10],
      melody: { voice: 'panflute', density: 0.5, rest: 0.2, range: 8, octave: 0, minLen: 2 },
      ostinato: { voice: 'charango', octave: 0, degs: [0, 2, 4, 2, 0, 2, 4, 2, 1, 3, 4, 3, 1, 3, 4, 3] },
      bass: { voice: 'bass', octave: -1, pattern: 'x.......x.......' },
      drums: [{ hit: 'bombo', p: 'x...x...x...x.x.', v: 0.7 }, { hit: 'shaker', p: '..x...x...x...x.', v: 0.5 }],
    },
    mediterranean: {
      title: 'Guitar, oud & tambourine', search: 'Mediterranean Greek Andalusian traditional music',
      bpm: 98, spb: 16, root: 246.94, scale: [0, 2, 3, 5, 7, 8, 11],
      chords: [[0, 3, 7, 12], [-2, 2, 5, 10], [-4, 0, 3, 8], [-5, -1, 2, 7]],
      arp: { voice: 'nylon', pattern: 'x..x..x.x..x..x.', octave: 0 },
      melody: { voice: 'oud', density: 0.5, rest: 0.2, range: 9, trem: 0.15, octave: 1, chordy: true },
      bass: { voice: 'bass', octave: -1, pattern: 'x.......x.......' },
      drums: [{ hit: 'doum', p: 'x.......x.......', v: 0.7 }, { hit: 'tamb', p: '....x.......x...', v: 0.5 }, { hit: 'tek', p: '......x.......x.', v: 0.5 }],
    },
    sahel: {
      title: 'Desert blues guitar & calabash', search: 'Tuareg desert blues Malian traditional music',
      bpm: 88, spb: 16, root: 220, scale: [0, 3, 5, 7, 10],
      melody: { voice: 'riff', density: 0.55, rest: 0.2, range: 7, octave: 0 },
      ostinato: { voice: 'riff', octave: -1, degs: [0, 0, 2, 0, 3, 0, 2, 4, 0, 0, 2, 0, 3, 2, 0, 0], soft: 0.6 },
      drums: [{ hit: 'calabash', p: 'x.....x...x.....', v: 0.9 }, { hit: 'clap', p: '....x.......x...', v: 0.5 }, { hit: 'shaker', p: 'x.x.x.x.x.x.x.x.', v: 0.35 }],
    },
    caucasus: {
      title: 'Duduk & lezginka drum', search: 'Caucasian folk music duduk lezginka',
      bpm: 132, spb: 12, root: 220, scale: [0, 2, 3, 5, 7, 8, 11],
      melody: { voice: 'flute', density: 0.4, rest: 0.25, range: 8, slide: true, octave: 0, minLen: 3 },
      drone: { octave: -1, soft: true },
      ostinato: { voice: 'charango', octave: -1, degs: [0, 0, 4, 0, 0, 4, 2, 2, 4, 2, 2, 4], soft: 0.45 },
      drums: [{ hit: 'doum', p: 'x..x..x..x..', v: 0.9 }, { hit: 'tek', p: '.xx.xx.xx.xx', v: 0.55 }, { hit: 'clap', p: '......x.....', v: 0.4 }],
    },
    eurasian: {
      title: 'Steppe flute & drone', search: 'Central Asian Turkic dombra throat singing music',
      bpm: 90, spb: 16, root: 246.94, scale: [0, 2, 3, 5, 7, 8, 10],
      melody: { voice: 'flute', density: 0.45, rest: 0.2, range: 8, slide: true, octave: 1, minLen: 2 },
      ostinato: { voice: 'charango', octave: -1, degs: [0, 4, 0, 4, 0, 4, 0, 4, 2, 4, 2, 4, 0, 4, 0, 4], soft: 0.5 },
      drone: { octave: -1 },
      drums: [{ hit: 'taiko', p: 'x.....x.x.......', v: 0.6 }, { hit: 'shaker', p: '..x...x...x...x.', v: 0.35 }],
    },
  };

  // ---------- generative helpers ----------
  const semi = (root, s) => root * Math.pow(2, s / 12);
  function degFreq(deg, octave = 0) {
    const sc = profile.scale, n = sc.length;
    const oct = Math.floor(deg / n), idx = ((deg % n) + n) % n;
    return semi(profile.root, sc[idx] + 12 * (oct + octave));
  }
  function chordNow() { return profile.chords ? profile.chords[bar % profile.chords.length] : null; }
  function stepMelody(t, stepDur, s) {
    const m = profile.melody;
    if (melodyState.hold > 0) { melodyState.hold--; return; }
    const strong = s % (profile.spb / 4) === 0;
    if (Math.random() > m.density + (strong ? 0.25 : 0)) return;
    if (Math.random() < m.rest && !strong) return;
    const moves = [-2, -1, -1, 0, 1, 1, 2, 3, -3];
    let deg = melodyState.deg + moves[Math.floor(Math.random() * moves.length)];
    if (strong && Math.random() < 0.3) deg = 0;
    deg = Math.max(-2, Math.min(m.range, deg));
    melodyState.deg = deg;
    let f = degFreq(deg, m.octave);
    if (m.chordy && strong && chordNow()) { const ch = chordNow(); f = semi(profile.root, ch[Math.floor(Math.random() * ch.length)] + 12 * m.octave); }
    const len = (m.minLen || 1) + Math.floor(Math.random() * 3);
    melodyState.hold = len - 1;
    const dur = stepDur * len * 0.95, vel = strong ? 1 : 0.75;
    const voice = V[m.voice];
    if (m.grace && Math.random() < m.grace) voice(degFreq(deg + 1, m.octave), t - 0.05, 0.05, vel * 0.5);
    if (m.trem && Math.random() < m.trem) { for (let i = 0; i < len * 2; i++) voice(f, t + i * stepDur / 2, stepDur / 2, vel * (i ? 0.6 : 1)); }
    else voice(f, t, dur, vel);
    melodyState.lastFreq = f;
  }
  function schedule(s, t, stepDur) {
    const spb = profile.spb;
    profile.drums.forEach(d => { const c = d.p[s % spb]; if (c === 'x') D[d.hit](t, d.v); });
    if (profile.bass && profile.bass.pattern[s % spb] === 'x') {
      const ch = chordNow(); const f = ch ? semi(profile.root, ch[0] + 12 * profile.bass.octave) : degFreq(0, profile.bass.octave);
      V[profile.bass.voice](f, t, stepDur * 3, 0.9);
    }
    if (profile.arp && profile.arp.pattern[s % spb] === 'x') {
      const ch = chordNow(); const note = ch[Math.floor(s / 2) % ch.length + (s % 4 === 3 ? 0 : 0)];
      V[profile.arp.voice](semi(profile.root, ch[(s >> 1) % ch.length] + 12 * profile.arp.octave), t, stepDur * 2, 0.55);
    }
    if (profile.ostinato) { const o = profile.ostinato; V[o.voice](degFreq(o.degs[s % o.degs.length], o.octave), t, stepDur, o.soft || 0.5); }
    if (profile.pad && s % spb === 0) { const ch = chordNow(); ch.slice(0, 3).forEach(n => V.pad(semi(profile.root, n + 12 * profile.pad.octave), t, stepDur * spb, 1)); }
    if (profile.lead2 && s % spb === 0 && bar % profile.lead2.every === 1) {
      const l = profile.lead2, deg = [0, 2, 4, 3][bar % 4]; V[l.voice](degFreq(deg, l.octave), t, stepDur * spb * l.len / 4, 0.5);
    }
    stepMelody(t, stepDur, s);
  }
  function startDrone() {
    const d = profile.drone; if (!d) return;
    [0, 7].forEach((iv, i) => {
      const o = ctx.createOscillator(); o.type = i ? 'triangle' : 'sawtooth'; o.frequency.value = semi(profile.root, iv + 12 * d.octave);
      const fl = ctx.createBiquadFilter(); fl.type = 'lowpass'; fl.frequency.value = 420;
      const lfo = ctx.createOscillator(); lfo.frequency.value = 0.09; const lg = ctx.createGain(); lg.gain.value = 180; lfo.connect(lg).connect(fl.frequency);
      const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, ctx.currentTime); g.gain.linearRampToValueAtTime(d.soft ? 0.05 : 0.09, ctx.currentTime + 2);
      o.connect(fl).connect(g); out(g, 0.5); o.start(); lfo.start(); droneNodes.push(o, lfo, g);
    });
  }
  function stopDrone() {
    droneNodes.forEach(n => { if (n.gain) n.gain.linearRampToValueAtTime(0.0001, ctx.currentTime + 0.8); if (n.stop) n.stop(ctx.currentTime + 1); });
    droneNodes = [];
  }
  function tick() {
    const stepDur = 60 / profile.bpm / (profile.spb / 4);
    while (nextTime < ctx.currentTime + LOOKAHEAD) {
      schedule(step, nextTime, stepDur);
      nextTime += stepDur; step++;
      if (step % profile.spb === 0) bar++;
    }
  }

  // ---------- public ----------
  function play(name) {
    init(); if (ctx.state === 'suspended') ctx.resume();
    stop();
    profile = P[name] || P.european;
    step = 0; bar = 0; melodyState = { deg: 0, lastFreq: null, hold: 0 };
    nextTime = ctx.currentTime + 0.1;
    startDrone();
    timer = setInterval(tick, TICK); running = true;
    return profile;
  }
  function stop() { if (timer) clearInterval(timer); timer = null; running = false; stopDrone(); }
  function setVolume(v) { init(); master.gain.linearRampToValueAtTime(v, ctx.currentTime + 0.1); }
  return { play, stop, setVolume, isPlaying: () => running, profiles: P };
})();
