const test = require('node:test');
const assert = require('node:assert/strict');
const Core = require('../ff-v2-core.js');
const Director = require('../ff-v2-director.js');
const Production = require('../ff-v2-production.js');

function projectWithPlan() {
  const project = Core.createDefaultProject('Production workflow test');
  project.creative_brief.topic = 'How a simple network works';
  project.creative_brief.niche = 'cybersecurity';
  project.creative_brief.target_duration_seconds = 3;
  project.creative_brief.narration_script = 'A device sends a request.\\n\\nA network checks the request.\\n\\nA response returns.';
  Director.buildShotPlan(project, { duration_seconds: 3, fps: 30 });
  return project;
}

function makeAsset(id, mediaType, rights) {
  return {
    id,
    file_name: id + (mediaType === 'audio' ? '.wav' : mediaType === 'video' ? '.mp4' : '.png'),
    label: id,
    media_type: mediaType,
    mime_type: mediaType === 'audio' ? 'audio/wav' : mediaType === 'video' ? 'video/mp4' : 'image/png',
    metadata: { duration_seconds: 3, width: mediaType === 'video' ? 640 : undefined, height: mediaType === 'video' ? 360 : undefined },
    provenance: { source_type: 'user_supplied', acquired_at: '2026-11-28T00:00:00.000Z' },
    rights: Object.assign({ status: 'pending', attribution_required: false, restrictions: [] }, rights || {}),
    tags: []
  };
}

test('shot recipes are reusable and editable across all required shot types', () => {
  const recipes = Production.listRecipes();
  assert.ok(recipes.length >= 9);
  for (const id of ['character_reveal','comparison','explainer','diagram','map','timeline','evidence_callout','gameplay_overlay','documentary_scene']) {
    assert.ok(Production.RECIPES[id], 'missing recipe ' + id);
  }
  const recipe = Production.instantiateShotRecipe('comparison', {
    duration_scale: 1.4,
    layout: 'custom_split',
    transition_frames: 22
  });
  assert.equal(recipe.layout, 'custom_split');
  assert.equal(recipe.duration_scale, 1.4);
  assert.equal(recipe.transition.duration_frames, 22);
  assert.throws(() => Production.instantiateShotRecipe('not-a-recipe'), /Unknown shot recipe/);
});

test('applying a recipe stores a custom treatment without silently rewriting narration timing', () => {
  const project = projectWithPlan();
  const beat = project.shot_plan.beats[0];
  const originalStart = beat.start_frame;
  const originalEnd = beat.end_frame;
  Production.applyShotRecipe(project, beat.id, 'documentary_scene', { duration_scale: 1.25 });
  assert.equal(beat.start_frame, originalStart);
  assert.equal(beat.end_frame, originalEnd);
  assert.equal(beat.shot_recipe.id, 'documentary_scene');
  assert.equal(beat.recipe_duration_frames, Math.round((originalEnd - originalStart) * 1.25));
  assert.throws(() => Production.applyShotRecipe(project, 'missing', 'map'), /not found/);
});

