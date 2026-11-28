const test = require('node:test');
const assert = require('node:assert/strict');
const Core = require('../ff-v2-core.js');
const Director = require('../ff-v2-director.js');

function makeAsset(id='asset-source') {
  return {
    id, label:id, uri:'indexeddb://assets/'+id, media_type:'image',
    metadata:{width:100,height:100},
    provenance:{source_type:'user_supplied',creator:'',notes:'Fixture only'},
    rights:{status:'pending',attribution_required:false,restrictions:[]},tags:[]
  };
}

function makeProject() {
  const project=Core.createDefaultProject('Director tests','2026-11-28T00:00:00.000Z');
  Director.ensureDirectorData(project);
  return project;
}

test('new V2 projects include a structured, editable production brief and dossier',()=>{
  const project=makeProject();
  assert.equal(project.creative_brief.topic,'Untitled video project');
  assert.deepEqual(project.creative_brief.ambiguities_to_resolve,[]);
  assert.deepEqual(project.research.reference_videos,[]);
  assert.ok(project.visual_style_profile.visual_language.length>0);
  assert.equal(project.rights_review.status,'not_started');
  assert.equal(Core.validateProject(project).length,0);
});

test('brief updates preserve script, questions, ambiguity and restrictions',()=>{
  const project=makeProject();
  Director.updateBrief(project,{
    topic:'A network attack explained',niche:'cybersecurity',audience:'General viewers',
    platform:'youtube_shorts',target_duration_seconds:45,
    narration_script:'A clear script. A second beat.',
    research_questions:'Which date?\nWhat is the primary source?',
    ambiguities_to_resolve:'Clarify the device model.',
    restrictions:'No unrelated B-roll.\nNo unlicensed footage.'
  });
  assert.equal(project.creative_brief.topic,'A network attack explained');
  assert.equal(project.creative_brief.narration_script,'A clear script. A second beat.');
  assert.deepEqual(project.creative_brief.research_questions,['Which date?','What is the primary source?']);
  assert.deepEqual(project.creative_brief.ambiguities_to_resolve,['Clarify the device model.']);
  assert.deepEqual(project.research.research_questions,['Which date?','What is the primary source?']);
  assert.throws(()=>Director.updateBrief(project,{target_duration_seconds:0}),/Target duration/);
});

test('niche profiles are meaningfully different and custom edits persist',()=>{
  const cyber=Director.defaultStyleProfile('cybersecurity');
  const history=Director.defaultStyleProfile('history');
  const gaming=Director.defaultStyleProfile('gaming');
  assert.notDeepEqual(cyber.preferred_media,history.preferred_media);
  assert.ok(cyber.visual_language.includes('network'));
  assert.ok(history.visual_language.includes('archival'));
  assert.ok(gaming.preferred_media.includes('gameplay'));
  const project=makeProject();
  cyber.visual_language='My custom network-diagram treatment.';
  cyber.pacing='moderate';
  Director.applyStyleProfile(project,cyber);
  assert.equal(project.visual_style_profile.visual_language,'My custom network-diagram treatment.');
  assert.equal(project.creative_brief.niche,'cybersecurity');
  assert.throws(()=>Director.applyStyleProfile(project,{...cyber,preferred_media:['unknown_media']}),/supported visual medium/);
});

test('research source and video reference intake validate URLs and keep references separate',()=>{
  const project=makeProject();
  const source=Director.addResearchSource(project,{
    url:'https://example.org/report',title:'Technical report',publisher:'Example Institute',
    source_type:'primary',access_status:'public',confidence:'high'
  });
  const reference=Director.addReferenceVideo(project,{
    url:'https://video.example/watch/123',title:'A public format reference',
    creator:'Example Creator',platform:'Video site',observed_format:['Cold open','Animated diagram']
  });
  assert.equal(source.source_type,'primary');
  assert.equal(reference.reference_only,true);
  assert.ok(project.research.visual_style_observations.some(text=>text.includes('Cold open')));
  assert.throws(()=>Director.addResearchSource(project,{url:'javascript:alert(1)'}),/HTTP or HTTPS/);
  assert.throws(()=>Director.addReferenceVideo(project,{url:'file:///private/video.mp4'}),/HTTP or HTTPS/);
  assert.equal(Core.validateProject(project).length,0);
});

