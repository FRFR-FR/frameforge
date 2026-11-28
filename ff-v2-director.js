/* FrameForge V2 research intake and visual director.
   Deliberately transparent assistant/user-guided tooling; no hidden web scraping or autonomous fact verification. */
(function (root) {
  'use strict';

  const MEDIA_TYPES = ['character_cutout','source_footage','procedural_2d','three_d','diagram','typography','combination','maps','screenshots','gameplay'];
  const VISUAL_ROLES = ['illustration','factual_evidence','comparative_evidence','reconstruction','opinion','demonstration'];
  const PROFILES = {
    unclassified: {
      id:'style-general', niche:'unclassified', label:'General / unclassified',
      visual_language:'Choose a subject-specific visual treatment after research. Each shot needs a clear explanatory purpose.',
      preferred_media:['procedural_2d','three_d','typography','combination'], pacing:'variable',
      camera_language:'Use motivated camera movement; vary framing and hold shots long enough to understand the visual.',
      sound_language:'Use restrained sound design that reinforces visible events and never competes with narration.',
      avoid:['Generic unrelated B-roll','Decorative overlays without an explanatory purpose','Unverified visuals presented as proof'],
      creator_references:[]
    },
    cybersecurity: {
      id:'style-cybersecurity', niche:'cybersecurity', label:'Cybersecurity',
      visual_language:'Technical visual storytelling: realistic device/UI simulations, network topology, packet/data paths, access-control diagrams and clearly labelled threat models.',
      preferred_media:['procedural_2d','three_d','diagram','screenshots','typography'], pacing:'brisk',
      camera_language:'Move through systems: push into a device, track a data route, zoom to a control point, then hold on the security consequence.',
      sound_language:'Precise clicks, restrained digital pulses and impact accents tied to interface events; keep narration dominant.',
      avoid:['Generic stock footage unrelated to the described attack or defence','Fake interface screenshots presented as real evidence','Unlabelled simulated dashboards','Hacker hoodie clichés']
    },
    history: {
      id:'style-history', niche:'history', label:'History',
      visual_language:'Chronology-led documentary visuals: sourced archival material, geographic maps, timelines, artefact details and clearly labelled reconstructions.',
      preferred_media:['maps','source_footage','procedural_2d','three_d','typography'], pacing:'measured',
      camera_language:'Pan across maps, track along timelines, use slow detail pushes on artefacts, and reserve 3D movement for explanatory reconstructions.',
      sound_language:'Location-appropriate ambience and restrained period-inspired textures; do not imply reconstructed audio is archival.',
      avoid:['Invented archival images presented as authentic','Modern visuals implying historical provenance','Unlabelled speculative reconstructions']
    },
    science: {
      id:'style-science', niche:'science', label:'Science',
      visual_language:'Explanatory visualisation: accurate diagrams, scale comparisons, procedural animation, charts and carefully labelled 3D models.',
      preferred_media:['three_d','diagram','procedural_2d','source_footage','typography'], pacing:'moderate',
      camera_language:'Use camera moves to reveal scale, process and spatial relationships; pause at important states and label units.',
      sound_language:'Clear narration with subtle mechanical/environmental textures; use cues to reinforce process changes.',
      avoid:['Scientifically inaccurate decorative imagery','Charts without units or sources','Scale changes that mislead','Illustrations shown as direct observation']
    },
    mysteries: {
      id:'style-mysteries', niche:'mysteries', label:'Mysteries',
      visual_language:'Evidence-led investigation: maps, dated documents, timelines, location context, source excerpts and labelled reconstructions.',
      preferred_media:['maps','procedural_2d','typography','source_footage','three_d'], pacing:'variable',
      camera_language:'Controlled reveals, deliberate push-ins on specific clues and timeline/map moves that clarify relationships rather than obscure them.',
      sound_language:'Sparse tension beds and restrained transition cues; leave space around evidence and quotations.',
      avoid:['Fabricated documents presented as originals','Unfounded certainty','Sensational effects that distort evidence']
    },
    finance: {
      id:'style-finance', niche:'finance', label:'Finance',
      visual_language:'Data-first storytelling: sourced charts, market timelines, cash-flow diagrams, product/interface demonstrations and clear risk/assumption labels.',
      preferred_media:['diagram','procedural_2d','typography','screenshots','source_footage'], pacing:'brisk',
      camera_language:'Track along time series, highlight meaningful inflection points, compare like-for-like figures and show the date range.',
      sound_language:'Clean rhythmic accents on chart reveals; avoid dramatic cues that imply certainty or returns.',
      avoid:['Unsourced prices or returns','Misleading truncated axes','Guaranteed-outcome language','Unlabelled projections or illustrative data']
    },
    gaming: {
      id:'style-gaming', niche:'gaming', label:'Gaming',
      visual_language:'Gameplay-led visuals, original HUD/ability diagrams, character/object cut-outs, map callouts and 3D staging when it explains mechanics.',
      preferred_media:['gameplay','character_cutout','three_d','diagram','typography'], pacing:'fast',
      camera_language:'Track player/object movement, punch in on mechanics, use controlled speed ramps and keep gameplay context legible.',
      sound_language:'Sync UI, movement and impact sounds to visible actions; preserve important in-game audio when supplied and permitted.',
      avoid:['Unrelated gameplay filler','Fake gameplay presented as actual captured footage','Unlicensed music','Unreadable overlays']
    },
    entertainment_power_scaling: {
      id:'style-entertainment-power', niche:'entertainment_power_scaling', label:'Entertainment / power scaling',
      visual_language:'Character-focused analysis: supplied/licensed cut-outs, ability demonstrations, original comparison diagrams, scale graphics and labelled illustrative 3D staging.',
      preferred_media:['character_cutout','diagram','three_d','typography','source_footage'], pacing:'brisk',
      camera_language:'Use character reveals, motivated lateral comparisons, controlled push-ins and clear side-by-side scale framing.',
      sound_language:'Short whooshes and impacts only when they match a visible action; use restrained stings for reveals.',
      avoid:['Unrelated B-roll','Unverified feats stated as canon','Illustrative renders presented as source footage','Assuming franchise assets are free to reuse']
    }
  };

  const clone = value => value == null ? value : JSON.parse(JSON.stringify(value));
  const studio = () => root.FFV2Studio;
  const currentProject = () => studio()?.getProject?.();
  const status = (message, kind) => {
    const node = root.document?.getElementById('ffv2DirectorStatus');
    if (node) { node.textContent = message; node.dataset.kind = kind || 'info'; }
  };
  const el = id => root.document?.getElementById(id);
  const makeId = prefix => root.FFV2Core.makeId(prefix);

  function defaultStyleProfile(niche) {
    return clone(PROFILES[niche] || PROFILES.unclassified);
  }

  function ensureDirectorData(project) {
    if (!project) return false;
    let changed = false;
    project.creative_brief = project.creative_brief || {};
    const briefDefaults = {
      topic:'Untitled video project', niche:'unclassified', audience:'', platform:'youtube_longform',
      target_duration_seconds:30, tone:'', visual_direction:'', desired_style:'',
      narration_script:'', research_questions:[], ambiguities_to_resolve:[], restrictions:[], constraints:[]
    };
    for (const [key,value] of Object.entries(briefDefaults)) {
      if (project.creative_brief[key] === undefined) { project.creative_brief[key] = clone(value); changed = true; }
    }
    project.research = project.research || {};
    for (const [key,value] of Object.entries({
      sources:[], claims:[], reference_videos:[], research_questions:[],
      confidence_notes:[], visual_style_observations:[]
    })) {
      if (!Array.isArray(project.research[key])) { project.research[key] = clone(value); changed = true; }
    }
    if (!project.visual_style_profile) {
      project.visual_style_profile = defaultStyleProfile(project.creative_brief.niche);
      changed = true;
    }
    if (!project.rights_review) {
      project.rights_review = { status:'not_started', asset_reviews:[] };
      changed = true;
    }
    if (!Array.isArray(project.rights_review.asset_reviews)) {
      project.rights_review.asset_reviews = [];
      changed = true;
    }
    return changed;
  }

  function updateBrief(project, updates) {
    if (!project) throw new Error('Open a V2 project first.');
    ensureDirectorData(project);
    const allowed = [
      'topic','niche','audience','platform','target_duration_seconds','tone',
      'visual_direction','desired_style','narration_script','research_questions','ambiguities_to_resolve','restrictions','constraints'
    ];
    for (const key of allowed) {
      if (!Object.prototype.hasOwnProperty.call(updates || {}, key)) continue;
      if (key === 'target_duration_seconds') {
        const duration = Number(updates[key]);
        if (!Number.isFinite(duration) || duration <= 0 || duration > 7200) throw new Error('Target duration must be between 0 and 7,200 seconds.');
        project.creative_brief[key] = duration;
      } else if (['research_questions','ambiguities_to_resolve','restrictions','constraints'].includes(key)) {
        project.creative_brief[key] = Array.isArray(updates[key])
          ? updates[key].map(value => String(value).trim()).filter(Boolean).slice(0,30)
          : String(updates[key] || '').split(/\n|;/).map(value => value.trim()).filter(Boolean).slice(0,30);
      } else {
        project.creative_brief[key] = String(updates[key] == null ? '' : updates[key]).slice(0, key === 'narration_script' ? 100000 : 4000);
      }
    }
    if (Array.isArray(project.creative_brief.research_questions)) {
      project.research.research_questions = clone(project.creative_brief.research_questions);
    }
    return project.creative_brief;
  }

  function applyStyleProfile(project, profile) {
    if (!project) throw new Error('Open a V2 project first.');
    ensureDirectorData(project);
    const next = clone(profile || {});
    const required = ['id','niche','label','visual_language','preferred_media','pacing','camera_language','sound_language','avoid'];
    if (required.some(key => next[key] === undefined)) throw new Error('The visual style profile is incomplete.');
    if (!Array.isArray(next.preferred_media) || !next.preferred_media.length ||
        next.preferred_media.some(item => !MEDIA_TYPES.includes(item))) throw new Error('Choose at least one supported visual medium.');
    if (!['slow','measured','moderate','brisk','fast','variable'].includes(next.pacing)) throw new Error('Unsupported pacing profile.');
    next.avoid = Array.isArray(next.avoid) ? next.avoid.map(String).slice(0,30) : [];
    project.visual_style_profile = next;
    project.creative_brief.niche = next.niche;
    return next;
  }

  function validateWebUrl(value, label) {
    let url;
    try { url = new URL(String(value || '').trim()); }
    catch (_) { throw new Error((label || 'URL') + ' must be a valid absolute HTTP or HTTPS URL.'); }
    if (!['http:','https:'].includes(url.protocol)) throw new Error((label || 'URL') + ' must use HTTP or HTTPS.');
    return url.href;
  }

  function addResearchSource(project, input) {
    ensureDirectorData(project);
    const source = {
      id: makeId('source'), url:validateWebUrl(input?.url,'Source URL'),
      title:String(input?.title || '').trim().slice(0,500),
      publisher:String(input?.publisher || '').trim().slice(0,200),
      published_at:input?.published_at || undefined,
      retrieved_at:new Date().toISOString(),
      source_type:input?.source_type || 'other',
      access_status:input?.access_status || 'unknown',
      confidence:input?.confidence || 'unassessed',
      notes:String(input?.notes || '').slice(0,3000)
    };
    project.research.sources.push(source);
    project.research.researched_at = new Date().toISOString();
    return source;
  }

  function addReferenceVideo(project, input) {
    ensureDirectorData(project);
    const reference = {
      id:makeId('reference'),
      url:validateWebUrl(input?.url,'Reference-video URL'),
      title:String(input?.title || '').trim().slice(0,500),
      creator:String(input?.creator || '').trim().slice(0,200),
      platform:String(input?.platform || '').trim().slice(0,100),
      retrieved_at:new Date().toISOString(),
      access_status:input?.access_status || 'unknown',
      notes:String(input?.notes || '').slice(0,4000),
      observed_format:Array.isArray(input?.observed_format) ? input.observed_format.map(String).slice(0,20) : [],
      reference_only:true
    };
    if (input?.published_at) reference.published_at = input.published_at;
    project.research.reference_videos.push(reference);
    project.research.visual_style_observations.push(...reference.observed_format.map(value => 'Reference "'+(reference.title||reference.url)+'": '+value));
    return reference;
  }

  function addResearchClaim(project, input) {
    ensureDirectorData(project);
    const sourceIds = Array.isArray(input?.source_ids)
      ? input.source_ids.map(String).filter(Boolean)
      : String(input?.source_ids || '').split(',').map(value => value.trim()).filter(Boolean);
    const available = new Set(project.research.sources.map(source => source.id));
    const missing = sourceIds.filter(id => !available.has(id));
    if (missing.length) throw new Error('Unknown source ID(s): ' + missing.join(', '));
    const classification = input?.classification || 'factual';
    if (!['factual','comparative','interpretation','opinion','illustrative'].includes(classification)) throw new Error('Unsupported claim classification.');
    const claim = {
      id:makeId('claim'),
      text:String(input?.text || '').trim().slice(0,2000),
      source_ids:Array.from(new Set(sourceIds)),
      classification,
      evidence_required:input?.evidence_required === undefined ? ['factual','comparative'].includes(classification) : Boolean(input.evidence_required),
      confidence:input?.confidence || 'unassessed',
      verification_status:input?.verification_status || 'unverified',
      uncertainty_notes:String(input?.uncertainty_notes || '').slice(0,2000),
      caveat:String(input?.caveat || '').slice(0,2000)
    };
    if (!claim.text) throw new Error('Enter the claim text first.');
    project.research.claims.push(claim);
    return claim;
  }

  function splitNarration(script) {
    const text = String(script || '').trim();
    if (!text) return [];
    const paragraphs = text.split(/\n{2,}/).map(part => part.trim()).filter(Boolean);
    const beats = [];
    for (const paragraph of paragraphs) {
      const sentences = paragraph.match(/[^.!?…]+(?:[.!?…]+["'”’)]*|$)/g) || [paragraph];
      let chunk = '';
      for (const sentence of sentences) {
        const next = (chunk ? chunk + ' ' : '') + sentence.trim();
        const words = next.split(/\s+/).filter(Boolean).length;
        if (chunk && words > 34) {
          beats.push(chunk.trim());
          chunk = sentence.trim();
        } else chunk = next;
      }
      if (chunk.trim()) beats.push(chunk.trim());
    }
    return beats;
  }

  function inferMedia(text, profile, index) {
    const lower = text.toLowerCase();
    if (/\b(map|country|city|border|route|location|where|battlefield)\b/.test(lower) && profile.preferred_media.includes('maps')) return ['maps','typography'];
    if (/\b(data|percent|percentage|rate|chart|number|growth|decline|revenue|price)\b/.test(lower) && profile.preferred_media.includes('diagram')) return ['diagram','typography'];
    if (/\b(inside|how it works|process|system|engine|network|anatomy|structure)\b/.test(lower) && profile.preferred_media.includes('three_d')) return ['three_d','diagram'];
    const preferred = profile.preferred_media;
    if (!preferred.length) return ['procedural_2d'];
    return [preferred[index % preferred.length]];
  }

  function inferEvidenceRequirement(text, media) {
    const lower = text.toLowerCase();
    if (/\b(footage|recording|video shows|photo shows|camera captured|actual image|caught on camera|documented the event)\b/.test(lower)) return 'actual_footage';
    if (/\b(percent|percentage|rate|data|survey|study|statistic|number|revenue|price|chart)\b/.test(lower) || media.includes('diagram')) return 'sourced_data';
    if (/\b(document|report|letter|court|filing|official|according to|record|archive|source)\b/.test(lower)) return 'source_document';
    return 'none';
  }

  function inferAudioCues(text, media) {
    const lower = text.toLowerCase();
    const cues = [];
    if (/\b(reveal|introduce|uncover|discover|turns out|surprise)\b/.test(lower)) cues.push('Short restrained reveal accent on the visual reveal, only if it does not compete with narration.');
    if (/\b(impact|collision|crash|strike|explosion|hit|slam)\b/.test(lower)) cues.push('Sync a brief impact sound to the visible event; do not add a sound if the event is only metaphorical.');
    if (media.includes('maps')) cues.push('Optional subtle map transition or location ambience; keep factual labels readable.');
    return cues;
  }

  function inferPurpose(text, media) {
    const words = text.trim().split(/\s+/).filter(Boolean);
    const excerpt = words.slice(0, Math.min(8, words.length)).join(' ');
    if (media.includes('maps')) return 'Establish the geographic context and make the named place or route understandable.';
    if (media.includes('diagram')) return 'Translate the spoken relationship into a clearly labelled diagram or data visual.';
    if (media.includes('three_d')) return 'Reveal spatial structure or a process through a labelled 3D explanation.';
    if (media.includes('source_footage')) return 'Use a relevant, rights-reviewed shot that directly depicts the spoken subject.';
    if (media.includes('gameplay')) return 'Show the relevant gameplay action and preserve enough context to understand the mechanic.';
    if (media.includes('character_cutout')) return 'Show the relevant character or subject with an original, readable comparison or action.';
    return 'Create an original visual for: "' + excerpt + '". Keep the image specific to the narration rather than using unrelated filler.';
  }

  function buildShotPlan(project, options) {
    ensureDirectorData(project);
    const brief = project.creative_brief;
    const sequence = root.FFV2Core.getMainSequence(project);
    const fps = Number(options?.fps || sequence.fps || project.settings.fps || 30);
    const targetSeconds = Number(options?.duration_seconds || brief.target_duration_seconds || 30);
    if (!Number.isFinite(fps) || fps <= 0 || fps > 240) throw new Error('Project frame rate is invalid.');
    if (!Number.isFinite(targetSeconds) || targetSeconds <= 0 || targetSeconds > 7200) throw new Error('Target duration must be between 0 and 7,200 seconds.');
    const script = String(options?.script ?? brief.narration_script ?? '').trim();
    const sentences = splitNarration(script);
    if (!sentences.length) throw new Error('Add a narration script before generating a timed shot plan.');
    const profile = project.visual_style_profile || defaultStyleProfile(brief.niche);
    const totalFrames = Math.max(1, Math.round(targetSeconds * fps));
    if (totalFrames < sentences.length) throw new Error('The target duration is too short for the number of narration beats. Increase duration or combine sentences into fewer paragraphs.');
    const weights = sentences.map(sentence => Math.max(1, sentence.split(/\s+/).filter(Boolean).length));
    const totalWeight = weights.reduce((sum, value) => sum + value, 0);
    let cursor = 0;
    const beats = sentences.map((narration, index) => {
      const rawEnd = index === sentences.length - 1
        ? totalFrames
        : Math.max(cursor + 1, Math.round(totalFrames * weights.slice(0,index+1).reduce((sum,value)=>sum+value,0) / totalWeight));
      const end = Math.min(totalFrames, rawEnd);
      const media = inferMedia(narration, profile, index);
      const beat = {
        id:makeId('shot'),
        start_frame:cursor,
        end_frame:end,
        narration,
        visual_purpose:inferPurpose(narration,media),
        media_mix:media,
        visual_role:'illustration',
        evidence_requirement:inferEvidenceRequirement(narration,media),
        asset_ids:[],
        camera_movement:profile.camera_language,
        visual_actions:['Start with a clear subject-specific composition','Animate only the elements that explain this beat','Hold the key visual until the narration point is understood'],
        asset_requirements:['Identify exact subjects, locations, objects or data before acquiring media','Use only assets with reviewed provenance and rights'],
        transition_in:index===0?'Opening shot':'Cut or motivated match transition',
        transition_out:'Cut on the next narration beat unless a motivated transition is needed',
        effect_notes:'Use restrained, topic-specific motion graphics or practical VFX only when they clarify the beat.',
        audio_cues:inferAudioCues(narration,media),
        evidence_claim_ids:[],
        notes:'Rule-assisted draft. Review timing, visual accuracy, evidence role and rights before rendering.'
      };
      cursor=end;
      return beat;
    });
    project.shot_plan = {
      id:makeId('shotplan'), method:'assisted_rules', status:'draft', fps,
      generated_at:new Date().toISOString(), total_frames:totalFrames,
      director_notes:'This is a deterministic first-pass shot plan, not autonomous research or fact verification. Review every beat and replace suggestions that do not fit the actual topic.',
      beats
    };
    sequence.duration_frames = Math.max(sequence.duration_frames, totalFrames);
    return project.shot_plan;
  }

  function readinessReport(project) {
    ensureDirectorData(project);
    const blockers = [];
    const warnings = [];
    const sources = new Map(project.research.sources.map(item => [item.id,item]));
    const claims = new Map(project.research.claims.map(item => [item.id,item]));
    const reviews = new Map((project.rights_review.asset_reviews || []).map(item => [item.asset_id,item]));
    for (const claim of project.research.claims) {
      const needsEvidence = claim.evidence_required !== false || ['factual','comparative'].includes(claim.classification);
      if (needsEvidence && !claim.source_ids?.length) blockers.push('Claim "'+claim.text+'" has no cited research source.');
      if (needsEvidence && claim.verification_status !== 'verified') blockers.push('Claim "'+claim.text+'" is not marked verified.');
      for (const id of claim.source_ids || []) if (!sources.has(id)) blockers.push('Claim "'+claim.text+'" cites missing source '+id+'.');
      if (claim.confidence === 'low' || claim.confidence === 'unassessed') warnings.push('Claim "'+claim.text+'" has '+claim.confidence+' confidence.');
      if (claim.verification_status === 'disputed') warnings.push('Claim "'+claim.text+'" is disputed and should not be presented as established fact.');
    }
    for (const beat of project.shot_plan?.beats || []) {
      if (beat.end_frame <= beat.start_frame) blockers.push('Shot '+beat.id+' has invalid frame timing.');
      if (['factual_evidence','comparative_evidence'].includes(beat.visual_role)) {
        if (!beat.evidence_claim_ids?.length) blockers.push('Shot '+beat.id+' is marked as evidence but has no linked claim.');
        for (const id of beat.evidence_claim_ids || []) {
          const claim = claims.get(id);
          if (!claim) blockers.push('Shot '+beat.id+' references missing claim '+id+'.');
          else if (claim.verification_status !== 'verified' || !claim.source_ids?.length ||
                   !['factual','comparative'].includes(claim.classification)) {
            blockers.push('Shot '+beat.id+' uses claim "'+claim.text+'" as proof without a verified factual/comparative source.');
          }
        }
      }
      for (const id of beat.evidence_claim_ids || []) if (!claims.has(id)) blockers.push('Shot '+beat.id+' references missing claim '+id+'.');
      for (const id of beat.asset_ids || []) if (!project.assets.some(asset => asset.id === id)) blockers.push('Shot '+beat.id+' references missing asset '+id+'.');
      const evidenceRequirement = beat.evidence_requirement || 'none';
      if (evidenceRequirement === 'actual_footage' && !beat.media_mix.includes('source_footage')) blockers.push('Shot '+beat.id+' needs actual source footage but its media mix does not include source_footage.');
      if (evidenceRequirement === 'official_screenshot' && !beat.media_mix.includes('screenshots')) blockers.push('Shot '+beat.id+' needs an official screenshot but its media mix does not include screenshots.');
      if (evidenceRequirement === 'sourced_data' && !['factual_evidence','comparative_evidence'].includes(beat.visual_role)) warnings.push('Shot '+beat.id+' uses data but is not marked as evidence; label the data as illustrative or link verified claims.');
    }
    for (const asset of project.assets) {
      const decision = reviews.get(asset.id);
      const statusValue = asset.rights?.status || 'unknown';
      if (statusValue !== 'approved' || !asset.rights?.review_basis) {
        blockers.push('Asset "'+(asset.label || asset.id)+'" has not passed documented rights review.');
      }
      if (decision?.decision === 'rejected' || statusValue === 'rejected') blockers.push('Asset "'+(asset.label || asset.id)+'" is rejected and must not be used.');
      if (decision?.decision === 'permission_required' || statusValue === 'restricted') blockers.push('Asset "'+(asset.label || asset.id)+'" needs permission or has usage restrictions requiring review.');
      if (asset.rights?.attribution_required && !asset.rights?.attribution_text) blockers.push('Asset "'+(asset.label || asset.id)+'" requires attribution text.');
      if (!asset.provenance?.source_type || asset.provenance.source_type === 'unknown') warnings.push('Asset "'+(asset.label || asset.id)+'" has incomplete provenance.');
    }
    for (const ref of project.research.reference_videos || []) {
      if (ref.reference_only !== true) blockers.push('Reference video '+ref.id+' is not marked reference-only.');
    }
    return {
      status:blockers.length?'blocked':warnings.length?'approved_with_limits':'approved',
      blockers:Array.from(new Set(blockers)),
      warnings:Array.from(new Set(warnings)),
      reference_video_notice:'Reference-video URLs are style/format references only. They do not grant permission to copy or reuse video, audio, branding or other protected material.'
    };
  }

  function applyAssetRightsDecision(project, assetId, input) {
    ensureDirectorData(project);
    const asset = project.assets.find(item => item.id === assetId);
    if (!asset) throw new Error('Asset not found in this project.');
    const decision = input?.decision || 'needs_review';
    if (!['needs_review','approved','approved_with_limits','permission_required','rejected'].includes(decision)) throw new Error('Unsupported rights decision.');
    const now = new Date().toISOString();
    const basis = String(input?.basis || '').trim();
    const reviewer = String(input?.reviewer || 'Project owner').trim();
    if (['approved','approved_with_limits'].includes(decision) && basis.length < 10) throw new Error('An approval requires a documented rights basis of at least 10 characters.');
    if (['approved','approved_with_limits'].includes(decision) && !reviewer) throw new Error('A reviewer is required for an approval.');
    const existing = asset.rights || {};
    const statusValue = decision === 'approved' || decision === 'approved_with_limits' ? 'approved'
      : decision === 'permission_required' ? 'restricted'
      : decision === 'rejected' ? 'rejected' : 'pending';
    asset.rights = Object.assign({}, existing, {
      status:statusValue,
      review_basis:basis,
      reviewed_by:reviewer,
      reviewed_at:now,
      permission_reference:String(input?.permission_reference || '').trim(),
      intended_use:String(input?.intended_use || '').trim(),
      attribution_text:String(input?.attribution_text || existing.attribution_text || '').trim(),
      restrictions:Array.isArray(input?.restrictions) ? input.restrictions.map(String) : (decision==='approved_with_limits' ? [String(input?.limit || 'Use only within the documented permission scope.')] : [])
    });
    const entries = project.rights_review.asset_reviews;
    const record = {
      asset_id:assetId, decision, basis, reviewer, reviewed_at:now,
      permission_reference:asset.rights.permission_reference,
      intended_use:asset.rights.intended_use,
      restrictions:asset.rights.restrictions,
      attribution_text:asset.rights.attribution_text
    };
    const index = entries.findIndex(item => item.asset_id === assetId);
    if (index >= 0) entries[index] = record;
    else entries.push(record);
    project.rights_review.status = 'in_review';
    project.rights_review.reviewer = reviewer;
    return asset;
  }

  function finaliseRightsReview(project) {
    const report = readinessReport(project);
    project.rights_review.status = report.status;
    project.rights_review.reviewed_at = new Date().toISOString();
    project.rights_review.reviewer = project.rights_review.reviewer || 'Project owner';
    project.rights_review.notes = report.blockers.concat(report.warnings).join('\n').slice(0,6000);
    if (project.shot_plan) project.shot_plan.status = report.blockers.length || report.warnings.length ? 'review_required' : 'approved';
    return report;
  }

  function projectSummary(project) {
    ensureDirectorData(project);
    return {
      topic:project.creative_brief.topic,
      niche:project.creative_brief.niche,
      source_count:project.research.sources.length,
      reference_video_count:project.research.reference_videos.length,
      claim_count:project.research.claims.length,
      shot_count:project.shot_plan?.beats?.length || 0,
      asset_count:project.assets.length,
      readiness:readinessReport(project)
    };
  }

  function csv(values) { return (values || []).map(value => String(value).replace(/[\r\n]+/g,' ').trim()).filter(Boolean).join(', '); }

  function renderSources(project) {
    const host = el('ffv2ResearchSourceList');
    if (!host) return;
    host.replaceChildren();
    for (const source of project.research.sources) {
      const row = root.document.createElement('div'); row.className='ffv2-director-list-row';
      const title = root.document.createElement('a'); title.href=source.url; title.target='_blank'; title.rel='noopener noreferrer';
      title.textContent=(source.title || source.url)+' · '+source.source_type+' · '+source.confidence;
      const remove=root.document.createElement('button'); remove.type='button'; remove.className='button small quiet'; remove.textContent='Remove';
      remove.addEventListener('click',()=>{project.research.sources=project.research.sources.filter(item=>item.id!==source.id);project.research.claims.forEach(claim=>{claim.source_ids=(claim.source_ids||[]).filter(id=>id!==source.id);});markDirty();refresh();});
      row.append(title,remove);host.append(row);
    }
  }

  function renderReferenceVideos(project) {
    const host=el('ffv2ReferenceVideoList'); if(!host)return; host.replaceChildren();
    for(const item of project.research.reference_videos){
      const row=root.document.createElement('div');row.className='ffv2-director-list-row';
      const link=root.document.createElement('a');link.href=item.url;link.target='_blank';link.rel='noopener noreferrer';
      link.textContent=(item.title||item.url)+' · '+(item.creator||item.platform||'Reference');
      const remove=root.document.createElement('button');remove.type='button';remove.className='button small quiet';remove.textContent='Remove';
      remove.addEventListener('click',()=>{project.research.reference_videos=project.research.reference_videos.filter(ref=>ref.id!==item.id);markDirty();refresh();});
      row.append(link,remove);host.append(row);
    }
  }

  function renderClaims(project) {
    const host=el('ffv2ResearchClaimList');if(!host)return;host.replaceChildren();
    for(const claim of project.research.claims){
      const card=root.document.createElement('article');card.className='ffv2-director-claim';
      const heading=root.document.createElement('strong');heading.textContent=claim.classification+' · '+claim.verification_status;
      const text=root.document.createElement('p');text.textContent=claim.text;
      const sources=root.document.createElement('small');sources.textContent='Sources: '+((claim.source_ids||[]).join(', ')||'none');
      const remove=root.document.createElement('button');remove.type='button';remove.className='button small quiet';remove.textContent='Remove claim';
      remove.addEventListener('click',()=>{project.research.claims=project.research.claims.filter(item=>item.id!==claim.id);(project.shot_plan?.beats||[]).forEach(beat=>{beat.evidence_claim_ids=(beat.evidence_claim_ids||[]).filter(id=>id!==claim.id);});markDirty();refresh();});
      card.append(heading,text,sources,remove);host.append(card);
    }
  }

  function renderShotPlan(project) {
    const host=el('ffv2ShotPlanList');if(!host)return;host.replaceChildren();
    const plan=project.shot_plan;
    if(!plan?.beats?.length){host.textContent='No shot plan yet. Add narration and generate a first-pass plan.';return;}
    const fps=Number(plan.fps)||30;
    for(const beat of plan.beats){
      const card=root.document.createElement('article');card.className='ffv2-shot-card';
      const head=root.document.createElement('div');head.className='ffv2-shot-head';
      const timing=root.document.createElement('strong');timing.textContent='Shot '+(plan.beats.indexOf(beat)+1)+' · '+(beat.start_frame/fps).toFixed(2)+'–'+(beat.end_frame/fps).toFixed(2)+' s';
      const role=root.document.createElement('select');role.setAttribute('aria-label','Visual role for shot '+(plan.beats.indexOf(beat)+1));
      for(const value of VISUAL_ROLES){const option=root.document.createElement('option');option.value=value;option.textContent=value.replaceAll('_',' ');role.append(option);}
      role.value=beat.visual_role;
      role.addEventListener('change',()=>{beat.visual_role=role.value;markDirty();renderReadiness(project);});
      const evidence=root.document.createElement('select');
      evidence.setAttribute('aria-label','Evidence requirement for shot '+(plan.beats.indexOf(beat)+1));
      for(const value of ['none','source_document','actual_footage','official_screenshot','sourced_data','user_review']){
        const option=root.document.createElement('option');option.value=value;option.textContent='Need: '+value.replaceAll('_',' ');evidence.append(option);
      }
      evidence.value=beat.evidence_requirement||'none';
      evidence.addEventListener('change',()=>{beat.evidence_requirement=evidence.value;markDirty();renderReadiness(project);});
      head.append(timing,role,evidence);
      const narration=root.document.createElement('p');narration.className='ffv2-shot-narration';narration.textContent=beat.narration;
      const grid=root.document.createElement('div');grid.className='ffv2-director-grid';
      const fields=[
        ['Visual purpose','visual_purpose','textarea'],
        ['VFX / motion treatment','effect_notes','textarea'],
        ['Media mix (comma separated)','media_mix','input'],
        ['Camera movement','camera_movement','input'],
        ['Visual actions (one per line)','visual_actions','textarea'],
        ['Required assets / footage','asset_requirements','textarea'],
        ['Linked claim IDs (comma separated)','evidence_claim_ids','input'],
        ['Linked asset IDs (comma separated)','asset_ids','input'],
        ['Transition in','transition_in','input'],
        ['Transition out','transition_out','input'],
        ['SFX / audio cues','audio_cues','input']
      ];
      for(const [label,key,tag] of fields){
        const wrap=root.document.createElement('label');wrap.textContent=label;
        const control=root.document.createElement(tag);control.className='ffv2-director-input';
        if(tag==='textarea')control.rows=2;
        control.value=Array.isArray(beat[key])?csv(beat[key]):(beat[key]||'');
        control.addEventListener('change',()=>{
          if(['media_mix','evidence_claim_ids','asset_ids'].includes(key)) beat[key]=control.value.split(',').map(value=>value.trim()).filter(Boolean);
          else if(['visual_actions','asset_requirements','audio_cues'].includes(key)) beat[key]=control.value.split(/\n/).map(value=>value.trim()).filter(Boolean);
          else beat[key]=control.value;
          if(key==='evidence_claim_ids') beat[key]=Array.from(new Set(beat[key]));
          if(key==='media_mix') beat[key]=beat[key].filter(value=>MEDIA_TYPES.includes(value));
          markDirty();renderReadiness(project);
        });
        wrap.append(control);grid.append(wrap);
      }
      card.append(head,narration,grid);host.append(card);
    }
  }

  function renderRightsAssets(project) {
    const host=el('ffv2RightsAssetList');if(!host)return;host.replaceChildren();
    if(!project.assets.length){host.textContent='No imported assets to review.';return;}
    for(const asset of project.assets){
      const card=root.document.createElement('article');card.className='ffv2-rights-card';
      const title=root.document.createElement('strong');title.textContent=asset.label||asset.id;
      const current=root.document.createElement('small');current.textContent='Current rights: '+(asset.rights?.status||'unknown');
      const select=root.document.createElement('select');select.setAttribute('aria-label','Rights decision for '+(asset.label||asset.id));
      const decisions=[['needs_review','Needs review'],['approved','Approved — permission/basis documented'],['approved_with_limits','Approved with limits'],['permission_required','Permission required / restricted'],['rejected','Rejected']];
      for(const [value,label] of decisions){const option=root.document.createElement('option');option.value=value;option.textContent=label;select.append(option);}
      const prior=project.rights_review.asset_reviews.find(item=>item.asset_id===asset.id);
      select.value=prior?.decision||'needs_review';
      const basis=root.document.createElement('textarea');basis.rows=2;basis.placeholder='Rights basis / permission evidence (required for approval)';
      basis.value=prior?.basis||asset.rights?.review_basis||'';
      const intended=root.document.createElement('input');intended.placeholder='Intended use';intended.value=prior?.intended_use||asset.rights?.intended_use||'';
      const permission=root.document.createElement('input');permission.placeholder='Permission reference or licence URL';permission.value=prior?.permission_reference||asset.rights?.permission_reference||asset.rights?.license_url||'';
      const attribution=root.document.createElement('input');attribution.placeholder='Attribution text (when required)';attribution.value=prior?.attribution_text||asset.rights?.attribution_text||'';
      const reviewer=root.document.createElement('input');reviewer.placeholder='Reviewer';reviewer.value=prior?.reviewer||asset.rights?.reviewed_by||'Project owner';
      const apply=root.document.createElement('button');apply.type='button';apply.className='button small';apply.textContent='Save rights decision';
      apply.addEventListener('click',()=>{
        try{
          applyAssetRightsDecision(project,asset.id,{
            decision:select.value,basis:basis.value,intended_use:intended.value,
            permission_reference:permission.value,attribution_text:attribution.value,reviewer:reviewer.value
          });
          markDirty();refresh();status('Saved rights decision for '+(asset.label||asset.id)+'.','success');
        }catch(error){status(error.message,'warning');}
      });
      card.append(title,current,select,basis,intended,permission,attribution,reviewer,apply);host.append(card);
    }
  }

  function renderReadiness(project) {
    const host=el('ffv2ReadinessReport');if(!host)return;
    const report=readinessReport(project);
    host.replaceChildren();
    const statusText=root.document.createElement('strong');statusText.textContent='Production readiness: '+report.status.replaceAll('_',' ');
    statusText.className=report.blockers.length?'is-blocked':report.warnings.length?'has-warnings':'is-approved';
    host.append(statusText);
    for(const [heading,items] of [['Blockers',report.blockers],['Warnings',report.warnings]]){
      const section=root.document.createElement('div');section.className='ffv2-readiness-section';
      const label=root.document.createElement('strong');label.textContent=heading+' ('+items.length+')';section.append(label);
      const list=root.document.createElement('ul');
      for(const item of items){const li=root.document.createElement('li');li.textContent=item;list.append(li);}
      if(!items.length){const li=root.document.createElement('li');li.textContent='None';list.append(li);}
      section.append(list);host.append(section);
    }
    const notice=root.document.createElement('small');notice.textContent=report.reference_video_notice;host.append(notice);
    const finalize=el('ffv2FinaliseRightsReview');if(finalize)finalize.disabled=report.blockers.length>0;
  }

  function syncForm(project) {
    ensureDirectorData(project);
    const brief=project.creative_brief;
    const values={
      ffv2BriefTopic:brief.topic,ffv2BriefNiche:brief.niche,ffv2BriefAudience:brief.audience,
      ffv2BriefPlatform:brief.platform,ffv2BriefDuration:brief.target_duration_seconds,
      ffv2BriefTone:brief.tone,ffv2BriefVisualDirection:brief.visual_direction,
      ffv2BriefDesiredStyle:brief.desired_style,ffv2BriefScript:brief.narration_script,
      ffv2BriefQuestions:(brief.research_questions||[]).join('\n'),
      ffv2BriefAmbiguities:(brief.ambiguities_to_resolve||[]).join('\n'),
      ffv2BriefRestrictions:(brief.restrictions||[]).join('\n')
    };
    for(const [id,value] of Object.entries(values))if(el(id))el(id).value=String(value??'');
    const profile=project.visual_style_profile||defaultStyleProfile(brief.niche);
    el('ffv2StyleNiche').value=profile.niche;
    el('ffv2StyleLanguage').value=profile.visual_language;
    el('ffv2StyleMedia').value=csv(profile.preferred_media);
    el('ffv2StylePacing').value=profile.pacing;
    el('ffv2StyleCamera').value=profile.camera_language;
    el('ffv2StyleSound').value=profile.sound_language;
    el('ffv2StyleAvoid').value=(profile.avoid||[]).join('\n');
    renderSources(project);renderReferenceVideos(project);renderClaims(project);renderShotPlan(project);renderRightsAssets(project);renderReadiness(project);
    el('ffv2DirectorSummary').textContent=
      project.research.sources.length+' sources · '+project.research.reference_videos.length+' video references · '+
      project.research.claims.length+' claims · '+(project.shot_plan?.beats?.length||0)+' planned shots';
  }

  function refresh() {
    const project=currentProject();if(!project)return;
    const changed=ensureDirectorData(project);
    if(changed)markDirty();
    syncForm(project);
  }

  function saveBrief() {
    const project=currentProject();if(!project)return;
    try{
      updateBrief(project,{
        topic:el('ffv2BriefTopic').value.trim()||'Untitled video project',
        niche:el('ffv2BriefNiche').value,
        audience:el('ffv2BriefAudience').value,
        platform:el('ffv2BriefPlatform').value,
        target_duration_seconds:el('ffv2BriefDuration').value,
        tone:el('ffv2BriefTone').value,
        visual_direction:el('ffv2BriefVisualDirection').value,
        desired_style:el('ffv2BriefDesiredStyle').value,
        narration_script:el('ffv2BriefScript').value,
        research_questions:el('ffv2BriefQuestions').value,
        ambiguities_to_resolve:el('ffv2BriefAmbiguities').value,
        restrictions:el('ffv2BriefRestrictions').value
      });
      markDirty();status('Production brief saved to the V2 project.','success');refresh();
    }catch(error){status(error.message,'warning');}
  }

  function addSourceFromForm() {
    const project=currentProject();if(!project)return;
    try{
      addResearchSource(project,{
        url:el('ffv2ResearchUrl').value,title:el('ffv2ResearchTitle').value,
        publisher:el('ffv2ResearchPublisher').value,source_type:el('ffv2ResearchType').value,
        access_status:el('ffv2ResearchAccess').value,confidence:el('ffv2ResearchConfidence').value,
        notes:el('ffv2ResearchNotes').value
      });
      ['ffv2ResearchUrl','ffv2ResearchTitle','ffv2ResearchPublisher','ffv2ResearchNotes','ffv2ResearchPublished'].forEach(id=>el(id).value='');
      markDirty();refresh();status('Research source recorded. No page scraping or access bypass was performed.','success');
    }catch(error){status(error.message,'warning');}
  }

  function addReferenceFromForm() {
    const project=currentProject();if(!project)return;
    try{
      addReferenceVideo(project,{
        url:el('ffv2ReferenceUrl').value,title:el('ffv2ReferenceTitle').value,
        creator:el('ffv2ReferenceCreator').value,platform:el('ffv2ReferencePlatform').value,
        access_status:el('ffv2ReferenceAccess').value,notes:el('ffv2ReferenceNotes').value,
        published_at:el('ffv2ReferencePublished').value ? new Date(el('ffv2ReferencePublished').value+'T00:00:00Z').toISOString() : undefined,
        observed_format:el('ffv2ReferenceObservations').value.split(/\n/).filter(Boolean)
      });
      ['ffv2ReferenceUrl','ffv2ReferenceTitle','ffv2ReferenceCreator','ffv2ReferencePublished','ffv2ReferenceNotes','ffv2ReferenceObservations'].forEach(id=>el(id).value='');
      markDirty();refresh();status('Reference recorded for style analysis only; reuse rights are not implied.','success');
    }catch(error){status(error.message,'warning');}
  }

  function addClaimFromForm() {
    const project=currentProject();if(!project)return;
    try{
      addResearchClaim(project,{
        text:el('ffv2ClaimText').value,classification:el('ffv2ClaimClass').value,
        verification_status:el('ffv2ClaimStatus').value,confidence:el('ffv2ClaimConfidence').value,
        source_ids:el('ffv2ClaimSources').value,
        uncertainty_notes:el('ffv2ClaimUncertainty').value,
        evidence_required:el('ffv2ClaimEvidenceRequired').checked
      });
      ['ffv2ClaimText','ffv2ClaimSources','ffv2ClaimUncertainty'].forEach(id=>el(id).value='');
      markDirty();refresh();status('Claim added. Verification status is retained exactly as entered.','success');
    }catch(error){status(error.message,'warning');}
  }

  function saveStyleFromForm() {
    const project=currentProject();if(!project)return;
    try{
      const niche=el('ffv2StyleNiche').value;
      const profile={
        id:project.visual_style_profile?.id||makeId('style'),
        niche,label:niche==='custom'?'Custom profile':(PROFILES[niche]?.label||niche),
        visual_language:el('ffv2StyleLanguage').value,
        preferred_media:el('ffv2StyleMedia').value.split(',').map(value=>value.trim()).filter(Boolean),
        pacing:el('ffv2StylePacing').value,
        camera_language:el('ffv2StyleCamera').value,
        sound_language:el('ffv2StyleSound').value,
        avoid:el('ffv2StyleAvoid').value.split(/\n/).map(value=>value.trim()).filter(Boolean)
      };
      applyStyleProfile(project,profile);
      markDirty();refresh();status('Editable visual style profile saved.','success');
    }catch(error){status(error.message,'warning');}
  }

  function loadProfilePreset() {
    const project=currentProject();if(!project)return;
    const niche=el('ffv2StyleNiche').value;
    const profile=defaultStyleProfile(niche);
    profile.id=project.visual_style_profile?.id||profile.id;
    applyStyleProfile(project,profile);
    markDirty();refresh();status('Niche profile loaded. You can now edit its guidance.','success');
  }

  function generatePlan() {
    const project=currentProject();if(!project)return;
    try{
      saveBrief();
      const plan=buildShotPlan(project);
      markDirty();refresh();
      status('Created '+plan.beats.length+' timed visual beats. This is a rule-assisted draft; review before rendering.','success');
    }catch(error){status(error.message,'warning');}
  }

  function finaliseReview() {
    const project=currentProject();if(!project)return;
    const report=finaliseRightsReview(project);
    markDirty();refresh();
    if(report.blockers.length)status('Review remains blocked by '+report.blockers.length+' item(s).','warning');
    else status('Review recorded as '+report.status+'.','success');
  }

  function markDirty() { studio()?.markDirty?.(); }
  function bind() {
    el('ffv2BriefSave').addEventListener('click',saveBrief);
    el('ffv2ResearchAddSource').addEventListener('click',addSourceFromForm);
    el('ffv2ReferenceAdd').addEventListener('click',addReferenceFromForm);
    el('ffv2ClaimAdd').addEventListener('click',addClaimFromForm);
    el('ffv2StyleLoadPreset').addEventListener('click',loadProfilePreset);
    el('ffv2StyleSave').addEventListener('click',saveStyleFromForm);
    el('ffv2GenerateShotPlan').addEventListener('click',generatePlan);
    el('ffv2FinaliseRightsReview').addEventListener('click',finaliseReview);
    el('ffv2DirectorRefresh').addEventListener('click',refresh);
    el('ffv2BriefNiche').addEventListener('change',()=>{
      el('ffv2StyleNiche').value=el('ffv2BriefNiche').value;
    });
  }

  const api={
    MEDIA_TYPES,VISUAL_ROLES,PROFILES,clone,defaultStyleProfile,ensureDirectorData,
    updateBrief,applyStyleProfile,addResearchSource,addReferenceVideo,addResearchClaim,
    splitNarration,buildShotPlan,readinessReport,applyAssetRightsDecision,finaliseRightsReview,projectSummary,refresh
  };
  root.FFV2Director=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root.document)document.addEventListener('ffv2:ready',()=>{bind();refresh();});
})(typeof globalThis!=='undefined'?globalThis:this);
