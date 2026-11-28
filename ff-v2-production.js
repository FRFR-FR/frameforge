/* FrameForge V2 reusable production workflows: shot recipes, source adapters,
   procedural graphics, rights-aware audio cataloguing and editable shot assembly. */
(function (root) {
  'use strict';

  const Core = root.FFV2Core || (typeof require === 'function' ? require('./ff-v2-core.js') : null);
  const Director = root.FFV2Director || (typeof require === 'function' ? require('./ff-v2-director.js') : null);
  const MAX_RESULTS = 8;
  const MAX_LABELS = 8;

  const RECIPES = {
    character_reveal: {
      label: 'Character reveal',
      layout: 'hero_reveal',
      media_priority: ['character_cutout', 'three_d', 'procedural_2d'],
      camera: 'Begin wide; push in toward the subject, then hold on the defining detail.',
      action: 'Reveal silhouette first, then face or key prop. Keep the subject readable against a designed background.',
      motion: 'slow_push_in',
      effects: ['glow'],
      transition: { type: 'zoom', direction: 'in', duration_frames: 12 },
      overlay: 'Name or role label only when it adds context.',
      duration_scale: 1
    },
    comparison: {
      label: 'Side-by-side comparison',
      layout: 'split_comparison',
      media_priority: ['procedural_2d', 'character_cutout', 'three_d'],
      camera: 'Locked split-screen; use matching scale and aligned reference points.',
      action: 'Reveal one side, then the other; highlight only the differences supported by the brief.',
      motion: 'staggered_reveal',
      effects: ['vignette'],
      transition: { type: 'wipe', direction: 'left', duration_frames: 10 },
      overlay: 'Two concise labels and a neutral comparison axis.',
      duration_scale: 1.15
    },
    explainer: {
      label: 'Step-by-step explainer',
      layout: 'sequential_steps',
      media_priority: ['procedural_2d', 'three_d', 'typography'],
      camera: 'Track the active step; move the camera only when the mechanism changes.',
      action: 'Reveal components in causal order and keep inactive elements visually quiet.',
      motion: 'sequential_build',
      effects: ['glow'],
      transition: { type: 'fade', direction: 'in', duration_frames: 8 },
      overlay: 'Short step labels; avoid repeating full narration.',
      duration_scale: 1.1
    },
    diagram: {
      label: 'Technical diagram',
      layout: 'annotated_system',
      media_priority: ['procedural_2d', 'three_d', 'typography'],
      camera: 'Start on the full system, then pan or zoom to the component being discussed.',
      action: 'Show connections, direction and component relationships; label each element once.',
      motion: 'draw_connections',
      effects: ['glow'],
      transition: { type: 'wipe', direction: 'right', duration_frames: 8 },
      overlay: 'Use a legend when more than one connection type appears.',
      duration_scale: 1.2
    },
    map: {
      label: 'Map / spatial sequence',
      layout: 'map_route',
      media_priority: ['procedural_2d', 'source_footage', 'three_d'],
      camera: 'Establish the whole area before following a route or changing location.',
      action: 'Animate only routes or locations supported by the production brief and cited sources.',
      motion: 'route_draw',
      effects: ['vignette'],
      transition: { type: 'zoom', direction: 'in', duration_frames: 10 },
      overlay: 'Keep place names and map scale legible.',
      duration_scale: 1.15
    },
    timeline: {
      label: 'Chronological timeline',
      layout: 'chronology',
      media_priority: ['procedural_2d', 'source_footage', 'typography'],
      camera: 'Move consistently along the time axis and pause at each event.',
      action: 'Reveal dated events in order; distinguish confirmed dates from approximate periods.',
      motion: 'timeline_pan',
      effects: ['vignette'],
      transition: { type: 'wipe', direction: 'left', duration_frames: 10 },
      overlay: 'Date, event and source marker; never imply unsupported precision.',
      duration_scale: 1.25
    },
    evidence_callout: {
      label: 'Evidence callout',
      layout: 'source_evidence',
      media_priority: ['source_footage', 'procedural_2d', 'typography'],
      camera: 'Hold the cited source in frame; zoom to the supplied page or timecode when available.',
      action: 'Separate the source itself from editorial annotations and interpretation.',
      motion: 'evidence_focus',
      effects: [],
      transition: { type: 'fade', direction: 'in', duration_frames: 6 },
      overlay: 'Source title and pinpoint location; label reconstructions as illustrations.',
      duration_scale: 1
    },
    gameplay_overlay: {
      label: 'Gameplay / UI overlay',
      layout: 'gameplay_hud',
      media_priority: ['source_footage', 'three_d', 'procedural_2d'],
      camera: 'Preserve the gameplay camera; crop or punch in only to explain a specific mechanic.',
      action: 'Use restrained callouts, path traces or timing markers tied to visible gameplay events.',
      motion: 'tracked_callout',
      effects: ['glitch'],
      transition: { type: 'whip_pan', direction: 'right', duration_frames: 8 },
      overlay: 'Keep overlays outside the important gameplay action area.',
      duration_scale: 1
    },
    documentary_scene: {
      label: 'Documentary scene',
      layout: 'cinematic_observation',
      media_priority: ['source_footage', 'three_d', 'procedural_2d'],
      camera: 'Use motivated establishing, medium and detail coverage; avoid arbitrary movement.',
      action: 'Build context through place, object and process details with evidence/illustration clearly distinguished.',
      motion: 'measured_dolly',
      effects: ['vignette'],
      transition: { type: 'fade', direction: 'out', duration_frames: 12 },
      overlay: 'Minimal date/location lower third when verified.',
      duration_scale: 1.1
    }
  };

  const PROVIDERS = {
    openverse: {
      label: 'Openverse',
      modes: ['image', 'audio'],
      auth: 'Anonymous access is available; API rate limits apply.',
      rights: 'Each result has its own licence. Review the item page and attribution before publication.',
      homepage: 'https://openverse.org/',
      api: 'https://api.openverse.org/v1/'
    },
    wikimedia_commons: {
      label: 'Wikimedia Commons',
      modes: ['image', 'audio', 'video'],
      auth: 'Public MediaWiki API; use a modest result limit and respect Wikimedia API etiquette.',
      rights: 'Each file page declares its own licence and attribution requirements; inspect it individually.',
      homepage: 'https://commons.wikimedia.org/',
      api: 'https://commons.wikimedia.org/w/api.php'
    },
    poly_haven: {
      label: 'Poly Haven',
      modes: ['model3d', 'texture', 'hdri'],
      auth: 'Free public API; live API integrations require a distinct User-Agent and visible Poly Haven credit.',
      rights: 'The asset library is CC0. Review current API terms before implementing an API client.',
      homepage: 'https://polyhaven.com/',
      api: 'https://api.polyhaven.com/'
    },
    internet_archive: {
      label: 'Internet Archive',
      modes: ['image', 'audio', 'video'],
      auth: 'Public item search; item metadata and rights vary.',
      rights: 'A public archive record is not a licence. Check the rights statement for each file.',
      homepage: 'https://archive.org/',
      api: 'https://archive.org/advancedsearch.php'
    }
  };

  function text(value, max) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim().slice(0, max || 240);
  }

  function xml(value) {
    return text(value, 500).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
  }

  function asNumber(value, fallback, min, max) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.max(min, Math.min(max, number)) : fallback;
  }

  function safeHttpUrl(value) {
    try { const url = new URL(String(value || '')); return ['http:','https:'].includes(url.protocol) ? url.href : ''; }
    catch (_) { return ''; }
  }

  function listRecipes() {
    return Object.entries(RECIPES).map(([id, recipe]) => Object.assign({ id: id }, Core.clone(recipe)));
  }

  function instantiateShotRecipe(id, overrides) {
    const base = RECIPES[id];
    if (!base) throw new Error('Unknown shot recipe: ' + id);
    const input = overrides || {};
    const durationScale = asNumber(input.duration_scale, base.duration_scale, 0.5, 2.5);
    const transitionType = input.transition_type || base.transition.type;
    if (Core && !Core.TRANSITION_TYPES.includes(transitionType)) throw new Error('Unsupported recipe transition: ' + transitionType);
    return Object.assign({ id: id }, Core.clone(base), {
      duration_scale: durationScale,
      layout: text(input.layout || base.layout, 80),
      emphasis: text(input.emphasis || '', 240),
      transition: Object.assign({}, Core.clone(base.transition), {
        type: transitionType,
        duration_frames: Math.round(asNumber(input.transition_frames, base.transition.duration_frames, 1, 240))
      })
    });
  }

  function applyShotRecipe(project, beatId, recipeId, overrides) {
    if (!project || !project.shot_plan || !Array.isArray(project.shot_plan.beats)) throw new Error('Generate a shot plan before applying shot recipes.');
    const beat = project.shot_plan.beats.find(item => item.id === beatId);
    if (!beat) throw new Error('Shot beat was not found.');
    const recipe = instantiateShotRecipe(recipeId, overrides);
    beat.shot_recipe = recipe;
    beat.composition = recipe.layout;
    beat.camera_movement = recipe.camera;
    beat.visual_actions = [recipe.action];
    beat.motion_treatment = recipe.motion;
    beat.recipe_overlay = recipe.overlay;
    beat.recipe_transition = Core.clone(recipe.transition);
    const originalDuration = Math.max(1, beat.end_frame - beat.start_frame);
    beat.recipe_duration_frames = Math.max(1, Math.round(originalDuration * recipe.duration_scale));
    return beat;
  }

  function svgText(x, y, value, size, fill, weight, anchor) {
    return '<text x="' + x + '" y="' + y + '" fill="' + (fill || '#edf5ff') +
      '" font-size="' + (size || 28) + '" font-family="Inter,Arial,sans-serif" font-weight="' +
      (weight || 500) + '" text-anchor="' + (anchor || 'start') + '">' + xml(value) + '</text>';
  }

  function buildGraphicSvg(spec) {
    const input = spec || {};
    const width = Math.round(asNumber(input.width, 1280, 320, 3840));
    const height = Math.round(asNumber(input.height, 720, 180, 2160));
    const kind = input.type || 'background';
    const title = xml(input.title || 'FrameForge procedural graphic');
    const subtitle = xml(input.subtitle || '');
    const labels = (Array.isArray(input.labels) ? input.labels : [])
      .slice(0, MAX_LABELS).map(item => text(item, 100));
    const values = (Array.isArray(input.values) ? input.values : [])
      .slice(0, MAX_LABELS).map(value => asNumber(value, 0, 0, 1000000));
    const accent = /^#[0-9a-f]{6}$/i.test(input.accent || '') ? input.accent : '#55a7ff';
    const second = /^#[0-9a-f]{6}$/i.test(input.secondary || '') ? input.secondary : '#ffad62';
    const bg = /^#[0-9a-f]{6}$/i.test(input.background || '') ? input.background : '#101b29';
    const parts = [
      '<svg xmlns="http://www.w3.org/2000/svg" width="' + width + '" height="' + height + '" viewBox="0 0 ' + width + ' ' + height + '">',
      '<defs><linearGradient id="ff-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="' + bg + '"/><stop offset="1" stop-color="#172d43"/></linearGradient>',
      '<linearGradient id="ff-accent" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="' + accent + '"/><stop offset="1" stop-color="' + second + '"/></linearGradient></defs>',
      '<rect width="100%" height="100%" rx="28" fill="url(#ff-bg)"/>',
      '<path d="M0 ' + Math.round(height * 0.78) + ' Q' + Math.round(width * 0.45) + ' ' + Math.round(height * 0.54) + ' ' + width + ' ' + Math.round(height * 0.72) + ' L' + width + ' ' + height + ' L0 ' + height + 'Z" fill="#0b1420" opacity=".44"/>',
      '<rect x="38" y="38" width="' + (width - 76) + '" height="' + (height - 76) + '" rx="22" fill="none" stroke="#ffffff" stroke-opacity=".12"/>'
    ];
    parts.push(svgText(78, 105, title, 38, '#f3f7fc', 750));
    if (subtitle) parts.push(svgText(80, 145, subtitle, 19, '#a9bfd5', 450));

    if (kind === 'comparison') {
      const left = labels[0] || 'Option A';
      const right = labels[1] || 'Option B';
      const mid = Math.round(width / 2);
      parts.push('<rect x="82" y="205" width="' + (mid - 120) + '" height="390" rx="18" fill="#0a1420" stroke="' + accent + '" stroke-width="3"/>');
      parts.push('<rect x="' + (mid + 38) + '" y="205" width="' + (mid - 120) + '" height="390" rx="18" fill="#0a1420" stroke="' + second + '" stroke-width="3"/>');
      parts.push(svgText(Math.round(mid / 2), 405, left, 31, '#eaf4ff', 700, 'middle'));
      parts.push(svgText(mid + Math.round(mid / 2), 405, right, 31, '#eaf4ff', 700, 'middle'));
      parts.push('<circle cx="' + mid + '" cy="400" r="47" fill="#24364a" stroke="#ffffff" stroke-opacity=".22"/>');
      parts.push(svgText(mid, 411, 'VS', 25, '#ffffff', 800, 'middle'));
    } else if (kind === 'flowchart' || kind === 'diagram') {
      const names = labels.length ? labels : ['Input', 'Process', 'Output'];
      const nodeW = Math.min(250, Math.floor((width - 240) / Math.min(4, names.length)));
      const gap = 38;
      const used = names.length * nodeW + (names.length - 1) * gap;
      let x = Math.round((width - used) / 2);
      const y = Math.round(height * 0.52);
      names.forEach((name, index) => {
        if (index) {
          const ax = x - gap;
          parts.push('<path d="M' + (ax - 24) + ' ' + y + ' l16 -12 m-16 12 l16 12" stroke="' + accent + '" stroke-width="5" fill="none" stroke-linecap="round"/>');
        }
        parts.push('<rect x="' + x + '" y="' + (y - 58) + '" width="' + nodeW + '" height="116" rx="18" fill="#17283b" stroke="' + (index % 2 ? second : accent) + '" stroke-width="3"/>');
        parts.push(svgText(x + nodeW / 2, y + 8, name, 23, '#edf5ff', 650, 'middle'));
        x += nodeW + gap;
      });
    } else if (kind === 'map') {
      const points = [[180,290],[430,420],[700,250],[1000,440],[1110,270]];
      const route = points.map((point,index)=>(index?'L':'M')+point[0]+' '+point[1]).join(' ');
      parts.push('<path d="' + route + '" stroke="' + accent + '" stroke-width="8" stroke-dasharray="15 13" fill="none" stroke-linecap="round"/>');
      points.forEach((point,index)=>{
        parts.push('<circle cx="'+point[0]+'" cy="'+point[1]+'" r="16" fill="'+(index%2?second:accent)+'" stroke="#ffffff" stroke-width="3"/>');
        parts.push(svgText(point[0],point[1]+46,labels[index]||('Point '+(index+1)),18,'#e7f0fa',600,'middle'));
      });
      parts.push(svgText(80,height-80,'SCHEMATIC MAP — NOT TO SCALE',15,'#8ea5bc',700));
    } else if (kind === 'timeline') {
      const names = labels.length ? labels : ['Event 1','Event 2','Event 3'];
      const y = Math.round(height * 0.54);
      parts.push('<path d="M110 '+y+' H'+(width-110)+'" stroke="'+accent+'" stroke-width="8" stroke-linecap="round"/>');
      const step = names.length > 1 ? (width-260)/(names.length-1) : 0;
      names.forEach((name,index)=>{
        const x = 130 + step * index;
        parts.push('<circle cx="'+x+'" cy="'+y+'" r="17" fill="'+(index%2?second:accent)+'" stroke="#ffffff" stroke-width="3"/>');
        parts.push(svgText(x,y+(index%2?78:-52),name,18,'#edf5ff',600,'middle'));
      });
      parts.push(svgText(80,height-80,'CHRONOLOGY — CHECK DATES AGAINST SOURCES',15,'#8ea5bc',700));
    } else if (kind === 'evidence') {
      const quote = xml(input.evidence_text || 'Add a verified excerpt or source observation before publication.');
      const source = xml(input.source || 'Source details not supplied');
      parts.push('<rect x="96" y="205" width="'+(width-192)+'" height="300" rx="18" fill="#09131e" stroke="'+accent+'" stroke-width="3"/>');
      parts.push('<rect x="96" y="205" width="14" height="300" rx="7" fill="'+accent+'"/>');
      parts.push(svgText(145,280,'SOURCE EXCERPT / OBSERVATION',16,accent,800));
      parts.push(svgText(145,360,quote,25,'#f2f6fb',550));
      parts.push(svgText(145,450,source,17,'#a8bdd1',500));
      parts.push(svgText(98,height-88,'VERIFY THE ORIGINAL SOURCE AND PINPOINT LOCATION',14,'#ffca87',700));
    } else if (kind === 'bar_chart') {
      const chartValues = values.length ? values : [3,5,4];
      const max = Math.max(1,...chartValues);
      const barW = Math.min(130,Math.floor((width-260)/(chartValues.length*1.8)));
      const gap = Math.max(24,Math.floor(barW*.45));
      const total = chartValues.length*barW+(chartValues.length-1)*gap;
      let x = Math.round((width-total)/2);
      const floor = height-130;
      chartValues.forEach((value,index)=>{
        const h = Math.round((value/max)*290);
        parts.push('<rect x="'+x+'" y="'+(floor-h)+'" width="'+barW+'" height="'+h+'" rx="10" fill="'+(index%2?second:accent)+'"/>');
        parts.push(svgText(x+barW/2,floor+35,labels[index]||('Item '+(index+1)),16,'#dce9f6',550,'middle'));
        x += barW+gap;
      });
      parts.push(svgText(80,height-70,values.length?'VALUES SUPPLIED BY PROJECT':'ILLUSTRATIVE SAMPLE — NOT FACTUAL DATA',14,'#ffca87',700));
    } else if (kind === 'badge') {
      parts.push('<circle cx="'+Math.round(width/2)+'" cy="'+Math.round(height*.54)+'" r="155" fill="#0a1420" stroke="url(#ff-accent)" stroke-width="13"/>');
      parts.push(svgText(width/2,Math.round(height*.56),labels[0]||'KEY IDEA',42,'#f4f8fc',800,'middle'));
    } else {
      for (let index=0; index<12; index++) {
        const x = 95 + ((index*197)%(width-190));
        const y = 185 + ((index*113)%(height-250));
        parts.push('<circle cx="'+x+'" cy="'+y+'" r="'+(5+(index%4)*3)+'" fill="'+(index%2?second:accent)+'" opacity=".23"/>');
      }
      parts.push(svgText(80,height-90,'ORIGINAL PROCEDURAL ARTWORK',14,'#9fb4c8',750));
    }
    parts.push('</svg>');
    return parts.join('');
  }

  function createProceduralParticleClip(project, spec, options) {
    const input = spec || {};
    const opts = options || {};
    const sequence = Core.getMainSequence(project);
    let track = sequence.tracks.find(item => item.type === 'graphic' && !item.locked);
    if (!track) track = Core.addTrack(project, 'graphic', 'Procedural particles');
    const preset = ['sparks','dust','embers','magic','confetti'].includes(input.preset) ? input.preset : 'sparks';
    const parameters = {
      preset: preset,
      count: Math.round(asNumber(input.count, 72, 1, 500)),
      seed: Math.round(asNumber(input.seed, 1337, 0, 2147483647)),
      speed: asNumber(input.speed, 1, 0, 8),
      size: asNumber(input.size, 3.5, 0.2, 30),
      color: /^#[0-9a-f]{6}$/i.test(input.color || '') ? input.color : '#ffc46b',
      spread: asNumber(input.spread, 1, 0.1, 4),
      gravity: asNumber(input.gravity, 72, -500, 500),
      life_seconds: asNumber(input.life_seconds, 1.8, 0.1, 20)
    };
    const clip = Core.addGraphicClip(
      project, track.id, 'particles', parameters,
      Math.max(0, Math.round(Number(opts.start_frame) || 0)),
      Math.max(1, Math.round(Number(opts.duration_frames) || sequence.fps * 3))
    );
    return clip;
  }

  function createProceduralGraphicClip(project, spec, options) {
    const input = spec || {};
    const opts = options || {};
    const sequence = Core.getMainSequence(project);
    let track = sequence.tracks.find(item => item.type === (opts.track_type === 'title' ? 'title' : 'graphic') && !item.locked);
    if (!track) track = Core.addTrack(project, opts.track_type === 'title' ? 'title' : 'graphic', opts.track_name || 'Procedural graphics');
    const svg = buildGraphicSvg(Object.assign({}, input, {
      width: sequence.width || project.settings.width,
      height: sequence.height || project.settings.height
    }));
    const clip = Core.addGraphicClip(
      project, track.id, 'svg', { svg: svg },
      Math.max(0, Math.round(Number(opts.start_frame) || 0)),
      Math.max(1, Math.round(Number(opts.duration_frames) || sequence.fps * 3))
    );
    return clip;
  }

  function attributionIsRequired(licenseName) {
    const value = text(licenseName, 100).toLowerCase().replace(/[_-]/g, ' ');
    if (!value) return true;
    if (value.includes('cc0') || value.includes('public domain') || value === 'pdm') return false;
    if (value.includes('by') || value.includes('attribution')) return true;
    return true;
  }

  function normaliseOpenverse(item, mediaType) {
    const license = text(item.license, 100);
    return {
      provider: 'Openverse',
      media_type: mediaType,
      title: text(item.title || 'Untitled media', 300),
      creator: text(item.creator || 'Creator not supplied', 240),
      preview_url: item.thumbnail || item.url || '',
      download_url: item.url || '',
      landing_url: item.foreign_landing_url || item.detail_url || item.url || '',
      license_name: license ? license.toUpperCase() + (item.license_version ? ' ' + text(item.license_version, 30) : '') : '',
      license_url: item.license_url || '',
      attribution_text: text(item.attribution || '', 1000),
      rights_status: 'pending',
      source_type: license.toLowerCase().includes('cc0') ? 'public_domain' : (license ? 'open_license' : 'unknown')
    };
  }

  function normaliseCommons(page, mediaType) {
    const info = page.imageinfo && page.imageinfo[0] || {};
    const meta = info.extmetadata || {};
    const get = key => text(String(meta[key]?.value || '').replace(/<[^>]*>/g, ' '), 500);
    const license = get('LicenseShortName');
    const title = text(String(page.title || 'Untitled file').replace(/^File:/, ''), 300);
    return {
      provider: 'Wikimedia Commons',
      media_type: mediaType,
      title: title,
      creator: get('Artist') || get('Credit') || 'Creator not supplied',
      preview_url: info.thumburl || info.url || '',
      download_url: info.url || '',
      landing_url: info.descriptionurl || ('https://commons.wikimedia.org/wiki/' + encodeURIComponent(page.title || '')),
      license_name: license,
      license_url: get('LicenseUrl'),
      attribution_text: get('Attribution') || (get('Artist') ? 'Creator: ' + get('Artist') : ''),
      rights_status: 'pending',
      source_type: license.toLowerCase().includes('cc0') || license.toLowerCase().includes('public domain') ? 'public_domain' : (license ? 'open_license' : 'unknown')
    };
  }

  function providerSearchUrl(provider, query, mediaType) {
    const q = encodeURIComponent(text(query, 200));
    if (provider === 'openverse') {
      const type = mediaType === 'audio' ? 'audio' : 'images';
      return 'https://api.openverse.org/v1/' + type + '/?q=' + q + '&page_size=' + MAX_RESULTS;
    }
    if (provider === 'wikimedia_commons') {
      return 'https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=' + q +
        '&gsrnamespace=6&gsrlimit=' + MAX_RESULTS + '&prop=imageinfo&iiprop=url%7Cextmetadata&iiurlwidth=420&format=json&origin=*';
    }
    if (provider === 'poly_haven') return 'https://polyhaven.com/' + (mediaType === 'model3d' ? 'models' : mediaType === 'texture' ? 'textures' : 'hdris');
    if (provider === 'internet_archive') return 'https://archive.org/search?query=' + q;
    throw new Error('This provider uses a manual browser workflow or is not supported.');
  }

  async function searchProvider(provider, query, mediaType, fetchImpl) {
    if (!text(query, 200)) throw new Error('Enter a search phrase first.');
    const fetcher = fetchImpl || root.fetch;
    if (provider === 'poly_haven' || provider === 'internet_archive') {
      return { provider: PROVIDERS[provider].label, mode: 'manual', url: providerSearchUrl(provider, query, mediaType), results: [] };
    }
    if (!['openverse','wikimedia_commons'].includes(provider)) throw new Error('Unsupported media provider.');
    if (provider === 'openverse' && !['image','audio'].includes(mediaType)) throw new Error('Openverse adapter supports image and audio search.');
    if (typeof fetcher !== 'function') throw new Error('This browser does not provide network search. Use the manual provider link or local import.');
    const url = providerSearchUrl(provider, query, mediaType);
    const response = await fetcher(url, { method: 'GET', headers: { Accept: 'application/json' }, credentials: 'omit' });
    if (!response || !response.ok) throw new Error('Provider search failed. Open the provider page or import a file manually.');
    const payload = await response.json();
    let results;
    if (provider === 'openverse') {
      results = (payload.results || []).slice(0, MAX_RESULTS).map(item => normaliseOpenverse(item, mediaType));
    } else {
      results = Object.values(payload.query?.pages || {}).slice(0, MAX_RESULTS).map(page => {
        const urlValue = page.imageinfo?.[0]?.url || '';
        const ext = urlValue.split('?')[0].split('.').pop().toLowerCase();
        const inferred = /\.(mp3|wav|flac|ogg|oga|opus)$/i.test(urlValue) || ['mp3','wav','flac','ogg','oga','opus'].includes(ext)
          ? 'audio' : /\.(mp4|webm|ogv|mov)$/i.test(urlValue) ? 'video' : mediaType;
        return normaliseCommons(page, inferred);
      });
    }
    return { provider: PROVIDERS[provider].label, mode: 'api', url: url, results: results };
  }

  function importOptionsForSelection(selected, audioRole) {
    const item = selected || {};
    const license = text(item.license_name, 300);
    const sourceType = ['public_domain','open_license'].includes(item.source_type) ? item.source_type
      : (/cc0|public domain|pdm/i.test(license) ? 'public_domain' : (license ? 'open_license' : 'unknown'));
    const attributionRequired = attributionIsRequired(license);
    const attribution = text(item.attribution_text, 1800) ||
      (item.creator && item.creator !== 'Creator not supplied' ? 'Creator: ' + item.creator + '. Source: ' + item.landing_url : '');
    const provenance = {
      source_type: sourceType,
      source_title: text(item.title, 500),
      creator: text(item.creator, 300),
      provider: text(item.provider, 200),
      acquired_at: new Date().toISOString(),
      notes: 'Imported after manual selection. Source and licence metadata are recorded but remain subject to user review.'
    };
    const sourceUrl = safeHttpUrl(item.landing_url || item.download_url);
    const licenseUrl = safeHttpUrl(item.license_url);
    if (sourceUrl) provenance.source_url = sourceUrl;
    const rights = {
      status: 'pending',
      license_name: license || 'Unverified — inspect the file page',
      attribution_required: attributionRequired,
      attribution_text: attribution,
      restrictions: ['Pending individual rights review; verify licence scope, creator, source page and intended use before publication.']
    };
    if (licenseUrl) rights.license_url = licenseUrl;
    return {
      provenance: provenance,
      rights: rights,
      tags: audioRole ? ['audio-role:' + audioRole] : []
    };
  }

  function registerAudioMetadata(project, assetId, input) {
    const asset = (project.assets || []).find(item => item.id === assetId);
    if (!asset || asset.media_type !== 'audio') throw new Error('Choose an imported audio asset.');
    const rights = asset.rights || { status: 'pending', attribution_required: true, restrictions: [] };
    rights.status = 'pending';
    rights.license_name = text(input?.license_name || rights.license_name || 'Unverified', 300);
    const licenseUrl = safeHttpUrl(input?.license_url || rights.license_url || '');
    if (licenseUrl) rights.license_url = licenseUrl;
    else delete rights.license_url;
    rights.attribution_required = input?.attribution_required === undefined
      ? attributionIsRequired(rights.license_name) : Boolean(input.attribution_required);
    rights.attribution_text = text(input?.attribution_text || rights.attribution_text || '', 1800);
    rights.restrictions = Array.isArray(rights.restrictions) ? rights.restrictions : [];
    if (!rights.restrictions.some(item => String(item).includes('Pending individual rights review'))) {
      rights.restrictions.push('Pending individual rights review; verify licence scope, creator, source page and intended use before publication.');
    }
    asset.rights = rights;
    return asset;
  }

  function audioCatalogue(project) {
    return (project.assets || []).filter(asset => asset.media_type === 'audio').map(asset => ({
      id: asset.id,
      label: asset.label || asset.id,
      role: (asset.tags || []).find(tag => String(tag).startsWith('audio-role:'))?.slice(11) || 'unassigned',
      license_name: asset.rights?.license_name || 'Unverified',
      attribution_text: asset.rights?.attribution_text || '',
      attribution_required: asset.rights?.attribution_required !== false,
      status: asset.rights?.status || 'unknown',
      source: asset.provenance?.provider || asset.provenance?.source_type || 'unknown'
    }));
  }

  function buildAudioCredits(project) {
    return audioCatalogue(project).filter(item => item.status === 'approved' && item.attribution_text)
      .map(item => item.attribution_text).filter(Boolean).join('\n');
  }

  function audioPackagingReport(project) {
    const entries = audioCatalogue(project);
    const blockers = [];
    for (const item of entries) {
      if (item.status !== 'approved') blockers.push('Audio "' + item.label + '" is not rights-approved.');
      if (item.attribution_required && !item.attribution_text) blockers.push('Audio "' + item.label + '" requires attribution text.');
    }
    return {
      status: blockers.length ? 'blocked' : 'ready',
      can_package: blockers.length === 0,
      audio_assets: entries.length,
      blockers: blockers,
      credits: buildAudioCredits(project),
      note: 'This is a metadata gate, not an independent legal or licence verification.'
    };
  }

  function trackForAsset(project, asset, audioRoleMap) {
    let type = Core.trackForAssetType(asset.media_type);
    if (asset.media_type === 'audio') {
      const role = (audioRoleMap && audioRoleMap[asset.id]) ||
        (asset.tags || []).find(tag => String(tag).startsWith('audio-role:'))?.slice(11) || 'sfx';
      type = ['voiceover','music','sfx','audio'].includes(role) ? role : 'sfx';
    }
    const sequence = Core.getMainSequence(project);
    let track = sequence.tracks.find(item => item.type === type && !item.locked);
    if (!track) track = Core.addTrack(project, type, type === 'sfx' ? 'Imported sound effects' : 'Production ' + type);
    return track;
  }

  function assembleShotPlan(project, options) {
    if (!project || !project.shot_plan || !Array.isArray(project.shot_plan.beats) || !project.shot_plan.beats.length) {
      throw new Error('A generated shot plan is required before assembly.');
    }
    const opts = options || {};
    const readiness = Director?.readinessReport ? Director.readinessReport(project) : { blockers: [] };
    if (opts.require_ready && readiness.blockers.length) {
      throw new Error('Shot plan is not cleared for production: ' + readiness.blockers.slice(0, 5).join(' '));
    }
    const sequence = Core.getMainSequence(project);
    const fps = sequence.fps || project.settings.fps || 30;
    const created = [];
    const unfilled = [];
    const cues = [];

    for (const beat of project.shot_plan.beats) {
      const start = Math.max(0, Math.round(beat.start_frame));
      const recipe = beat.shot_recipe || null;
      const duration = Math.max(1, Math.round(beat.recipe_duration_frames || (beat.end_frame - beat.start_frame)));
      const linkedAssets = (beat.asset_ids || []).map(id => (project.assets || []).find(asset => asset.id === id)).filter(Boolean);
      const visualAssets = linkedAssets.filter(asset => ['image','video','graphic','model3d'].includes(asset.media_type));
      const audioAssets = linkedAssets.filter(asset => asset.media_type === 'audio');
      let visualCreated = 0;

      for (const asset of visualAssets) {
        const track = trackForAsset(project, asset, opts.audio_role_map);
        const clip = Core.addAssetClip(project, asset.id, track.id, start, duration);
        if (recipe?.transition && Core.TRANSITION_TYPES.includes(recipe.transition.type)) {
          Core.setClipTransition(project, clip.id, 'in', {
            type: recipe.transition.type,
            direction: recipe.transition.direction || 'in',
            duration_frames: Math.min(duration, recipe.transition.duration_frames || Math.round(fps * 0.25))
          });
        }
        for (const effect of recipe?.effects || []) {
          if (Core.CLIP_EFFECT_TYPES.includes(effect)) Core.setClipEffect(project, clip.id, effect, { intensity: 0.25 });
        }
        created.push({ beat_id: beat.id, clip_id: clip.id, asset_id: asset.id, track_id: track.id, kind: 'asset' });
        visualCreated += 1;
      }

      if (!visualCreated && beat.media_mix?.includes('procedural_2d') &&
          !['factual_evidence','comparative_evidence'].includes(beat.visual_role) &&
          beat.evidence_requirement !== 'actual_footage' && beat.evidence_requirement !== 'official_screenshot') {
        const graphic = buildGraphicSvg({
          type: recipe?.layout === 'split_comparison' ? 'comparison' :
            recipe?.layout === 'chronology' ? 'timeline' :
            recipe?.layout === 'map_route' ? 'map' :
            recipe?.layout === 'annotated_system' || recipe?.layout === 'sequential_steps' ? 'flowchart' : 'background',
          title: project.creative_brief?.topic || 'Explainer graphic',
          subtitle: text(beat.visual_purpose || 'Original procedural illustration', 150),
          labels: [text(beat.narration, 90), ...(recipe?.emphasis ? [recipe.emphasis] : [])],
          width: sequence.width, height: sequence.height
        });
        const track = sequence.tracks.find(item => item.type === 'graphic' && !item.locked) ||
          Core.addTrack(project, 'graphic', 'Procedural illustrations');
        const clip = Core.addGraphicClip(project, track.id, 'svg', { svg: graphic }, start, duration);
        if (recipe?.transition && Core.TRANSITION_TYPES.includes(recipe.transition.type)) {
          Core.setClipTransition(project, clip.id, 'in', {
            type: recipe.transition.type, direction: recipe.transition.direction || 'in',
            duration_frames: Math.min(duration, recipe.transition.duration_frames || 8)
          });
        }
        created.push({ beat_id: beat.id, clip_id: clip.id, track_id: track.id, kind: 'procedural_graphic' });
        visualCreated += 1;
      }

      if (!visualCreated) {
        unfilled.push({
          beat_id: beat.id,
          narration: beat.narration,
          reason: beat.evidence_requirement === 'actual_footage' || beat.evidence_requirement === 'official_screenshot'
            ? 'Required factual source media is not linked; no substitute was fabricated.'
            : 'No suitable visual asset is linked; add a topic-specific asset or procedural treatment.'
        });
      }

      for (const asset of audioAssets) {
        const track = trackForAsset(project, asset, opts.audio_role_map);
        const clip = Core.addAssetClip(project, asset.id, track.id, start, duration);
        created.push({ beat_id: beat.id, clip_id: clip.id, asset_id: asset.id, track_id: track.id, kind: 'audio_cue' });
      }
      if (Array.isArray(beat.audio_cues) && beat.audio_cues.length) {
        cues.push({ beat_id: beat.id, start_frame: start, cues: Core.clone(beat.audio_cues) });
      }
      sequence.duration_frames = Math.max(sequence.duration_frames, start + duration);
    }

    project.extensions = project.extensions || {};
    project.extensions.production_orchestration = {
      version: 1,
      generated_at: new Date().toISOString(),
      status: unfilled.length ? 'draft_needs_assets' : (readiness.blockers.length ? 'draft_needs_review' : 'draft_ready_for_review'),
      created_clip_ids: created.map(item => item.clip_id),
      unfilled_beats: unfilled,
      audio_cues: cues,
      rights_blockers: readiness.blockers || [],
      review_required_before_render: true
    };
    return {
      status: project.extensions.production_orchestration.status,
      created: created,
      unfilled: unfilled,
      audio_cues: cues,
      rights_blockers: readiness.blockers || [],
      project: project
    };
  }

  const api = {
    RECIPES, PROVIDERS, listRecipes, instantiateShotRecipe, applyShotRecipe, safeHttpUrl,
    buildGraphicSvg, createProceduralGraphicClip, createProceduralParticleClip, providerSearchUrl, searchProvider,
    importOptionsForSelection, registerAudioMetadata, audioCatalogue, buildAudioCredits,
    audioPackagingReport, assembleShotPlan
  };
  root.FFV2Production = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