test('claims cannot cite unknown sources and retain separate evidence classifications',()=>{
  const project=makeProject();
  const source=Director.addResearchSource(project,{url:'https://example.org/facts',source_type:'primary'});
  const factual=Director.addResearchClaim(project,{
    text:'The report was published in 2024.',classification:'factual',
    verification_status:'verified',confidence:'high',source_ids:[source.id]
  });
  const opinion=Director.addResearchClaim(project,{
    text:'This design is elegant.',classification:'opinion',
    verification_status:'opinion',confidence:'medium',evidence_required:false
  });
  assert.equal(factual.evidence_required,true);
  assert.equal(opinion.evidence_required,false);
  assert.throws(()=>Director.addResearchClaim(project,{
    text:'A claim with a dangling source.',classification:'factual',source_ids:['not-a-source']
  }),/Unknown source/);
  assert.equal(Core.validateProject(project).length,0);
});

test('narration is split into timed visual beats with profile-aware media and required fields',()=>{
  const project=makeProject();
  Director.updateBrief(project,{
    niche:'cybersecurity',target_duration_seconds:8,
    narration_script:'A device connects to a network. The system checks the user identity. The network blocks suspicious access.'
  });
  Director.applyStyleProfile(project,Director.defaultStyleProfile('cybersecurity'));
  const plan=Director.buildShotPlan(project);
  assert.equal(plan.method,'assisted_rules');
  assert.equal(plan.status,'draft');
  assert.equal(plan.total_frames,240);
  assert.equal(plan.beats.length,3);
  assert.equal(plan.beats[0].start_frame,0);
  assert.equal(plan.beats.at(-1).end_frame,240);
  assert.ok(plan.beats.every(beat=>beat.end_frame>beat.start_frame));
  assert.ok(plan.beats.every(beat=>beat.visual_purpose&&beat.asset_requirements.length&&beat.effect_notes));
  assert.ok(plan.beats.every(beat=>beat.media_mix.every(media=>Director.MEDIA_TYPES.includes(media))));
  assert.equal(plan.beats[0].visual_role,'illustration');
  assert.throws(()=>Director.buildShotPlan(project,{duration_seconds:0}),/Target duration/);
});

test('shot planner refuses an impossible duration instead of creating zero-frame beats',()=>{
  const project=makeProject();
  project.creative_brief.narration_script='One sentence. Two sentences. Three sentences.';
  assert.throws(()=>Director.buildShotPlan(project,{duration_seconds:0.05,fps:30}),/too short/);
});

test('readiness gate blocks unsupported factual claims and distinguishes illustration',()=>{
  const project=makeProject();
  const claim=Director.addResearchClaim(project,{
    text:'An unverified statement.',classification:'factual',
    verification_status:'unverified',confidence:'unassessed'
  });
  project.shot_plan={
    id:'plan-readiness',method:'user_authored',status:'draft',fps:30,total_frames:30,
    beats:[{
      id:'shot-proof',start_frame:0,end_frame:30,narration:'An unverified statement.',
      visual_purpose:'Show the statement',media_mix:['source_footage'],
      visual_role:'factual_evidence',evidence_requirement:'actual_footage',
      evidence_claim_ids:[claim.id],asset_ids:[]
    }]
  };
  const report=Director.readinessReport(project);
  assert.equal(report.status,'blocked');
  assert.ok(report.blockers.some(item=>item.includes('not marked verified')));
  assert.ok(report.blockers.some(item=>item.includes('without a verified factual/comparative source')));
  project.shot_plan.beats[0].visual_role='illustration';
  const illustration=Director.readinessReport(project);
  assert.ok(!illustration.blockers.some(item=>item.includes('uses claim')));
});

test('rights decision needs a documented basis and is reflected in the readiness gate',()=>{
  const project=makeProject();
  Core.addAsset(project,makeAsset());
  assert.ok(Director.readinessReport(project).blockers.some(item=>item.includes('rights review')));
  assert.throws(()=>Director.applyAssetRightsDecision(project,'asset-source',{
    decision:'approved',basis:'too short',reviewer:'Owner'
  }),/at least 10 characters/);
  Director.applyAssetRightsDecision(project,'asset-source',{
    decision:'approved',basis:'Created by our team for this project; no third-party content.',
    intended_use:'Use as a simple explainer visual.',reviewer:'Project owner'
  });
  const report=Director.readinessReport(project);
  assert.equal(report.blockers.length,0,report.blockers.join('\n'));
  assert.equal(report.status,'approved');
  const final=Director.finaliseRightsReview(project);
  assert.equal(final.status,'approved');
  assert.equal(project.shot_plan,undefined);
  assert.equal(project.rights_review.asset_reviews[0].decision,'approved');
  assert.equal(Core.validateProject(project).length,0);
});