test('procedural SVG builder creates safe editable artwork for each visual treatment', () => {
  const kinds = ['background','comparison','flowchart','diagram','map','timeline','evidence','bar_chart','badge'];
  for (const type of kinds) {
    const svg = Production.buildGraphicSvg({
      type,
      title: 'A & B <script>alert(1)</script>',
      subtitle: 'A labelled explanation',
      labels: ['Input','Process','Output'],
      values: [2,5,3]
    });
    assert.match(svg, /^<svg /);
    assert.match(svg, /A &amp; B &lt;script&gt;/);
    assert.doesNotMatch(svg, /<script/i);
    assert.doesNotMatch(svg, /foreignObject|(?:href|src)=['\"]https?:|url\(['\"]?https?:/i);
    assert.doesNotThrow(() => Core.validateSvgText(svg));
  }
});

test('procedural graphic is inserted as an editable SVG timeline clip', () => {
  const project = Core.createDefaultProject('Procedural clip');
  const clip = Production.createProceduralGraphicClip(project, {
    type: 'flowchart',
    title: 'Request path',
    labels: ['Device','Firewall','Server']
  }, { start_frame: 12, duration_frames: 75 });
  assert.equal(clip.kind, 'generated');
  assert.equal(clip.generator.type, 'svg');
  assert.equal(clip.start_frame, 12);
  assert.equal(clip.duration_frames, 75);
});

test('procedural particle clips use editable, bounded parameters and a stable seed', () => {
  const project = Core.createDefaultProject('Procedural particles');
  const clip = Production.createProceduralParticleClip(project, {
    preset: 'embers', count: 900, seed: 42, speed: 1.4, color: '#ff8844'
  }, { start_frame: 18, duration_frames: 120 });
  assert.equal(clip.generator.type, 'particles');
  assert.equal(clip.generator.parameters.preset, 'embers');
  assert.equal(clip.generator.parameters.count, 500);
  assert.equal(clip.generator.parameters.seed, 42);
  assert.equal(clip.start_frame, 18);
  assert.equal(clip.duration_frames, 120);
  assert.equal(Core.validateProject(project).length, 0);
});

test('a manual CC0 source is classified as public-domain but never approved automatically', () => {
  const options = Production.importOptionsForSelection({
    provider: 'Poly Haven', license_name: 'CC0 1.0', landing_url: 'https://polyhaven.com/a/test'
  });
  assert.equal(options.provenance.source_type, 'public_domain');
  assert.equal(options.rights.status, 'pending');
  assert.equal(options.rights.attribution_required, false);
});

test('audio usage limits are retained in the catalogue until rights review', () => {
  const project = Core.createDefaultProject('Audio terms');
  Core.addAsset(project,makeAsset('music-terms','audio',{ attribution_required: true }));
  Production.registerAudioMetadata(project,'music-terms',{
    license_name:'CC BY-NC 4.0',
    attribution_required:true,
    attribution_text:'Composer credit',
    restrictions:['Non-commercial use only','Attribution required in the video description']
  });
  const asset=project.assets.find(item=>item.id==='music-terms');
  assert.ok(asset.rights.restrictions.includes('Non-commercial use only'));
  assert.ok(asset.rights.restrictions.includes('Attribution required in the video description'));
  assert.equal(asset.rights.status,'pending');
});

test('source adapter URLs are bounded and preserve provider-specific manual fallbacks', () => {
  const openverse = Production.providerSearchUrl('openverse','network security','image');
  assert.match(openverse, /^https:\/\/api\.openverse\.org\/v1\/images/);
  assert.match(openverse, /network%20security/);
  const commons = Production.providerSearchUrl('wikimedia_commons','historic aircraft','video');
  assert.match(commons, /^https:\/\/commons\.wikimedia\.org\/w\/api\.php/);
  const poly = Production.providerSearchUrl('poly_haven','HDRI','model3d');
  assert.equal(poly, 'https://polyhaven.com/models');
  const archive = Production.providerSearchUrl('internet_archive','public radio','audio');
  assert.match(archive, /^https:\/\/archive\.org\/search/);
  assert.throws(() => Production.providerSearchUrl('unknown','query','image'), /manual browser workflow/);
});

test('Openverse results retain source and licence metadata but remain pending', async () => {
  const mockFetch = async url => ({
    ok: true,
    json: async () => ({
      results: [{
        title: 'Example photograph',
        creator: 'A. Creator',
        url: 'https://media.example.org/file.jpg',
        thumbnail: 'https://media.example.org/thumb.jpg',
        foreign_landing_url: 'https://openverse.org/image/123',
        license: 'by',
        license_version: '4.0',
        license_url: 'https://creativecommons.org/licenses/by/4.0/',
        attribution: 'A. Creator, Example photograph'
      }]
    })
  });
  const result = await Production.searchProvider('openverse','example','image',mockFetch);
  assert.equal(result.results.length,1);
  const item = result.results[0];
  assert.equal(item.provider,'Openverse');
  assert.equal(item.license_name,'BY 4.0');
  const options = Production.importOptionsForSelection(item);
  assert.equal(options.provenance.source_type,'open_license');
  assert.equal(options.provenance.source_url,'https://openverse.org/image/123');
  assert.equal(options.rights.status,'pending');
  assert.equal(options.rights.attribution_required,true);
  assert.equal(options.rights.license_url,'https://creativecommons.org/licenses/by/4.0/');
  const unsafeUrlOptions = Production.importOptionsForSelection({ license_url: 'javascript:alert(1)', landing_url: 'javascript:alert(1)' });
  assert.equal(unsafeUrlOptions.provenance.source_url, undefined);
  assert.equal(unsafeUrlOptions.rights.license_url, undefined);
});

test('Wikimedia Commons adapter reads per-file metadata without approving rights', async () => {
  const mockFetch = async () => ({
    ok: true,
    json: async () => ({
      query: {
        pages: {
          1: {
            title: 'File:Example.ogg',
            imageinfo: [{
              url: 'https://upload.wikimedia.org/example.ogg',
              thumburl: 'https://upload.wikimedia.org/example-preview.jpg',
              descriptionurl: 'https://commons.wikimedia.org/wiki/File:Example.ogg',
              extmetadata: {
                LicenseShortName: { value: 'CC BY-SA 4.0' },
                LicenseUrl: { value: 'https://creativecommons.org/licenses/by-sa/4.0/' },
                Artist: { value: 'A. Creator' },
                Attribution: { value: 'A. Creator / Wikimedia Commons' }
              }
            }]
          }
        }
      }
    })
  });
  const result = await Production.searchProvider('wikimedia_commons','example audio','audio',mockFetch);
  assert.equal(result.results.length,1);
  assert.equal(result.results[0].media_type,'audio');
  const options = Production.importOptionsForSelection(result.results[0]);
  assert.equal(options.rights.status,'pending');
  assert.equal(options.rights.attribution_required,true);
  assert.match(options.rights.attribution_text,/A\. Creator/);
});

test('audio catalogue and publication report block unreviewed assets and output approved credits', () => {
  const project = Core.createDefaultProject('Audio rights test');
  const audio = makeAsset('audio-1','audio');
  Core.addAsset(project,audio);
  Production.registerAudioMetadata(project,'audio-1',{
    license_name:'CC0 1.0',
    license_url:'https://creativecommons.org/publicdomain/zero/1.0/',
    attribution_required:false,
    attribution_text:'Optional creator credit'
  });
  const pending = Production.audioPackagingReport(project);
  assert.equal(pending.can_package,false);
  assert.ok(pending.blockers.some(item=>item.includes('not rights-approved')));
  Director.applyAssetRightsDecision(project,'audio-1',{
    decision:'approved',
    basis:'Audio was created by the project owner and released as CC0.',
    reviewer:'Project owner',
    intended_use:'Music and sound design in the video.'
  });
  const ready = Production.audioPackagingReport(project);
  assert.equal(ready.can_package,true,ready.blockers.join('\\n'));
  assert.equal(ready.status,'ready');
  assert.match(ready.credits,/Optional creator credit/);
});

test('unknown audio remains conservatively attribution-required and cannot be packaged', () => {
  const project = Core.createDefaultProject('Unknown audio');
  Core.addAsset(project,makeAsset('audio-unknown','audio',{ attribution_required: true }));
  Production.registerAudioMetadata(project,'audio-unknown',{
    license_name:'Unverified licence',
    attribution_required:true,
    attribution_text:''
  });
  const report = Production.audioPackagingReport(project);
  assert.equal(report.can_package,false);
  assert.ok(report.blockers.some(item=>item.includes('attribution text')));
});

test('shot orchestrator creates real clips, requested procedural art and records missing evidence', () => {
  const project = projectWithPlan();
  const beats = project.shot_plan.beats;
  const video = makeAsset('source-video','video');
  Core.addAsset(project,video);
  beats[0].media_mix = ['source_footage'];
  beats[0].asset_ids = ['source-video'];
  beats[0].visual_role = 'illustration';
  beats[1].media_mix = ['procedural_2d'];
  beats[1].asset_ids = [];
  beats[1].visual_role = 'illustration';
  beats[2].media_mix = ['source_footage'];
  beats[2].asset_ids = [];
  beats[2].visual_role = 'factual_evidence';
  beats[2].evidence_requirement = 'actual_footage';
  beats[2].audio_cues = ['subtle impact'];

  Production.applyShotRecipe(project,beats[0].id,'documentary_scene');
  const report = Production.assembleShotPlan(project);
  assert.equal(report.created.length,2);
  assert.equal(report.created[0].kind,'asset');
  assert.equal(report.created[0].asset_id,'source-video');
  assert.equal(report.created[1].kind,'procedural_graphic');
  assert.equal(report.unfilled.length,1);
  assert.equal(report.unfilled[0].beat_id,beats[2].id);
  assert.match(report.unfilled[0].reason,/no substitute was fabricated/);
  assert.equal(report.audio_cues.length,1);
  assert.equal(project.extensions.production_orchestration.review_required_before_render,true);
  assert.equal(project.extensions.production_orchestration.status,'draft_needs_assets');
  assert.equal(Core.validateProject(project).length,0);
});

test('orchestrator can enforce the director readiness gate when requested', () => {
  const project = projectWithPlan();
  const beat = project.shot_plan.beats[0];
  beat.visual_role = 'factual_evidence';
  beat.evidence_requirement = 'actual_footage';
  beat.media_mix = ['source_footage'];
  assert.throws(() => Production.assembleShotPlan(project,{require_ready:true}),/not cleared for production/);
});
