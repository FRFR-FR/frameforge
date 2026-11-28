/* Browser controls for the V2 production workflow module. */
(function (root) {
  'use strict';

  const $ = id => root.document && root.document.getElementById(id);
  const value = id => $(id)?.value || '';
  let selectedResult = null;
  let bound = false;

  function status(message, kind) {
    const node = $('ffv2ProductionStatus');
    const summary = $('ffv2ProductionSummary');
    if (node) {
      node.textContent = message;
      node.dataset.state = kind || 'info';
    }
    if (summary) summary.textContent = kind === 'error' ? 'Action needs attention' : 'Production tools ready';
  }

  function currentProject() {
    return root.FFV2Studio?.getProject?.() || null;
  }

  function studio() {
    return root.FFV2Studio || null;
  }

  function safeLink(value) {
    try {
      const url = new URL(String(value || ''));
      return ['http:','https:'].includes(url.protocol) ? url.href : '';
    } catch (_) { return ''; }
  }

  function populateRecipes() {
    const project = currentProject();
    const beatSelect = $('ffv2RecipeBeat');
    const recipeSelect = $('ffv2RecipeChoice');
    if (!project || !beatSelect || !recipeSelect || !root.FFV2Production) return;
    const previous = beatSelect.value;
    beatSelect.replaceChildren();
    const beats = project.shot_plan?.beats || [];
    if (!beats.length) {
      const option = root.document.createElement('option');
      option.value = '';
      option.textContent = 'Generate a shot plan first';
      beatSelect.append(option);
    } else {
      beats.forEach((beat, index) => {
        const option = root.document.createElement('option');
        option.value = beat.id;
        option.textContent = (index + 1) + '. ' + String(beat.narration || beat.id).slice(0, 72);
        beatSelect.append(option);
      });
      if (beats.some(beat => beat.id === previous)) beatSelect.value = previous;
    }
    const chosen = recipeSelect.value;
    recipeSelect.replaceChildren();
    root.FFV2Production.listRecipes().forEach(recipe => {
      const option = root.document.createElement('option');
      option.value = recipe.id;
      option.textContent = recipe.label;
      recipeSelect.append(option);
    });
    if (root.FFV2Production.RECIPES[chosen]) recipeSelect.value = chosen;
    renderRecipePreview();
  }

  function renderRecipePreview() {
    const node = $('ffv2RecipePreview');
    if (!node || !root.FFV2Production) return;
    const recipe = root.FFV2Production.instantiateShotRecipe(value('ffv2RecipeChoice') || 'explainer', {
      duration_scale: Number(value('ffv2RecipeDuration')) || 1,
      transition_frames: Number(value('ffv2RecipeTransitionFrames')) || 10,
      layout: value('ffv2RecipeLayout')
    });
    node.textContent = recipe.label + ' · ' + recipe.layout + '\n' + recipe.camera + '\n' +
      recipe.action + '\nMotion: ' + recipe.motion + ' · Duration scale: ' + recipe.duration_scale.toFixed(2) +
      ' · Transition: ' + recipe.transition.type + ' (' + recipe.transition.duration_frames + ' frames)';
  }

  function populateAudio() {
    const project = currentProject();
    const select = $('ffv2AudioAsset');
    const catalogue = $('ffv2AudioCatalogue');
    if (!project || !select || !catalogue || !root.FFV2Production) return;
    const records = root.FFV2Production.audioCatalogue(project);
    const previous = select.value;
    select.replaceChildren();
    const placeholder = root.document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = records.length ? 'Select imported audio' : 'No audio assets imported';
    select.append(placeholder);
    records.forEach(item => {
      const option = root.document.createElement('option');
      option.value = item.id;
      option.textContent = item.label + ' · ' + item.status;
      select.append(option);
    });
    if (records.some(item => item.id === previous)) select.value = previous;
    catalogue.replaceChildren();
    if (!records.length) {
      catalogue.textContent = 'No audio assets in this project yet. Import a file with the media picker above.';
      return;
    }
    records.forEach(item => {
      const row = root.document.createElement('div');
      row.className = 'ffv2-audio-row';
      const info = root.document.createElement('div');
      const title = root.document.createElement('strong');
      title.textContent = item.label + ' · ' + item.role;
      const detail = root.document.createElement('small');
      detail.textContent = item.license_name + ' · ' + item.status + (item.attribution_required ? ' · attribution required' : '') + (item.restrictions.length ? ' · ' + item.restrictions.length + ' usage limit(s)' : '');
      info.append(title, detail);
      row.append(info);
      catalogue.append(row);
    });
  }

  function renderProviderResults(resultSets) {
    const node = $('ffv2ProviderResults');
    if (!node) return;
    node.replaceChildren();
    const results = [];
    (resultSets || []).forEach(result => {
      if (result?.results) results.push(...result.results);
      else if (result?.mode === 'manual') {
        const note = root.document.createElement('p');
        note.textContent = result.provider + ' uses a manual browser workflow: ' + result.url;
        node.append(note);
      }
    });
    if (!results.length && !node.childNodes.length) {
      node.textContent = 'No results were returned. Open the provider page or use manual local import.';
      return;
    }
    results.slice(0, 16).forEach(item => {
      const row = root.document.createElement('article');
      row.className = 'ffv2-provider-result';
      const info = root.document.createElement('div');
      const title = root.document.createElement('strong');
      title.textContent = item.title || 'Untitled media';
      const detail = root.document.createElement('small');
      detail.textContent = (item.provider || 'Catalogue') + ' · ' + (item.creator || 'Creator not supplied') +
        ' · ' + (item.license_name || 'Licence not supplied; review required');
      info.append(title, detail);
      const actions = root.document.createElement('div');
      const link = root.document.createElement('a');
      link.href = safeLink(item.landing_url || item.download_url) || '#';
      link.textContent = 'Open source';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      if (link.href === '#') link.removeAttribute('target');
      const choose = root.document.createElement('button');
      choose.type = 'button';
      choose.className = 'button small';
      choose.textContent = 'Select';
      choose.addEventListener('click', () => selectResult(item));
      actions.append(link, choose);
      row.append(info, actions);
      node.append(row);
    });
  }

  function selectResult(item) {
    selectedResult = item;
    $('ffv2ProductionSourceUrl').value = item.landing_url || '';
    $('ffv2ProductionProvider').value = item.provider || '';
    $('ffv2ProductionTitle').value = item.title || '';
    $('ffv2ProductionCreator').value = item.creator || '';
    $('ffv2ProductionLicense').value = item.license_name || '';
    $('ffv2ProductionLicenseUrl').value = item.license_url || '';
    $('ffv2ProductionAttribution').value = item.attribution_text || '';
    status('Selected "' + (item.title || 'media') + '". Download from the source page, then import the local file.', 'success');
  }

  async function search(provider) {
    const query = value('ffv2SourceQuery').trim();
    const mediaType = value('ffv2SourceType') || 'image';
    if (provider === 'openverse' && mediaType === 'video') {
      status('Openverse search supports images and audio here. Use Wikimedia Commons for video search.', 'warning');
      return;
    }
    status('Searching ' + (provider === 'openverse' ? 'Openverse' : 'Wikimedia Commons') + '…');
    try {
      const result = await root.FFV2Production.searchProvider(provider, query, mediaType);
      renderProviderResults([result]);
      status('Loaded ' + result.results.length + ' result(s) from ' + result.provider + '. Check each source page and licence.', 'success');
    } catch (error) {
      status(error.message, 'error');
    }
  }

  function importSelectionOptions() {
    const manual = {
      provider: value('ffv2ProductionProvider'),
      title: value('ffv2ProductionTitle'),
      creator: value('ffv2ProductionCreator'),
      landing_url: value('ffv2ProductionSourceUrl'),
      download_url: value('ffv2ProductionSourceUrl'),
      license_name: value('ffv2ProductionLicense'),
      license_url: value('ffv2ProductionLicenseUrl'),
      attribution_text: value('ffv2ProductionAttribution'),
      restrictions: value('ffv2ProductionRestrictions').split('\n').map(item => item.trim()).filter(Boolean)
    };
    const merged = Object.assign({}, selectedResult || {}, manual);
    return root.FFV2Production.importOptionsForSelection(merged, value('ffv2AudioRole'));
  }

  async function importLocalFile(file) {
    if (!file) return;
    try {
      const imported = await studio().importAsset(file, importSelectionOptions());
      selectedResult = null;
      populateAudio();
      status('Imported and validated ' + imported.file_name + '. Rights status remains pending until reviewed.', 'success');
    } catch (error) {
      status('Import rejected: ' + error.message, 'error');
    } finally {
      $('ffv2ProductionImportFile').value = '';
    }
  }

  function createGraphic() {
    const project = currentProject();
    if (!project) return;
    try {
      const type = value('ffv2GraphicType');
      const startInput = Number(value('ffv2GraphicStart'));
      const durationInput = Number(value('ffv2GraphicDuration'));
      const options = {
        start_frame: Number.isFinite(startInput) && startInput >= 0 ? startInput : studio().getPlayheadFrame(),
        duration_frames: Number.isFinite(durationInput) && durationInput > 0 ? durationInput : 90
      };
      let clip;
      if (type === 'particles') {
        clip = root.FFV2Production.createProceduralParticleClip(project, {
          preset: value('ffv2GraphicParticlePreset'),
          count: Number(value('ffv2GraphicParticleCount')) || 72,
          seed: Number(value('ffv2GraphicParticleSeed')) || 1337
        }, options);
      } else {
        const labels = value('ffv2GraphicLabels').split(/\r?\n/).map(item => item.trim()).filter(Boolean);
        const values = value('ffv2GraphicValues').split(/\r?\n/)
          .map(item => Number(item.trim())).filter(item => Number.isFinite(item) && item >= 0);
        clip = root.FFV2Production.createProceduralGraphicClip(project, {
          type: type,
          title: value('ffv2GraphicTitle'),
          subtitle: value('ffv2GraphicSubtitle'),
          labels: labels,
          values: values
        }, options);
      }
      studio().markDirty();
      studio().refreshTimeline();
      status('Created editable procedural ' + (type === 'particles' ? 'particle' : 'SVG') + ' clip ' + clip.id + '.', 'success');
    } catch (error) {
      status('Graphic creation failed: ' + error.message, 'error');
    }
  }

  async function saveAudioMetadata() {
    const project = currentProject();
    const assetId = value('ffv2AudioAsset');
    if (!project || !assetId) {
      status('Select an imported audio asset first.', 'warning');
      return;
    }
    try {
      const asset = root.FFV2Production.registerAudioMetadata(project, assetId, {
        license_name: value('ffv2AudioLicense'),
        license_url: value('ffv2AudioLicenseUrl'),
        attribution_required: $('ffv2AudioAttributionRequired').checked,
        attribution_text: value('ffv2AudioAttribution'),
        restrictions: value('ffv2AudioRestrictions').split('\n').map(item => item.trim()).filter(Boolean)
      });
      const role = value('ffv2AudioRole');
      asset.tags = (asset.tags || []).filter(tag => !String(tag).startsWith('audio-role:'));
      asset.tags.push('audio-role:' + role);
      await studio().updateAssetRecord(assetId, { rights: asset.rights, tags: asset.tags });
      buildAudioReport();
      populateAudio();
      $('ffv2AudioAsset').value = assetId;
      status('Audio usage metadata saved. The asset remains pending until the rights review is completed.', 'success');
    } catch (error) {
      status('Audio metadata could not be saved: ' + error.message, 'error');
    }
  }

  function loadAudioEditor() {
    const asset = currentProject()?.assets?.find(item => item.id === value('ffv2AudioAsset'));
    if (!asset) return;
    $('ffv2AudioLicense').value = asset.rights?.license_name || '';
    $('ffv2AudioLicenseUrl').value = asset.rights?.license_url || '';
    $('ffv2AudioAttribution').value = asset.rights?.attribution_text || '';
    $('ffv2AudioRestrictions').value = (asset.rights?.restrictions || []).filter(item => !String(item).includes('Pending individual rights review')).join('\n');
    $('ffv2AudioAttributionRequired').checked = asset.rights?.attribution_required !== false;
    const role = (asset.tags || []).find(tag => String(tag).startsWith('audio-role:'))?.slice(11);
    if (['sfx','music','voiceover'].includes(role)) $('ffv2AudioRole').value = role;
  }

  function buildAudioReport() {
    const report = root.FFV2Production.audioPackagingReport(currentProject());
    const node = $('ffv2AudioReport');
    const credits = $('ffv2AudioCredits');
    if (node) node.textContent = report.status.toUpperCase() + ' · ' + report.audio_assets + ' audio asset(s)\n' +
      (report.blockers.length ? report.blockers.join('\n') : 'No audio metadata blockers detected.') +
      '\n' + report.note;
    if (credits) credits.value = report.credits;
    const limits = $('ffv2AudioUsageLimits');
    if (limits) { const newline = String.fromCharCode(10); limits.value = report.usage_limits.map(item => item.label + ':' + newline + item.restrictions.join(newline)).join(newline + newline); }
  }

  function assemble() {
    const project = currentProject();
    if (!project) return;
    try {
      const report = root.FFV2Production.assembleShotPlan(project);
      studio().markDirty();
      studio().refreshTimeline();
      const parts = [
        'Draft status: ' + report.status,
        'Created editable clips: ' + report.created.length,
        'Unfilled beats: ' + report.unfilled.length,
        'Rights blockers: ' + report.rights_blockers.length
      ];
      if (report.unfilled.length) parts.push(report.unfilled.map(item => item.narration + ' — ' + item.reason).join('\n'));
      if (report.rights_blockers.length) parts.push(report.rights_blockers.slice(0, 8).join('\n'));
      $('ffv2AssemblyReport').textContent = parts.join('\n');
      status('Editable draft assembly complete. Review unfilled shots and rights blockers before rendering.', 'success');
    } catch (error) {
      status('Assembly blocked: ' + error.message, 'error');
    }
  }

  function bind() {
    if (bound || !root.FFV2Production || !studio()) return;
    bound = true;
    $('ffv2RecipeBeat').addEventListener('change', renderRecipePreview);
    $('ffv2RecipeChoice').addEventListener('change', renderRecipePreview);
    $('ffv2RecipeDuration').addEventListener('input', renderRecipePreview);
    $('ffv2RecipeTransitionFrames').addEventListener('input', renderRecipePreview);
    $('ffv2RecipeLayout').addEventListener('input', renderRecipePreview);
    $('ffv2ApplyRecipe').addEventListener('click', () => {
      try {
        const beat = root.FFV2Production.applyShotRecipe(currentProject(), value('ffv2RecipeBeat'), value('ffv2RecipeChoice'), {
          duration_scale: Number(value('ffv2RecipeDuration')) || 1,
          transition_frames: Number(value('ffv2RecipeTransitionFrames')) || 10,
          layout: value('ffv2RecipeLayout')
        });
        studio().markDirty();
        populateRecipes();
        $('ffv2RecipeBeat').value = beat.id;
        renderRecipePreview();
        status('Applied "' + beat.shot_recipe.label + '" to the selected narration beat. Timing remains editable.', 'success');
      } catch (error) { status(error.message, 'error'); }
    });
    $('ffv2SearchOpenverse').addEventListener('click', () => search('openverse'));
    $('ffv2SearchCommons').addEventListener('click', () => search('wikimedia_commons'));
    $('ffv2ChooseProductionFile').addEventListener('click', () => $('ffv2ProductionImportFile').click());
    $('ffv2ProductionImportFile').addEventListener('change', event => importLocalFile(event.target.files?.[0]));
    $('ffv2CreateProceduralGraphic').addEventListener('click', createGraphic);
    $('ffv2AudioAsset').addEventListener('change', loadAudioEditor);
    $('ffv2SaveAudioMetadata').addEventListener('click', saveAudioMetadata);
    $('ffv2BuildAudioCredits').addEventListener('click', buildAudioReport);
    $('ffv2AssembleShotPlan').addEventListener('click', assemble);
    const sourceType = $('ffv2SourceType');
    sourceType.addEventListener('change', () => {
      $('ffv2SearchOpenverse').disabled = sourceType.value === 'video';
    });
    populateRecipes();
    populateAudio();
    buildAudioReport();
    status('Production workflows loaded. Select a shot plan, then choose the appropriate workflow.');
    root.document.addEventListener('ffv2:project-updated', () => {
      populateRecipes();
      populateAudio();
      buildAudioReport();
    });
  }

  root.FFV2ProductionUI = { bind: bind, refresh: () => { populateRecipes(); populateAudio(); buildAudioReport(); } };
  if (root.document) root.document.addEventListener('ffv2:ready', bind);
})(typeof globalThis !== 'undefined' ? globalThis : this);
