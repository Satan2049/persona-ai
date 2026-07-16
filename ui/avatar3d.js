/**
 * 3D GLB avatar — lip sync via Rhubarb mouth shapes A–H / X.
 */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const GENDERS = ["male", "female"];

/**
 * Rhubarb mouth cues → blendshape weights.
 * A/X closed · B slight · C–D open · E/H round-wide · F/G labiodental
 */
const RHUBARB_TO_SHAPES = {
  A: { pp: 0.9 },
  B: { aa: 0.35, ih: 0.15 },
  C: { aa: 0.65, ee: 0.2 },
  D: { aa: 1.0 },
  E: { oh: 0.75, aa: 0.35 },
  F: { ff: 0.85 },
  G: { ou: 0.55, ih: 0.2 },
  H: { aa: 0.55, ee: 0.45 },
  X: {},
};

/** Logical shape → morph target name aliases (RPM / ARKit / VRM leftovers). */
const SHAPE_MORPH_ALIASES = {
  aa: ["viseme_aa", "viseme_aa.001", "mouthOpen", "jawOpen", "aa", "A", "Fcl_MTH_A"],
  ih: ["viseme_I", "viseme_I.001", "ih", "I", "Fcl_MTH_I"],
  ou: ["viseme_U", "viseme_U.001", "ou", "U", "Fcl_MTH_U", "mouthPucker", "mouthFunnel"],
  ee: ["viseme_E", "viseme_E.001", "ee", "E", "Fcl_MTH_E"],
  oh: ["viseme_O", "viseme_O.001", "oh", "O", "Fcl_MTH_O"],
  pp: ["viseme_PP", "viseme_PP.001"],
  ff: ["viseme_FF", "viseme_FF.001"],
};

const MOUTH_PRESETS = Object.keys(SHAPE_MORPH_ALIASES);

class Avatar3D {
  constructor() {
    this.host = null;
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.modelRoot = null;
    this.avatar = null;
    this.gender = "female";
    this.mouthOpen = 0;
    this.targetMouthOpen = 0;
    this.targetViseme = "X";
    this.raf = null;
    this.resizeObs = null;
    this.ready = false;
    this._clock = new THREE.Clock();
    this._loadToken = 0;
    this._mouthMeshes = [];
    this._bones = Object.create(null);
    this._mouthValues = Object.fromEntries(MOUTH_PRESETS.map((k) => [k, 0]));
  }

  mount(host) {
    if (!host) return;
    if (this.host === host && this.renderer) {
      this.onHostMoved();
      return;
    }
    if (this.renderer && this.host && this.host !== host) {
      host.appendChild(this.renderer.domElement);
      this.host = host;
      this.onHostMoved();
      return;
    }

    this.disposeRendererOnly();
    this.host = host;
    host.classList.add("avatar3d-host");

    const canvas = document.createElement("canvas");
    canvas.className = "avatar3d-canvas";
    canvas.setAttribute("aria-hidden", "true");
    host.appendChild(canvas);

    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    if (THREE.ColorManagement) {
      THREE.ColorManagement.enabled = true;
    }
    if (THREE.SRGBColorSpace != null) {
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    }
    if (THREE.ACESFilmicToneMapping != null) {
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.05;
    }

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(28, 1, 0.05, 20);
    this.camera.position.set(0, 1.4, 1.1);
    this.camera.lookAt(0, 1.35, 0);

    this.scene.add(new THREE.HemisphereLight(0xb8c8e0, 0x1a1410, 0.9));
    const key = new THREE.DirectionalLight(0xfff6ee, 1.1);
    key.position.set(0.4, 1.6, 0.8);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0x9bb0d0, 0.32);
    fill.position.set(-0.6, 1.1, 0.4);
    this.scene.add(fill);

