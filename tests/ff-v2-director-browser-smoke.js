#!/usr/bin/env node
/* Chromium smoke test for the V2 research intake, visual director and evidence/rights gate. */
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');

const PORT = 4175;
const BASE_URL = 'http://127.0.0.1:' + PORT;

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function pngChunk(type, data) {
  const typeBuffer = Buffer.from(type);
  const length = Buffer.alloc(4); length.writeUInt32BE(data.length, 0);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 0);
  return Buffer.concat([length, typeBuffer, data, crc]);
}
function makeTestPng() {
  const signature = Buffer.from([137,80,78,71,13,10,26,10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(4,0); ihdr.writeUInt32BE(4,4); ihdr[8]=8; ihdr[9]=6;
  const row = Buffer.from([0, 45,170,230,255, 45,170,230,255, 45,170,230,255, 45,170,230,255]);
  const zlib=require('node:zlib');
  return Buffer.concat([
    signature,pngChunk('IHDR',ihdr),
    pngChunk('IDAT',zlib.deflateSync(Buffer.concat([row,row,row,row]))),
    pngChunk('IEND',Buffer.alloc(0))
  ]);
}
async function waitForServer(server) {
  const started=Date.now();
  while(Date.now()-started<15000){
    if(server.exitCode!==null)throw new Error('Director smoke server exited.');
    try{const response=await fetch(BASE_URL);const ok=response.ok;await response.arrayBuffer();if(ok)return;}catch(_){}
    await new Promise(resolve=>setTimeout(resolve,200));
  }
  throw new Error('Director smoke server did not start.');
}

async function main() {
  const server=spawn('python3',['-m','http.server',String(PORT),'--bind','127.0.0.1'],{stdio:'ignore'});
  let browser;
  try{
    await waitForServer(server);
    browser=await chromium.launch({headless:true,args:['--no-sandbox']});
    const context=await browser.newContext({acceptDownloads:true,viewport:{width:1365,height:1100}});
    const page=await context.newPage();
    const pageErrors=[];
    page.on('pageerror',error=>pageErrors.push(error.message));
    await page.goto(BASE_URL,{waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>document.getElementById('ffv2DirectorStatus')?.textContent.includes('Research and visual director ready'));
    assert.equal(await page.locator('#ffv2ResearchUrl').count(),1);
    assert.equal(await page.locator('#ffv2ShotPlanList').count(),1);

    // Step 31: brief intake persists the topic, script, ambiguities, audience and constraints.
    await page.locator('#ffv2BriefTopic').fill('How a network firewall filters traffic');
    await page.locator('#ffv2BriefNiche').selectOption('cybersecurity');
    await page.locator('#ffv2BriefAudience').fill('Curious non-specialists');
    await page.locator('#ffv2BriefPlatform').selectOption('youtube_shorts');
    await page.locator('#ffv2BriefDuration').fill('8');
    await page.locator('#ffv2BriefTone').fill('Clear, energetic and accurate');
    await page.locator('#ffv2BriefQuestions').fill('What does the firewall inspect?\nWhich statements need a primary source?');
    await page.locator('#ffv2BriefAmbiguities').fill('Clarify the exact firewall type before describing packet inspection.');
    await page.locator('#ffv2BriefRestrictions').fill('No unrelated stock footage.\nNo unlicensed third-party media.');
    await page.locator('#ffv2BriefScript').fill('An official document describes the firewall rule.\n\nThe system checks the packet against those rules.\n\nSuspicious traffic is blocked before it reaches the protected network.');
    await page.locator('#ffv2BriefSave').click();
    await page.waitForFunction(()=>window.FFV2Studio.getProject().creative_brief.topic==='How a network firewall filters traffic');
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().creative_brief.ambiguities_to_resolve.length),1);

    // Step 32: public sources and creator/video references are recorded with separate purposes.
    await page.locator('#ffv2ResearchUrl').fill('https://example.org/firewall-report');
    await page.locator('#ffv2ResearchTitle').fill('Firewall technical report');
    await page.locator('#ffv2ResearchPublisher').fill('Example Institute');
    await page.locator('#ffv2ResearchType').selectOption('primary');
    await page.locator('#ffv2ResearchAccess').selectOption('public');
    await page.locator('#ffv2ResearchConfidence').selectOption('high');
    await page.locator('#ffv2ResearchPublished').fill('2026-10-01');
    await page.locator('#ffv2ResearchNotes').fill('Primary technical document used to verify the terminology.');
    await page.locator('#ffv2ResearchAddSource').click();
    await page.waitForFunction(()=>window.FFV2Studio.getProject().research.sources.length===1);
    const sourceId=await page.evaluate(()=>window.FFV2Studio.getProject().research.sources[0].id);

    await page.locator('#ffv2ReferenceUrl').fill('https://www.youtube.com/watch?v=public-reference');
    await page.locator('#ffv2ReferenceTitle').fill('Technical explainer format reference');
    await page.locator('#ffv2ReferenceCreator').fill('Example Channel');
    await page.locator('#ffv2ReferencePlatform').fill('YouTube');
    await page.locator('#ffv2ReferenceAccess').selectOption('public');
    await page.locator('#ffv2ReferencePublished').fill('2026-09-01');
    await page.locator('#ffv2ReferenceObservations').fill('Starts with a concrete question\nUses animated diagrams to explain data flow');
    await page.locator('#ffv2ReferenceAdd').click();
    await page.waitForFunction(()=>window.FFV2Studio.getProject().research.reference_videos.length===1);
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().research.reference_videos[0].reference_only),true);
    assert.ok(await page.locator('#ffv2ReferenceVideoList').innerText().then(text=>text.includes('Technical explainer format reference')));

    // Step 33: load a niche profile, customise it and save it into the project.
    await page.locator('#ffv2StyleNiche').selectOption('cybersecurity');
    await page.locator('#ffv2StyleLoadPreset').click();
    await page.locator('#ffv2StyleLanguage').fill('Detailed network diagrams, realistic interface simulations and labelled threat paths.');
    await page.locator('#ffv2StylePacing').selectOption('moderate');
    await page.locator('#ffv2StyleSave').click();
    await page.waitForFunction(()=>window.FFV2Studio.getProject().visual_style_profile.visual_language.startsWith('Detailed network'));
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().visual_style_profile.niche),'cybersecurity');

    // Step 35: add a sourced and verified factual claim before attaching it to an evidence shot.
    await page.locator('#ffv2ClaimText').fill('The cited technical report documents the firewall rule.');
    await page.locator('#ffv2ClaimClass').selectOption('factual');
    await page.locator('#ffv2ClaimStatus').selectOption('verified');
    await page.locator('#ffv2ClaimConfidence').selectOption('high');
    await page.locator('#ffv2ClaimSources').fill(sourceId);
    await page.locator('#ffv2ClaimEvidenceLocations').fill(sourceId+' | NIST report overview, page reference');
    await page.locator('#ffv2ClaimEvidenceRequired').check();
    await page.locator('#ffv2ClaimAdd').click();
    await page.waitForFunction(()=>window.FFV2Studio.getProject().research.claims.length===1);
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().research.claims[0].evidence_locations[0].locator),'NIST report overview, page reference');
    const claimId=await page.evaluate(()=>window.FFV2Studio.getProject().research.claims[0].id);

    // Step 34: the narration director splits script into timed, editable visual beats.
    await page.locator('#ffv2GenerateShotPlan').click();
    await page.waitForFunction(()=>window.FFV2Studio.getProject().shot_plan?.beats?.length===3);
    assert.equal(await page.locator('.ffv2-shot-card').count(),3);
    const firstShot=page.locator('.ffv2-shot-card').first();
    await firstShot.locator('.ffv2-shot-head select').nth(0).selectOption('factual_evidence');
    await firstShot.locator('.ffv2-shot-head select').nth(1).selectOption('source_document');
    const claimLinkInput=firstShot.locator('label').filter({hasText:'Linked claim IDs'}).locator('input');
    await claimLinkInput.fill(claimId);
    await claimLinkInput.press('Tab');
    await page.waitForFunction(()=>window.FFV2Studio.getProject().shot_plan.beats[0].evidence_claim_ids[0]===window.FFV2Studio.getProject().research.claims[0].id);

    // Import a locally generated test asset, then record a documented rights basis.
    await page.locator('[data-panel="ffv2AssetsPanel"]').click();
    await page.locator('#ffv2FileInput').setInputFiles({name:'director-test.png',mimeType:'image/png',buffer:makeTestPng()});
    await page.waitForFunction(()=>document.querySelectorAll('.ffv2-asset-card').length===1);
    await page.waitForFunction(()=>document.querySelectorAll('.ffv2-rights-card').length===1);
    const assetId=await page.evaluate(()=>window.FFV2Studio.getProject().assets[0].id);
    const assetLinkInput=firstShot.locator('label').filter({hasText:'Linked asset IDs'}).locator('input');
    await assetLinkInput.fill(assetId);
    await assetLinkInput.press('Tab');
    await page.waitForFunction(id=>window.FFV2Studio.getProject().shot_plan.beats[0].asset_ids[0]===id,assetId);
    const rightsCard=page.locator('.ffv2-rights-card').first();
    await rightsCard.locator('select').selectOption('approved');
    await rightsCard.locator('textarea').fill('Original vector asset created by the project owner for this video; no third-party media.');
    await rightsCard.locator('input').nth(0).fill('Use as a supporting network diagram.');
    await rightsCard.locator('input').nth(3).fill('Project owner');
    await rightsCard.locator('button').click();
    await page.waitForFunction(()=>window.FFV2Studio.getProject().assets[0].rights.status==='approved');

    // The factual evidence link and rights approval must clear the pre-production review gate.
    const report=await page.evaluate(()=>window.FFV2Director.readinessReport(window.FFV2Studio.getProject()));
    assert.deepEqual(report.blockers,[],report.blockers.join('\n'));
    await page.locator('#ffv2FinaliseRightsReview').click();
    await page.waitForFunction(()=>window.FFV2Studio.getProject().rights_review.status==='approved');
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().shot_plan.status),'approved');
    assert.deepEqual(await page.evaluate(()=>window.FFV2Core.validateProject(window.FFV2Studio.getProject())),[]);
    assert.deepEqual(pageErrors,[],'Director workspace should not emit browser errors.');

    // Autosave and reload keep the brief, dossier, shot plan and review evidence.
    await page.waitForFunction(()=>document.getElementById('ffv2SaveStatus').textContent.includes('Saved locally'),null,{timeout:12000});
    await page.reload({waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>window.FFV2Studio?.getProject()?.shot_plan?.status==='approved');
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().research.sources.length),1);
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().research.claims[0].evidence_locations.length),1);
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().research.reference_videos.length),1);
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().shot_plan.beats.length),3);
    assert.equal(await page.evaluate(()=>window.FFV2Studio.getProject().rights_review.asset_reviews.length),1);

    console.log('FRAMEFORGE_V2_DIRECTOR_BROWSER_SMOKE_PASS');
    console.log('Validated: brief/ambiguity intake, research source records, reference-only video research, niche profile editing, timed narration shot plan, sourced factual proof, asset rights review and persistence after reload.');
    await context.close();
  } finally {
    if(browser)await browser.close();
    server.kill('SIGTERM');
  }
}
main().catch(error=>{
  console.error('FRAMEFORGE_V2_DIRECTOR_BROWSER_SMOKE_FAIL');
  console.error(error);
  process.exitCode=1;
});
