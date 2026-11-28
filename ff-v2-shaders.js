/* FrameForge V2 shader pipeline — optional WebGL 1 post-processing with explicit Canvas 2D fallback.
 * Built-in shaders are local, deterministic and preserve sampled alpha. No CDN or GPU dependency.
 */
(function (root) {
  'use strict';
  const VERTEX = [
    'attribute vec2 a_position;',
    'varying vec2 v_uv;',
    'void main(){',
    '  v_uv = (a_position + 1.0) * 0.5;',
    '  gl_Position = vec4(a_position, 0.0, 1.0);',
    '}'
  ].join('\n');

  const BUILTIN = [
    'precision highp float;',
    'varying vec2 v_uv;',
    'uniform sampler2D u_image;',
    'uniform vec2 u_resolution;',
    'uniform float u_time;',
    'uniform float u_intensity;',
    'uniform float u_seed;',
    'uniform float u_p0;',
    'uniform float u_p1;',
    'uniform float u_p2;',
    'uniform int u_kind;',
    'float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)) + u_seed) * 43758.5453); }',
    'void main(){',
    '  vec2 uv = v_uv;',
    '  float t = u_time;',
    '  vec4 base = texture2D(u_image, uv);',
    '  vec4 outColor = base;',
    '  if(u_kind == 0){',
    '    vec3 c = (base.rgb - 0.5) * u_p1 + 0.5 + u_p0;',
    '    outColor = vec4(clamp(c,0.0,1.0), base.a);',
    '  } else if(u_kind == 1){',
    '    float l = dot(base.rgb, vec3(0.2126,0.7152,0.0722));',
    '    outColor = vec4(mix(vec3(l),base.rgb,u_p0),base.a);',
    '  } else if(u_kind == 2){',
    '    float d = distance(uv,vec2(0.5));',
    '    float v = smoothstep(u_p0,0.78,d) * u_p1;',
    '    outColor = vec4(base.rgb * (1.0 - v),base.a);',
    '  } else if(u_kind == 3){',
    '    vec2 px = 1.0 / max(u_resolution,vec2(1.0));',
    '    vec4 sum = base * 0.25;',
    '    sum += texture2D(u_image,uv+vec2(px.x,0.0))*0.125;',
    '    sum += texture2D(u_image,uv-vec2(px.x,0.0))*0.125;',
    '    sum += texture2D(u_image,uv+vec2(0.0,px.y))*0.125;',
    '    sum += texture2D(u_image,uv-vec2(0.0,px.y))*0.125;',
    '    sum += texture2D(u_image,uv+px)*0.125;',
    '    sum += texture2D(u_image,uv-px)*0.125;',
    '    outColor = vec4(sum.rgb,base.a);',
    '  } else if(u_kind == 4){',
    '    vec2 px = 1.0 / max(u_resolution,vec2(1.0));',
    '    vec3 glow = vec3(0.0);',
    '    for(int x=-2;x<=2;x++){ for(int y=-2;y<=2;y++){',
    '      vec4 s = texture2D(u_image,uv+vec2(float(x),float(y))*px*u_p0);',
    '      glow += max(s.rgb-vec3(0.55),vec3(0.0))*0.04;',
    '    }}',
    '    outColor = vec4(clamp(base.rgb+glow*u_p1,0.0,1.0),base.a);',
    '  } else if(u_kind == 5){',
    '    vec2 delta = uv-vec2(0.5);',
    '    float ang = atan(delta.y,delta.x);',
    '    float rays = pow(max(0.0,cos(ang*u_p1 + t*0.15)),18.0);',
    '    float falloff = 1.0-smoothstep(0.08,0.85,length(delta));',
    '    outColor = vec4(clamp(base.rgb+vec3(1.0,0.82,0.56)*rays*falloff*u_p0,0.0,1.0),base.a);',
    '  } else if(u_kind == 6){',
    '    float offset = u_p0 / max(u_resolution.x,1.0);',
    '    float r = texture2D(u_image,uv+vec2(offset,0.0)).r;',
    '    float g = base.g;',
    '    float b = texture2D(u_image,uv-vec2(offset,0.0)).b;',
    '    outColor = vec4(r,g,b,base.a);',
    '  } else if(u_kind == 7){',
    '    float band = floor(uv.y * max(8.0,u_p1));',
    '    float shift = (hash(vec2(band,floor(t*24.0)))-0.5)*u_p0/max(u_resolution.x,1.0);',
    '    vec4 s = texture2D(u_image,clamp(uv+vec2(shift,0.0),0.0,1.0));',
    '    outColor = vec4(s.rgb,base.a);',
    '  } else if(u_kind == 8){',
    '    vec2 center = uv-vec2(0.5);',
    '    float radius = length(center);',
    '    vec2 direction = normalize(center+vec2(0.0001));',
    '    float wave = sin(radius*u_p1*40.0-t*3.0)*u_p0*0.004;',
    '    vec2 warped = clamp(uv+direction*wave,0.0,1.0);',
    '    vec4 s = texture2D(u_image,warped);',
    '    outColor = vec4(s.rgb,base.a);',
    '  } else if(u_kind == 9){',
    '    vec2 offset = vec2(sin(t*15.0+u_seed),cos(t*12.0+u_seed))*u_p0/u_resolution;',
    '    vec4 s = texture2D(u_image,clamp(uv+offset,0.0,1.0));',
    '    outColor = vec4(s.rgb,base.a);',
    '  } else if(u_kind == 10){',
    '    vec2 px = vec2(u_p0/max(u_resolution.x,1.0),0.0);',
    '    vec4 a = texture2D(u_image,clamp(uv-px,0.0,1.0));',
    '    vec4 b = texture2D(u_image,clamp(uv+px,0.0,1.0));',
    '    outColor = vec4((base.rgb+a.rgb+b.rgb)/3.0,base.a);',
    '  }',
    '  gl_FragColor = outColor;',
    '}'
  ].join('\n').replace('    if(u_pass == 6){}','');

  const KIND = {
    'brightness-contrast':0, saturation:1, vignette:2, blur:3, glow:4,
    'light-rays':5, 'chromatic-aberration':6, glitch:7, ripple:8, shake:9, 'motion-blur':10
  };
  let state = null;

  function createShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const message = gl.getShaderInfoLog(shader) || 'Shader compilation failed.';
      gl.deleteShader(shader);
      throw new Error(message);
    }
    return shader;
  }

  function createProgram(gl, fragment) {
    const vertex = createShader(gl, gl.VERTEX_SHADER, VERTEX);
    const frag = createShader(gl, gl.FRAGMENT_SHADER, fragment);
    const program = gl.createProgram();
    gl.attachShader(program, vertex);
    gl.attachShader(program, frag);
    gl.linkProgram(program);
    gl.deleteShader(vertex);
    gl.deleteShader(frag);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const message = gl.getProgramInfoLog(program) || 'Shader program link failed.';
      gl.deleteProgram(program);
      throw new Error(message);
    }
    return program;
  }

  function getState(width, height) {
    if (state && state.width === width && state.height === height) return state;
    if (state) {
      try { state.gl.getExtension('WEBGL_lose_context')?.loseContext(); } catch (_) {}
    }
    const canvas = document.createElement('canvas');
    canvas.width = width; canvas.height = height;
    const gl = canvas.getContext('webgl', { alpha:true, antialias:false, premultipliedAlpha:true, preserveDrawingBuffer:true }) ||
      canvas.getContext('experimental-webgl', { alpha:true, antialias:false, premultipliedAlpha:true, preserveDrawingBuffer:true });
    if (!gl) throw new Error('WebGL is unavailable on this device.');
    const program = createProgram(gl, BUILTIN);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
    const textures = [gl.createTexture(), gl.createTexture()];
    const framebuffers = [gl.createFramebuffer(), gl.createFramebuffer()];
    textures.forEach((texture, index) => {
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,width,height,0,gl.RGBA,gl.UNSIGNED_BYTE,null);
      gl.bindFramebuffer(gl.FRAMEBUFFER,framebuffers[index]);
      gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,texture,0);
    });
    const uniforms = {};
    ['u_image','u_resolution','u_time','u_intensity','u_seed','u_p0','u_p1','u_p2','u_kind'].forEach(name => {
      uniforms[name] = gl.getUniformLocation(program,name);
    });
    state = { canvas,gl,width,height,program,buffer,textures,framebuffers,uniforms,customPrograms:new Map() };
    return state;
  }

  function drawProgram(ctx, program, texture, values, targetFramebuffer) {
    const gl = ctx.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER,targetFramebuffer);
    gl.viewport(0,0,ctx.width,ctx.height);
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER,ctx.buffer);
    const position = gl.getAttribLocation(program,'a_position');
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D,texture);
    gl.uniform1i(gl.getUniformLocation(program,'u_image'),0);
    gl.uniform2f(gl.getUniformLocation(program,'u_resolution'),ctx.width,ctx.height);
    gl.uniform1f(gl.getUniformLocation(program,'u_time'),values.time);
    gl.uniform1f(gl.getUniformLocation(program,'u_intensity'),values.intensity);
    gl.uniform1f(gl.getUniformLocation(program,'u_seed'),values.seed);
    gl.uniform1f(gl.getUniformLocation(program,'u_p0'),values.p0);
    gl.uniform1f(gl.getUniformLocation(program,'u_p1'),values.p1);
    gl.uniform1f(gl.getUniformLocation(program,'u_p2'),values.p2);
    gl.uniform1i(gl.getUniformLocation(program,'u_kind'),values.kind);
    gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
  }

  function normalize(pass) {
    const p = pass.parameters || {};
    const type = pass.type;
    const defaults = {
      'brightness-contrast':[Number(p.brightness)||0,Number(p.contrast)||1,0],
      saturation:[Number(p.saturation)||1,0,0],
      vignette:[Number(p.radius)||0.72,Number(p.strength)||0.35,0],
      blur:[Math.max(0,Number(p.radius)||2),0,0],
      glow:[Math.max(0,Number(p.radius)||12),Math.max(0,Number(p.strength)||0.45),0],
      'light-rays':[Math.max(0,Number(p.strength)||0.3),Math.max(8,Number(p.rays)||14),Number(p.angle)||0],
      'chromatic-aberration':[Math.max(0,Number(p.amount)||2),0,0],
      glitch:[Math.max(0,Number(p.amount)||0.35),Math.max(8,Number(p.bands)||24),0],
      ripple:[Math.max(0,Number(p.amount)||0.25),Math.max(1,Number(p.frequency)||8),0],
      shake:[Math.max(0,Number(p.amount)||5),0,0],
      'motion-blur':[Math.max(0,Number(p.amount)||4),0,0]
    };
    return defaults[type] || [0,0,0];
  }

  function apply(canvas, passes, frame, mode) {
    const active = (passes || []).filter(pass => pass && pass.enabled !== false);
    if (!active.length || mode === 'canvas2d') return { used:false, backend:'canvas2d', reason:'No active WebGL passes or Canvas 2D selected.' };
    try {
      const ctx = getState(canvas.width,canvas.height);
      const gl = ctx.gl;
      const glCanvas = ctx.canvas;
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,1);
      gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,1);
      gl.bindTexture(gl.TEXTURE_2D,ctx.textures[0]);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,canvas);
      let current=0;
      gl.disable(gl.BLEND);
      const warnings=[];
      for (const pass of active) {
        const params=pass.parameters||{};
        let program=ctx.program;
        let vals={kind:KIND[pass.type],time:frame/30,intensity:Number(params.intensity??1),seed:Number(params.seed)||0,p0:0,p1:0,p2:0};
        if (pass.type === 'custom') {
          if (!String(params.fragment||'').trim()) { warnings.push('Custom shader pass is empty and was skipped.'); continue; }
          if (!ctx.customPrograms.has(params.fragment)) ctx.customPrograms.set(params.fragment,createProgram(gl,String(params.fragment)));
          program=ctx.customPrograms.get(params.fragment);
          vals={...vals,kind:0};
        } else {
          if (!(pass.type in KIND)) { warnings.push('Unsupported shader pass '+pass.type+' was skipped.'); continue; }
          const values=normalize(pass);
          vals.p0=values[0]; vals.p1=values[1]; vals.p2=values[2];
          if (pass.type==='brightness-contrast') { vals.p0*=vals.intensity; vals.p1=1+(vals.p1-1)*vals.intensity; }
          if (pass.type==='saturation') vals.p0=1+(vals.p0-1)*vals.intensity;
          if (pass.type==='vignette') vals.p1*=vals.intensity;
          if (pass.type==='glow' || pass.type==='light-rays') vals.p1*=vals.intensity;
          if (pass.type==='glitch' || pass.type==='ripple' || pass.type==='shake' || pass.type==='motion-blur' || pass.type==='chromatic-aberration' || pass.type==='blur') vals.p0*=vals.intensity;
        }
        const next=1-current;
        drawProgram(ctx,program,ctx.textures[current],vals,ctx.framebuffers[next]);
        current=next;
      }
      drawProgram(ctx,ctx.program,ctx.textures[current],{kind:-1,time:frame/30,intensity:1,seed:0,p0:0,p1:0,p2:0},null);
      const out=canvas.getContext('2d');
      out.clearRect(0,0,canvas.width,canvas.height);
      out.drawImage(glCanvas,0,0);
      return { used:true,backend:'webgl',warnings };
    } catch (error) {
      return { used:false,backend:'canvas2d',reason:error.message };
    }
  }

  function capabilities() {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) return { webgl:false, reason:'WebGL is not available in this browser or hardware configuration.' };
      const precision = gl.getShaderPrecisionFormat(gl.FRAGMENT_SHADER,gl.HIGH_FLOAT);
      return { webgl:true, version:gl.getParameter(gl.VERSION), maxTextureSize:gl.getParameter(gl.MAX_TEXTURE_SIZE), highPrecision:Boolean(precision && precision.precision > 0) };
    } catch (error) { return { webgl:false,reason:error.message }; }
  }

  root.FFV2Shaders={apply,capabilities};
  if (typeof module!=='undefined'&&module.exports) module.exports=root.FFV2Shaders;
})(typeof globalThis!=='undefined'?globalThis:this);