    this.resizeObs = new ResizeObserver(() => this._resize());
    this.resizeObs.observe(host);
    this._resize();
    if (this.raf == null) this._tick();
    this.setGender(this.gender, true);
  }

  onHostMoved() {
    if (this.resizeObs && this.host) {
      this.resizeObs.disconnect();
      this.resizeObs.observe(this.host);
    }
    this._resize();
  }

  disposeRendererOnly() {
    if (this.resizeObs) {
      this.resizeObs.disconnect();
      this.resizeObs = null;
    }
    this._disposeModel();
    if (this.renderer) {
      this.renderer.dispose();
      this.renderer.domElement?.remove();
      this.renderer = null;
    }
    this.scene = null;
    this.camera = null;
  }

  unmount() {
    if (this.raf != null) {
      cancelAnimationFrame(this.raf);
      this.raf = null;
    }
    this.disposeRendererOnly();
    if (this.host) {
      this.host.innerHTML = "";
      this.host = null;
    }
    this.ready = false;
  }

  async setGender(gender, force = false) {
    const next = GENDERS.includes(gender) ? gender : "female";
    if (!force && next === this.gender && this.modelRoot) return;
    this.gender = next;
    window.localStorage.setItem("smartAvatarModelGender", next);
    if (!this.scene || !this.renderer) return;

    const token = ++this._loadToken;
    this.ready = false;
    this._disposeModel();

    const url = this._resolveAvatarUrl(next);
    try {
      await this._loadAvatar(url, token);
    } catch (err) {
      if (next === "male") {
        console.warn("[Avatar3D] male GLB missing, trying female", err?.message || err);
        try {
          await this._loadAvatar(this._resolveAvatarUrl("female"), token);
          return;
        } catch (err2) {
          console.error("Avatar load failed", err2);
          this._showLoadError(err2);
          this.ready = false;
          return;
        }
      }
      console.error("Avatar load failed", err);
      this._showLoadError(err);
      this.ready = false;
    }
  }

  /**
   * Desktop install embeds UI in Tauri; large binaries often fail on the asset protocol.
   * Prefer the sidecar HTTP origin when available.
   */
  _resolveAvatarUrl(gender) {
    const rel = `avatars/${gender}/avatar.glb`;
    const api = window.__PERSONA_API_BASE__;
    if (api) {
      return `${String(api).replace(/\/$/, "")}/${rel}`;
    }
    return new URL(`./${rel}`, window.location.href).href;
  }

  _showLoadError(err) {
    if (!this.host) return;
    let el = this.host.querySelector(".avatar3d-error");
    if (!el) {
      el = document.createElement("p");
      el.className = "avatar3d-error muted";
      this.host.appendChild(el);
    }
    el.textContent = `Avatar failed to load: ${err?.message || err}`;
  }

  async _loadAvatar(url, token) {
    const loader = new GLTFLoader();
    // WebView2 / some Chromium builds fail ImageBitmap decode for glTF blob
    // textures (silent null → grey untextured mesh). Prefer TextureLoader.
    loader.register((parser) => {
      const texLoader = new THREE.TextureLoader(parser.options.manager);
      texLoader.setCrossOrigin(parser.options.crossOrigin);
      if (parser.options.requestHeader && texLoader.setRequestHeader) {
        texLoader.setRequestHeader(parser.options.requestHeader);
      }
      parser.textureLoader = texLoader;
      return { name: "PersonaTextureLoader" };
    });
    const gltf = await new Promise((resolve, reject) => {
      loader.load(url, resolve, undefined, reject);
    });
    if (token !== this._loadToken) return;

    const root = gltf.scene;
    if (!root) {
      throw new Error("GLB did not contain a scene");
    }

    root.traverse((obj) => {
      if (obj.isMesh) {
        obj.castShadow = false;
        obj.receiveShadow = false;
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        mats.forEach((m) => {
          if (!m) return;
          if (m.map && THREE.SRGBColorSpace != null && m.map.colorSpace == null) {
            m.map.colorSpace = THREE.SRGBColorSpace;
          }
          m.needsUpdate = true;
        });
      }
    });

    this.avatar = root;
    this.modelRoot = new THREE.Group();
    this.modelRoot.add(root);
    this.scene.add(this.modelRoot);
    this.host?.querySelector(".avatar3d-error")?.remove();

    await new Promise((r) => setTimeout(r, 50));
    if (token !== this._loadToken) return;

    this._cacheBones();
    this._cacheMouthDrivers();
    this._applyIdlePose();
    this._frameOnHead();
    this.ready = true;
    this.resetMouth();
    console.info("[Avatar3D] Loaded GLB", url, {
      morphMeshes: this._mouthMeshes.length,
      bones: Object.keys(this._bones),
    });
  }

  _cacheBones() {
    this._bones = Object.create(null);
    if (!this.avatar) return;
    const wanted = new Set([
      "Head",
      "Neck",
      "Spine2",
      "Spine1",
      "Spine",
      "LeftArm",
      "RightArm",
      "LeftForeArm",
      "RightForeArm",
    ]);
    this.avatar.traverse((obj) => {
      if (obj.name && wanted.has(obj.name) && !this._bones[obj.name]) {
        this._bones[obj.name] = obj;
      }
    });
  }

  _bone(...names) {
    for (const name of names) {
      if (this._bones[name]) return this._bones[name];
    }
    return null;
  }

  /**
   * Default Mixamo/RPM rest is often T/A-pose. Fold arms down for a calm idle.
   */
  _applyIdlePose() {
    const leftUpper = this._bone("LeftArm");
    const rightUpper = this._bone("RightArm");
    const leftLower = this._bone("LeftForeArm");
    const rightLower = this._bone("RightForeArm");

    if (leftUpper) {
      leftUpper.rotation.set(0.1, 0.02, -1.2);
    }
    if (rightUpper) {
      rightUpper.rotation.set(0.1, -0.02, 1.2);
    }
    if (leftLower) {
      leftLower.rotation.set(0.08, -0.4, 0.02);
    }
    if (rightLower) {
      rightLower.rotation.set(0.08, 0.4, -0.02);
    }
  }

  _cacheMouthDrivers() {
    this._mouthMeshes = [];
    if (!this.avatar) return;

    this.avatar.traverse((obj) => {
      if (!obj.isMesh || !obj.morphTargetDictionary || !obj.morphTargetInfluences) return;
      const dict = obj.morphTargetDictionary;
      const map = {};
      for (const [preset, aliases] of Object.entries(SHAPE_MORPH_ALIASES)) {
        for (const alias of aliases) {
          if (dict[alias] != null) {
            map[preset] = dict[alias];
            break;
          }
        }
      }
      if (Object.keys(map).length) {
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        mats.forEach((m) => {
          if (!m) return;
          m.morphTargets = true;
          m.morphNormals = true;
          m.needsUpdate = true;
        });
        this._mouthMeshes.push({ mesh: obj, map });
      }
    });
  }

  _frameOnHead() {
    if (!this.avatar || !this.camera) return;
    const head = this._bone("Head");
    const neck = this._bone("Neck");
    const chest = this._bone("Spine2", "Spine1", "Spine");

    const headPos = new THREE.Vector3(0, 1.45, 0);
    const neckPos = new THREE.Vector3(0, 1.32, 0);
    const chestPos = new THREE.Vector3(0, 1.2, 0);

    if (head) {
      head.getWorldPosition(headPos);
    } else {
      const box = new THREE.Box3().setFromObject(this.avatar);
      headPos.set(0, box.max.y - 0.08, 0);
    }
    if (neck) {
      neck.getWorldPosition(neckPos);
    } else {
      neckPos.copy(headPos).add(new THREE.Vector3(0, -0.12, 0));
    }
    if (chest) {
      chest.getWorldPosition(chestPos);
    } else {
      chestPos.copy(headPos).add(new THREE.Vector3(0, -0.22, 0));
    }

    // Head bone ≈ skull center; hair sits above it — leave crown margin.
    const crownY = headPos.y + 0.22;
    const chinBeltY = neckPos.y - 0.02;
    const shoulderHintY = chestPos.y + 0.06;
    const bottomY = Math.min(chinBeltY, shoulderHintY);
    const topY = crownY;
    // Bias look-at upward so the figure sits lower and the crown clears the frame
    const lookAtY = (topY + bottomY) * 0.5 + 0;
    const halfHeight = Math.max(0.14, (topY - bottomY) * 0.5);

    this.camera.fov = 25;
    this.camera.near = 0.05;
    this.camera.far = 20;
    const vFov = THREE.MathUtils.degToRad(this.camera.fov);
    const distance = (halfHeight * 1) / Math.tan(vFov / 2);

    this.camera.position.set(headPos.x, lookAtY, headPos.z + distance);
    this.camera.lookAt(headPos.x, lookAtY, headPos.z);
    this.camera.updateProjectionMatrix();
  }

  setMouthOpen(amount) {
    this.targetMouthOpen = Math.max(0, Math.min(1, Number(amount) || 0));
  }

  applyViseme(visemeKey, weight = 0.85) {
    const w = Math.max(0.35, Math.min(1, Number(weight) || 0.85));
    let key = String(visemeKey || "X").replace(/^viseme_/i, "").toUpperCase();
    const legacy = { CLOSED: "A", REST: "B", TIGHT: "B", FV: "F", OPEN: "D" };
    if (legacy[key]) key = legacy[key];
    if (!RHUBARB_TO_SHAPES[key]) key = "X";
    this.targetViseme = key;
    const openMap = { A: 0.05, B: 0.35, C: 0.6, D: 1.0, E: 0.7, F: 0.45, G: 0.4, H: 0.65, X: 0 };
    this.setMouthOpen((openMap[key] ?? 0.4) * w);
  }

  resetMouth() {
    this.targetViseme = "X";
    this.setMouthOpen(0);
    this.mouthOpen = 0;
    this._applyMouth(0, "X");
  }

  testMouth(open = 1) {
    this.applyViseme("D", open);
    this.mouthOpen = this.targetMouthOpen;
    this._applyMouth(this.mouthOpen, "D");
    this._applyDirectMorphs(this._mouthValues);
    return {
      ready: this.ready,
      mouthMeshes: this._mouthMeshes.length,
      open: this.mouthOpen,
    };
  }

  _applyMouth(open, visemeKey) {
    if (!this.avatar) return;
    this._mouthValues = this._computeMouthValues(open, visemeKey);
  }

  _computeMouthValues(open, visemeKey) {
    const recipe = open <= 0.01 ? {} : RHUBARB_TO_SHAPES[visemeKey] || RHUBARB_TO_SHAPES.D;
    const values = Object.fromEntries(MOUTH_PRESETS.map((k) => [k, 0]));
    for (const [name, base] of Object.entries(recipe)) {
      values[name] = Math.min(1, base * Math.max(open, 0.5));
    }
    return values;
  }

  _applyDirectMorphs(values) {
    if (!values) return;
    for (const { mesh, map } of this._mouthMeshes) {
      const influences = mesh.morphTargetInfluences;
      if (!influences) continue;
      for (const name of MOUTH_PRESETS) {
        const idx = map[name];
        if (idx == null) continue;
        influences[idx] = values[name] || 0;
      }
    }
  }

  _disposeModel() {
    this._mouthMeshes = [];
    this._bones = Object.create(null);
    if (this.modelRoot) {
      this.scene?.remove(this.modelRoot);
      this.modelRoot.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
          mats.forEach((m) => {
            if (m?.map) m.map.dispose();
            m?.dispose?.();
          });
        }
      });
    }
    this.modelRoot = null;
    this.avatar = null;
  }

  _resize() {
    if (!this.host || !this.renderer || !this.camera) return;
    const w = Math.max(1, this.host.clientWidth);
    const h = Math.max(1, this.host.clientHeight);
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  _tick() {
    this.raf = requestAnimationFrame(() => this._tick());
    if (!this.renderer || !this.scene || !this.camera) return;
    const t = this._clock.elapsedTime;

    this.mouthOpen += (this.targetMouthOpen - this.mouthOpen) * 0.45;
    this._applyMouth(this.mouthOpen, this.targetViseme);

    if (this.avatar) {
      this._applyIdlePose();
      this._applyDirectMorphs(this._mouthValues);
      if (this.modelRoot) {
        this.modelRoot.rotation.y = Math.sin(t * 0.25) * 0.03;
      }
    }

    this.renderer.render(this.scene, this.camera);
  }
}

const avatar3d = new Avatar3D();
const storedGender = window.localStorage.getItem("smartAvatarModelGender");
if (storedGender === "female" || storedGender === "male") {
  avatar3d.gender = storedGender;
}

window.PersonaAvatar = {
  mount(el) {
    avatar3d.mount(el);
  },
  unmount() {
    avatar3d.unmount();
  },
  setGender(gender) {
    return avatar3d.setGender(gender);
  },
  getGender() {
    return avatar3d.gender;
  },
  applyViseme(key, weight) {
    avatar3d.applyViseme(key, weight);
  },
  resetMouth() {
    avatar3d.resetMouth();
  },
  testMouth(open) {
    return avatar3d.testMouth(open);
  },
  onHostMoved() {
    avatar3d.onHostMoved();
  },
};
