(function(){
  "use strict";
  const VOICES = [
    ["eponine","Eponine"],["george","George"],["azelma","Ezelma"],["bill_boerst","Bill Boerst"],
    ["jean","Jean"],["michael","Michael"],["peter_yearsley","Peter Yearsley"],["stuart_bell","Stuart Bell"],["charles","Charles"]
  ];
  const $ = id => document.getElementById(id);
  const state = {
    project:{schema_version:"1.0",project:{id:"gameforge-cutscene-prototype",title:"GAMEFORGE Cutscene Prototype",art_direction:"original stylized cinematic 3D; Blender-generated rigged characters"},
      render:{width:1280,height:720,fps:30,duration_seconds:12,profile:"balanced",samples:16},
      characters:[{id:"hero",name:"Original Hero",voice:"george",palette:{primary:[0.08,0.19,0.27,1],accent:[0.08,0.75,0.72,1]}}],
      dialogue:[{id:"line_001",character_id:"hero",voice:"george",start:1,text:"The signal is coming from beneath the old station."}]},
    playing:false, playStarted:0, raf:0
  };
  const esc = s => String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  function toast(message){$("toast").textContent=message;$("toast").classList.add("show");setTimeout(()=>$("toast").classList.remove("show"),2200);}
  function voiceOptions(current){return VOICES.map(([id,label])=>'<option value="'+id+'" '+(id===current?"selected":"")+'>'+label+'</option>').join("");}
  function safeId(value){return String(value||"character").toLowerCase().replace(/[^a-z0-9_-]+/g,"-").replace(/^-+|-+$/g,"")||"character";}
  function renderCharacters(){
    $("characters").innerHTML=state.project.characters.map((c,i)=>'<div class="character-card" data-index="'+i+'"><input class="char-name" aria-label="Character name" value="'+esc(c.name)+'"><select class="voice" aria-label="Voice">'+voiceOptions(c.voice)+'</select><button class="delete" aria-label="Delete character">×</button></div>').join("");
    $("characters").querySelectorAll(".character-card").forEach(card=>{
      const i=Number(card.dataset.index), c=state.project.characters[i];
      card.querySelector(".char-name").addEventListener("change",e=>{c.name=e.target.value||"Unnamed";c.id=safeId(c.id||c.name);renderDialogue();});
      card.querySelector(".voice").addEventListener("change",e=>{c.voice=e.target.value;state.project.dialogue.filter(d=>d.character_id===c.id).forEach(d=>d.voice=c.voice);renderDialogue();});
      card.querySelector(".delete").addEventListener("click",()=>{if(state.project.characters.length===1){toast("Keep at least one character.");return;}state.project.characters.splice(i,1);state.project.dialogue=state.project.dialogue.filter(d=>d.character_id!==c.id);renderAll();});
    });
  }
  function renderDialogue(){
    const chars=state.project.characters;
    $("dialogueRows").innerHTML=state.project.dialogue.map((d,i)=>{
      const charOptions=chars.map(c=>'<option value="'+esc(c.id)+'" '+(c.id===d.character_id?"selected":"")+'>'+esc(c.name)+'</option>').join("");
      return '<tr data-index="'+i+'"><td class="time"><input class="line-time" type="number" min="0" step="0.05" value="'+Number(d.start||0)+'"></td><td class="char"><select class="line-char">'+charOptions+'</select></td><td class="voice"><select class="line-voice">'+voiceOptions(d.voice)+'</select></td><td><textarea class="line-text" maxlength="2000">'+esc(d.text)+'</textarea></td><td class="action"><button class="delete-line" aria-label="Delete line">×</button></td></tr>';
    }).join("");
    $("dialogueRows").querySelectorAll("tr").forEach(row=>{
      const i=Number(row.dataset.index), d=state.project.dialogue[i];
      row.querySelector(".line-time").addEventListener("change",e=>{d.start=Math.max(0,Number(e.target.value)||0);});
      row.querySelector(".line-char").addEventListener("change",e=>{d.character_id=e.target.value;const c=chars.find(x=>x.id===d.character_id);if(c)d.voice=c.voice;renderDialogue();});
      row.querySelector(".line-voice").addEventListener("change",e=>{d.voice=e.target.value;const c=chars.find(x=>x.id===d.character_id);if(c){c.voice=d.voice;state.project.dialogue.filter(x=>x.character_id===c.id).forEach(x=>x.voice=d.voice);}renderDialogue();renderCharacters();});
      row.querySelector(".line-text").addEventListener("change",e=>{d.text=e.target.value.trim();});
      row.querySelector(".delete-line").addEventListener("click",()=>{state.project.dialogue.splice(i,1);renderDialogue();});
    });
  }
  function readSettings(){
    state.project.project.title=$("projectTitle").value.trim()||"Untitled Cutscene";
    state.project.render.width=Number($("resolution").value)===1080?1920:1280;
    state.project.render.height=Number($("resolution").value)===1080?1080:720;
    state.project.render.fps=Math.min(30,Math.max(1,Number($("fps").value)||30));
    state.project.render.profile=$("profile").value;
    state.project.render.duration_seconds=Math.min(600,Math.max(1,Number($("duration").value)||12));
    $("scrub").max=state.project.render.duration_seconds;
  }
  function validateProject(){
    readSettings();
    const p=state.project, ids=new Set(p.characters.map(c=>c.id));
    if(p.render.width>1920||p.render.height>1080||p.render.fps>30||p.render.duration_seconds>600)throw new Error("Render exceeds GAMEFORGE hard limits.");
    if(!p.characters.length)throw new Error("Add at least one character.");
    for(const d of p.dialogue){if(!ids.has(d.character_id))throw new Error("Dialogue references a missing character.");if(!VOICES.some(v=>v[0]===d.voice))throw new Error("Voice not on the approved list.");if(!d.text.trim())throw new Error("Dialogue text cannot be empty.");if(d.start+d.text.length/12>p.render.duration_seconds+1)throw new Error("A dialogue line may extend beyond the cutscene duration.");}
    return p;
  }
  function renderPreview(t){
    const canvas=$("preview"),ctx=canvas.getContext("2d"),w=canvas.width,h=canvas.height;
    ctx.clearRect(0,0,w,h);
    try{
      if(!window.FF3D)throw new Error("FrameForge 3D renderer missing");
      const F=window.FF3D, scene=new F.Scene({background:"#101b2a",depthMode:"zbuffer"});
      scene.addLight(F.ambientLight(0.42,"#b7c8dd"));
      scene.addLight(F.directionalLight([-0.5,0.9,0.35],0.9,"#e0f1ff"));
      scene.add(F.plane({width:15,depth:15,position:[0,-0.03,0],material:{color:"#263b43"}}));
      const count=state.project.characters.length;
      state.project.characters.forEach((c,i)=>{
        const x=(i-(count-1)/2)*2.15;
        const phase=t*3+i*0.7, bob=Math.sin(phase)*0.05;
        const primary=c.palette?.primary||[0.08,0.19,0.27,1], accent=c.palette?.accent||[0.08,0.75,0.72,1];
        const torso=F.cube({size:1,position:[x,0.96+bob,0],scale:[0.76,0.95,0.42],material:{color:primary}});
        const head=F.sphere({radius:0.31,position:[x,1.72+bob,0],scale:[0.92,1.1,0.9],material:{color:"#bd987d"}});
        const chest=F.cube({size:1,position:[x,1.08+bob,-0.235],scale:[0.36,0.42,0.035],material:{color:accent}});
        const armL=F.cube({size:1,position:[x-0.55,0.98+bob,0],scale:[0.22,0.72,0.24],material:{color:primary}});
        const armR=F.cube({size:1,position:[x+0.55,0.98+bob,0],scale:[0.22,0.72,0.24],material:{color:primary}});
        const legL=F.cube({size:1,position:[x-0.22,0.34,0],scale:[0.27,0.68,0.32],material:{color:primary}});
        const legR=F.cube({size:1,position:[x+0.22,0.34,0],scale:[0.27,0.68,0.32],material:{color:primary}});
        [torso,head,chest,armL,armR,legL,legR].forEach(mesh=>scene.add(mesh));
      });
      const camera=new F.Camera({position:[0,2.6,7.5],target:[0,1,0],projection:"perspective",fov:43});
      F.render(ctx,scene,camera,{width:w,height:h,depthMode:"zbuffer"});
      $("previewStatus").textContent="FrameForge CPU 3D blockout preview";
    }catch(error){
      const g=ctx.createLinearGradient(0,0,w,h);g.addColorStop(0,"#182a3c");g.addColorStop(1,"#090f17");ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
      ctx.fillStyle="#eaf1f8";ctx.font="700 24px system-ui";ctx.fillText("GAMEFORGE CUTSCENE STAGE",34,52);
      ctx.fillStyle="#8ea5b8";ctx.font="14px system-ui";ctx.fillText("FrameForge 3D preview unavailable — manifest authoring still works.",34,80);
      $("previewStatus").textContent="2D fallback preview";
    }
    $("timeLabel").textContent="00:"+Number(t).toFixed(1).padStart(4,"0");
  }
  function renderAll(){renderCharacters();renderDialogue();drawCurrent();}
  function drawCurrent(){renderPreview(Number($("scrub").value)||0);}
  function exportProject(){
    try{
      const p=validateProject();
      const blob=new Blob([JSON.stringify(p,null,2)+"\n"],{type:"application/json"});
      const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="cutscene_project.json";a.click();URL.revokeObjectURL(url);
      toast("Project manifest exported. Render it with the GAMEFORGE pipeline.");
    }catch(e){toast(e.message);}
  }
  function loadProject(file){
    const reader=new FileReader();reader.onload=()=>{try{
      const p=JSON.parse(reader.result);if(p.schema_version!=="1.0"||!Array.isArray(p.characters)||!Array.isArray(p.dialogue))throw new Error("Unsupported project manifest.");
      const allowed=new Set(VOICES.map(v=>v[0]));
      p.characters.forEach(c=>{if(!allowed.has(c.voice))throw new Error("Character voice is not allowed: "+c.voice);});
      p.dialogue.forEach(d=>{if(!allowed.has(d.voice))throw new Error("Dialogue voice is not allowed: "+d.voice);});
      state.project=p;$("projectTitle").value=p.project.title;$("resolution").value=p.render.height>=1080?"1080":"720";$("fps").value=String(Math.min(30,p.render.fps));$("profile").value=p.render.profile;$("duration").value=p.render.duration_seconds;renderAll();readSettings();toast("Cutscene project loaded.");
    }catch(e){toast("Open failed: "+e.message);}};reader.readAsText(file);
  }
  function addCharacter(){
    const n=state.project.characters.length+1,id="character_"+n;
    state.project.characters.push({id,name:"Character "+n,voice:"george",palette:{primary:[0.14,0.25,0.34,1],accent:[0.08,0.75,0.72,1]}});
    renderAll();
  }
  function addDialogue(){
    const c=state.project.characters[0],n=state.project.dialogue.length+1;
    state.project.dialogue.push({id:"line_"+String(n).padStart(3,"0"),character_id:c.id,voice:c.voice,start:Math.max(0,Number($("scrub").value)||0),text:"New dialogue line."});
    renderDialogue();
  }
  function startPreview(){
    state.playing=!state.playing;
    $("playPreview").textContent=state.playing?"Pause preview":"Play preview";
    if(state.playing){state.playStarted=performance.now()-(Number($("scrub").value)||0)*1000;tick();}
    else cancelAnimationFrame(state.raf);
  }
  function tick(){
    if(!state.playing)return;
    let t=((performance.now()-state.playStarted)/1000)%state.project.render.duration_seconds;
    $("scrub").value=t;drawCurrent();state.raf=requestAnimationFrame(tick);
  }
  ["resolution","fps","profile","duration","projectTitle"].forEach(id=>$(id).addEventListener("change",()=>{readSettings();drawCurrent();}));
  $("scrub").addEventListener("input",drawCurrent);
  $("addCharacter").addEventListener("click",addCharacter);
  $("addDialogue").addEventListener("click",addDialogue);
  $("playPreview").addEventListener("click",startPreview);
  $("exportProject").addEventListener("click",exportProject);
  $("importProject").addEventListener("click",()=>$("projectFile").click());
  $("projectFile").addEventListener("change",e=>{if(e.target.files[0])loadProject(e.target.files[0]);e.target.value="";});
  $("newProject").addEventListener("click",()=>{if(!confirm("Start a new cutscene project? Unsaved edits will be lost."))return;state.project={schema_version:"1.0",project:{id:"new-cutscene",title:"Untitled Cutscene",art_direction:"original stylized cinematic 3D"},render:{width:1280,height:720,fps:30,duration_seconds:12,profile:"balanced",samples:16},characters:[{id:"hero",name:"Hero",voice:"george"}],dialogue:[]};$("projectTitle").value=state.project.project.title;$("resolution").value="720";$("fps").value="30";$("profile").value="balanced";$("duration").value="12";renderAll();});
  readSettings();renderAll();
})();