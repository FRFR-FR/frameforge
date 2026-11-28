/* FrameForge V2 — local Three.js scene runtime.
 * Expects the pinned local vendor bundle (THREE r164.1); never loads from a CDN.
 */
(function (root) {
  'use strict';
  const VERSION = '0.164.1';
  const cache = new Map();
  const instanceCache = new Map();
  let renderer = null;
  let renderCanvas = null;
  let rendererSize = '';
  let lastBackend = 'unavailable';

  function requireThree() {
    if (!root.THREE || root.THREE.REVISION !== VERSION.split('.')[1] || !root.THREE.GLTFLoader) {
      throw new Error('The locally bundled Three.js r164.1 runtime is unavailable. Check vendor/three/0.164.1.');
    }
    return root.THREE;
  }

  function basename(value) {
    try { return decodeURIComponent(String(value).split(/[?#]/)[0].split('/').pop()).toLowerCase(); }
    catch (_) { return String(value).split('/').pop().toLowerCase(); }
  }

  async function loadModel(asset, allAssets, resolveDependency) {
    const THREE = requireThree();
    if (cache.has(asset.id)) return cache.get(asset.id);
    const promise = (async () => {
      if (!asset || !asset.blob) throw new Error('The GLB/glTF asset is missing from local browser storage.');
      const manager = new THREE.LoadingManager();
      const dependencyUrls = new Map();
      const managerResolver = manager.setURLModifier ? manager.setURLModifier : manager.setURLModifier;
      if (managerResolver) {
        manager.setURLModifier(url => {
          if (/^(data:|blob:|https?:)/i.test(url)) return url;
          const name = basename(url);
          const match = (allAssets || []).find(item => basename(item.file_name || item.label || '') === name);
          if (!match || !match.blob) throw new Error('Missing glTF dependency "' + name + '". Import the matching .bin or texture file.');
          let local = dependencyUrls.get(match.id);
          if (!local) {
            local = resolveDependency ? resolveDependency(match) : URL.createObjectURL(match.blob);
            dependencyUrls.set(match.id, local);
          }
          return local;
        });
      }
      const loader = new THREE.GLTFLoader(manager);
      const extension = String(asset.file_name || '').toLowerCase().split('.').pop();
      const data = extension === 'gltf' ? await asset.blob.text() : await asset.blob.arrayBuffer();
      const gltf = await new Promise((resolve, reject) => loader.parse(data, '', resolve, reject));
      const bounds = new THREE.Box3().setFromObject(gltf.scene);
      const size = bounds.getSize(new THREE.Vector3());
      const animations = (gltf.animations || []).map(item => ({
        name: item.name || 'Animation ' + ((gltf.animations || []).indexOf(item) + 1),
        duration_seconds: item.duration,
        track_count: item.tracks.length
      }));
      return { gltf, bounds, size:size.toArray(), animations, dependencyUrls };
    })();
    cache.set(asset.id, promise);
    try { return await promise; }
    catch (error) { cache.delete(asset.id); throw error; }
  }

  async function inspectModelFile(file, extension, allAssets, resolveDependency) {
    const asset = { id:'inspect-' + file.name, file_name:file.name, label:file.name, blob:file };
    const loaded = await loadModel(asset, allAssets || [], resolveDependency);
    return {
      codec: extension === 'glb' ? 'glTF Binary 2.0 · Three.js r164.1' : 'glTF JSON 2.0 · Three.js r164.1',
      decode_status:'model-decoded',
      model_count: loaded.gltf.scene.children.length,
      mesh_count: countMeshes(loaded.gltf.scene),
      animation_clips: loaded.animations,
      bounds: loaded.bounds.isEmpty() ? null : { min:loaded.bounds.min.toArray(), max:loaded.bounds.max.toArray() },
      dimensions: loaded.size
    };
  }

  function countMeshes(rootObject) {
    let count=0;
    rootObject.traverse(object=>{if(object.isMesh)count++;});
    return count;
  }

  function ensureRenderer(width,height,renderSettings) {
    const THREE=requireThree();
    const size=width+'x'+height;
    if (!renderer) {
      renderCanvas=document.createElement('canvas');
      renderCanvas.width=width;renderCanvas.height=height;
      renderer=new THREE.WebGLRenderer({
        canvas:renderCanvas,alpha:true,antialias:true,preserveDrawingBuffer:true,
        powerPreference:'default'
      });
      renderer.setPixelRatio(1);
      if ('outputColorSpace' in renderer) renderer.outputColorSpace=THREE.SRGBColorSpace;
      renderer.shadowMap.enabled=Boolean(renderSettings?.shadows);
      renderer.shadowMap.type=THREE.PCFSoftShadowMap;
      lastBackend='three-webgl';
    }
    if(rendererSize!==size){
      renderCanvas.width=width;renderCanvas.height=height;
      renderer.setSize(width,height,false);
      rendererSize=size;
    }
    renderer.toneMapping = renderSettings?.tone_mapping === 'none'
      ? THREE.NoToneMapping
      : renderSettings?.tone_mapping === 'linear'
        ? THREE.LinearToneMapping
        : THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure=Math.max(0,Number(renderSettings?.exposure)||1);
    renderer.shadowMap.enabled=Boolean(renderSettings?.shadows);
    return {THREE,renderer,canvas:renderCanvas};
  }

  function makeCamera(THREE,settings,width,height) {
    const c=settings?.camera||{};
    const aspect=width/height;
    let camera;
    if(c.projection==='orthographic'){
      const halfHeight=Math.max(0.01,Number(c.orthographic_height)||8)/2;
      camera=new THREE.OrthographicCamera(-halfHeight*aspect,halfHeight*aspect,halfHeight,-halfHeight,Number(c.near)||0.1,Number(c.far)||1000);
    } else {
      camera=new THREE.PerspectiveCamera(Math.max(10,Math.min(120,Number(c.fov)||45)),aspect,Number(c.near)||0.1,Number(c.far)||1000);
    }
    camera.position.fromArray(c.position||[6,4,7]);
    camera.up.fromArray(c.up||[0,1,0]);
    camera.lookAt(...(c.target||[0,0,0]));
    camera.updateProjectionMatrix();
    return camera;
  }

  function addLights(THREE,scene,settings) {
    for(const data of settings?.lights||[]){
      const color=data.color||'#ffffff', intensity=Math.max(0,Number(data.intensity)||0);
      let light;
      if(data.type==='ambient') light=new THREE.AmbientLight(color,intensity);
      else if(data.type==='point') {
        light=new THREE.PointLight(color,intensity,Number(data.distance)||0,2);
        light.position.fromArray(data.position||[0,2,2]);
      } else if(data.type==='spot') {
        light=new THREE.SpotLight(color,intensity,Number(data.distance)||0,Number(data.angle)||Math.PI/4,Number(data.penumbra)||0.2,2);
        light.position.fromArray(data.position||[0,3,2]);
        light.target.position.fromArray(data.target||[0,0,0]);
        scene.add(light.target);
      } else {
        light=new THREE.DirectionalLight(color,intensity);
        light.position.fromArray(data.direction||[-0.55,0.78,0.48]).multiplyScalar(8);
      }
      light.castShadow=Boolean(data.cast_shadow);
      scene.add(light);
    }
  }

  function setInstanceTransform(THREE,instance,clip,frame,fps) {
    const transform=root.FFV2Core?.evaluate3DClipState ? root.FFV2Core.evaluate3DClipState(clip,frame) : (clip.transform3d||{position:[0,0,0],rotation:[0,0,0],scale:[1,1,1]});
    instance.group.position.fromArray(transform.position||[0,0,0]);
    const rotation=(transform.rotation||[0,0,0]).map(n=>Number(n)*Math.PI/180);
    instance.group.rotation.set(rotation[0],rotation[1],rotation[2],'XYZ');
    instance.group.scale.fromArray(transform.scale||[1,1,1]);
    const animation=clip.animation||{};
    if(instance.mixer){
      if(animation.enabled===false || !instance.action) instance.mixer.stopAllAction();
      else {
        instance.mixer.stopAllAction();
        const clipName=animation.clip_name || instance.loaded.animations[0]?.name;
        const clipData=instance.loaded.gltf.animations.find(item=>item.name===clipName) || instance.loaded.gltf.animations[0];
        if(clipData){
          if(!instance.action || instance.action.getClip()!==clipData){
            instance.action=instance.mixer.clipAction(clipData);
            instance.action.setLoop(animation.loop===false?THREE.LoopOnce:THREE.LoopRepeat,animation.loop===false?1:Infinity);
            instance.action.clampWhenFinished=animation.loop===false;
          }
          instance.action.play();
          const elapsed=Math.max(0,frame-(Number(animation.start_frame)||clip.start_frame))/fps*Math.max(0,Number(animation.time_scale)||1);
          instance.mixer.setTime(elapsed);
        }
      }
    }
    instance.group.updateMatrixWorld(true);
  }

  function applyConstraints(THREE,instances,models) {
    const byClip=new Map(instances.map(item=>[item.clip.id,item]));
    for(const instance of instances){
      for(const constraint of instance.clip.constraints||[]){
        if(constraint.enabled===false) continue;
        if(constraint.type==='look_at'&&Array.isArray(constraint.target)){
          instance.group.lookAt(...constraint.target);
        } else if(constraint.type==='parent'&&byClip.has(constraint.target_clip_id)){
          byClip.get(constraint.target_clip_id).group.add(instance.group);
        } else if(constraint.type==='ground_contact'){
          const bounds=new THREE.Box3().setFromObject(instance.group);
          if(!bounds.isEmpty()){
            const ground=Number(constraint.ground_y)||0;
            const offset=Number(constraint.offset)||0;
            instance.group.position.y+=ground+offset-bounds.min.y;
            instance.group.updateMatrixWorld(true);
          }
        }
      }
    }
    const collisions=[];
    const colliders=instances.filter(item=>(item.clip.constraints||[]).some(c=>c.type==='aabb_collision'&&c.enabled!==false));
    for(let i=0;i<colliders.length;i++) for(let j=i+1;j<colliders.length;j++){
      const a=colliders[i], b=colliders[j];
      const ba=new THREE.Box3().setFromObject(a.group), bb=new THREE.Box3().setFromObject(b.group);
      if(!ba.intersectsBox(bb)) continue;
      collisions.push([a.clip.id,b.clip.id]);
      const mode=(b.clip.constraints||[]).find(c=>c.type==='aabb_collision')?.mode||'warn_only';
      if(mode==='push_up'){
        const overlap=ba.max.y-bb.min.y;
        if(overlap>0){b.group.position.y+=overlap+0.001;b.group.updateMatrixWorld(true);}
      }
    }
    return collisions;
  }

  async function renderTrack(options) {
    const width=options.width,height=options.height,frame=options.frame,fps=options.fps;
    const settings=options.settings||{};
    const {THREE,renderer,canvas}=ensureRenderer(width,height,settings.render);
    const scene=new THREE.Scene();
    const background=settings.environment?.transparent ? null : settings.environment?.background;
    scene.background=background ? new THREE.Color(background) : null;
    scene.add(new THREE.HemisphereLight(0xc8dcf0,0x27313d,0.18));
    addLights(THREE,scene,settings);
    const camera=makeCamera(THREE,settings,width,height);
    const instances=[];
    for(const item of options.models||[]){
      const loaded=await loadModel(item.asset,options.allAssets,options.resolveDependency);
      let instance=instanceCache.get(item.clip.id);
      if(!instance){
        const model=THREE.SkeletonUtils?.clone ? THREE.SkeletonUtils.clone(loaded.gltf.scene) : loaded.gltf.scene.clone(true);
        const group=new THREE.Group();
        group.name=item.asset.label||item.asset.file_name||'glTF model';
        group.add(model);
        const mixer=loaded.animations.length?new THREE.AnimationMixer(model):null;
        instance={group,model,loaded,mixer,action:null,clip:item.clip};
        instanceCache.set(item.clip.id,instance);
      } else {
        instance.clip=item.clip;
      }
      setInstanceTransform(THREE,instance,item.clip,frame,fps);
      instances.push(instance);
    }
    const byId=new Map(instances.map(item=>[item.clip.id,item]));
    for(const instance of instances){
      const parent=(instance.clip.constraints||[]).find(c=>c.type==='parent'&&c.enabled!==false);
      if(parent&&byId.has(parent.target_clip_id)) byId.get(parent.target_clip_id).group.add(instance.group);
      else scene.add(instance.group);
    }
    const collisions=applyConstraints(THREE,instances,options.models);
    renderer.render(scene,camera);
    return {canvas,drawn:instances.length,collisions,animationCount:instances.filter(item=>item.mixer&&item.clip.animation?.enabled!==false).length,backend:lastBackend};
  }

  function capabilities() {
    try {
      const THREE=requireThree();
      const canvas=document.createElement('canvas');
      const gl=canvas.getContext('webgl2')||canvas.getContext('webgl');
      if(!gl) return {available:false,reason:'WebGL is unavailable on this device.'};
      return {available:true,threeRevision:THREE.REVISION,webgl:gl.getParameter(gl.VERSION),maxTextureSize:gl.getParameter(gl.MAX_TEXTURE_SIZE)};
    } catch(error) { return {available:false,reason:error.message}; }
  }

  function purge(assetId) { cache.delete(assetId); }
  function purgeClip(clipId) { instanceCache.delete(clipId); }
  root.FFV2ThreeStudio={VERSION,loadModel,inspectModelFile,renderTrack,capabilities,purge,purgeClip};
})(typeof window!=='undefined'?window:globalThis);