test('core validator rejects missing shot claims and missing shot assets',()=>{
  const project=makeProject();
  project.shot_plan={
    id:'plan-invalid',method:'user_authored',status:'draft',fps:30,total_frames:30,
    beats:[{
      id:'shot-invalid',start_frame:0,end_frame:30,narration:'Proof.',
      visual_purpose:'Show proof',media_mix:['source_footage'],visual_role:'factual_evidence',
      evidence_requirement:'actual_footage',asset_ids:['asset-missing'],
      evidence_claim_ids:['claim-missing']
    }]
  };
  const errors=Core.validateProject(project);
  assert.ok(errors.some(error=>error.includes('references missing asset')));
  assert.ok(errors.some(error=>error.includes('references missing research claim')));
  assert.ok(errors.some(error=>error.includes('must reference at least one claim')));
});

test('verified claims cannot rely on a blocked or login-only source',()=>{
  const project=makeProject();
  const source=Director.addResearchSource(project,{
    url:'https://example.org/login-only',access_status:'login_required',confidence:'high'
  });
  Director.addResearchClaim(project,{
    text:'A verified statement from a restricted page.',classification:'factual',
    verification_status:'verified',confidence:'high',source_ids:[source.id]
  });
  const report=Director.readinessReport(project);
  assert.ok(report.blockers.some(item=>item.includes('not marked publicly accessible')));
});

test('actual-footage requirement needs a linked, rights-reviewed video asset',()=>{
  const project=makeProject();
  const source=Director.addResearchSource(project,{
    url:'https://example.org/official-event-report',access_status:'public',confidence:'high'
  });
  const claim=Director.addResearchClaim(project,{
    text:'A video documents the event.',classification:'factual',
    verification_status:'verified',confidence:'high',source_ids:[source.id]
  });
  project.shot_plan={
    id:'plan-actual-footage',method:'user_authored',status:'draft',fps:30,total_frames:30,
    beats:[{
      id:'shot-actual-footage',start_frame:0,end_frame:30,narration:'A video documents the event.',
      visual_purpose:'Show the actual recording',media_mix:['source_footage'],
      visual_role:'factual_evidence',evidence_requirement:'actual_footage',
      evidence_claim_ids:[claim.id],asset_ids:[]
    }]
  };
  assert.ok(Director.readinessReport(project).blockers.some(item=>item.includes('imported, rights-reviewed video asset')));
  const video={
    id:'asset-event-video',label:'Event video',uri:'indexeddb://assets/asset-event-video',media_type:'video',
    metadata:{duration_seconds:1},provenance:{source_type:'user_supplied'},
    rights:{status:'pending',attribution_required:false,restrictions:[]},tags:[]
  };
  Core.addAsset(project,video);
  Director.applyAssetRightsDecision(project,video.id,{
    decision:'approved',basis:'The video is original footage created by the project owner.',
    reviewer:'Project owner',intended_use:'Substantiate the described event.'
  });
  project.shot_plan.beats[0].asset_ids=[video.id];
  const report=Director.readinessReport(project);
  assert.deepEqual(report.blockers,[]);
});

test('reference records must stay reference-only and approved rights reviews need audit fields',()=>{
  const project=makeProject();
  project.research.reference_videos.push({
    id:'reference-bad',url:'https://example.org/video',retrieved_at:'2026-11-28T00:00:00.000Z',reference_only:false
  });
  project.rights_review.asset_reviews.push({
    asset_id:'asset-not-present',decision:'approved',basis:'A review basis with enough characters.',
    reviewer:'Owner',reviewed_at:'2026-11-28T00:00:00.000Z'
  });
  const errors=Core.validateProject(project);
  assert.ok(errors.some(error=>error.includes('reference_only')));
  assert.ok(errors.some(error=>error.includes('missing asset')));
});

