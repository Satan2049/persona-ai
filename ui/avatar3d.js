/**
 * 3D avatar (VRM / GLB) — lip sync via Rhubarb mouth shapes A–H / X.
 * Catalog: ui/avatars/catalog.json (named files, e.g. Kira.vrm, Lucien.vrm).
 */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";

const GENDERS = ["male", "female"];
const STORAGE_GENDER = "smartAvatarModelGender";
const STORAGE_AVATAR_ID = "smartAvatarId";

/**
 * Rhubarb mouth cues → VRM expression / morph weights.
 * A/X closed · B slight · C–D open · E/H round-wide · F/G labiodental
 */
const RHUBARB_TO_SHAPES = {
  A: {},
  B: { aa: 0.35, ih: 0.15 },
  C: { aa: 0.65, ee: 0.2 },
  D: { aa: 1.0 },
  E: { oh: 0.75, aa: 0.35 },
  F: { ou: 0.7, oh: 0.25 },
  G: { ou: 0.55, ih: 0.2 },
  H: { aa: 0.55, ee: 0.45 },
  X: {},
};

const SHAPE_MORPH_ALIASES = {
  aa: ["Fcl_MTH_A", "Fcl_MTH_Large", "viseme_aa", "mouthOpen", "jawOpen", "aa", "A"],
  ih: ["Fcl_MTH_I", "viseme_I", "ih", "I"],
  ou: ["Fcl_MTH_U", "viseme_U", "ou", "U", "mouthPucker", "mouthFunnel"],
  ee: ["Fcl_MTH_E", "viseme_E", "ee", "E"],
  oh: ["Fcl_MTH_O", "viseme_O", "oh", "O"],
  pp: ["viseme_PP", "Fcl_MTH_Close"],
  ff: ["viseme_FF"],
};

const MOUTH_PRESETS = ["aa", "ih", "ou", "ee", "oh", "pp", "ff"];

const FALLBACK_CATALOG = {
  version: 1,
  defaults: { female: "Kira", male: "Lucien" },
  avatars: [
    { id: "Kira", gender: "female", file: "female/Kira.vrm", label: "Kira", format: "vrm" },
    { id: "Lucien", gender: "male", file: "male/Lucien.vrm", label: "Lucien", format: "vrm" },
  ],
};

class Avatar3D {
  constructor() {
    this.host = null;
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.modelRoot = null;
    this.avatar = null;
    this.vrm = null;
    this.gender = "female";
    this.avatarId = null;
    this.catalog = null;
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

  async _ensureCatalog() {
    if (this.catalog) return this.catalog;
    try {
      const url = this._resolveCatalogUrl();
      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) throw new Error(`catalog HTTP ${res.status}`);
      this.catalog = await res.json();
    } catch (err) {
      console.warn("[Avatar3D] catalog load failed, using fallback", err?.message || err);
      this.catalog = FALLBACK_CATALOG;
    }
    return this.catalog;
  }

  _resolveCatalogUrl() {
    const rel = "avatars/catalog.json";
    const api = window.__PERSONA_API_BASE__;
    if (api) {
      return `${String(api).replace(/\/$/, "")}/${rel}`;
    }
    return new URL(`./${rel}`, window.location.href).href;
  }

  _entryById(id) {
    const list = this.catalog?.avatars || [];
    return list.find((a) => a && a.id === id) || null;
  }

  _defaultIdForGender(gender) {
    const g = GENDERS.includes(gender) ? gender : "female";
    return this.catalog?.defaults?.[g] || (g === "male" ? "Lucien" : "Kira");
  }

  async setGender(gender, force = false) {
    const next = GENDERS.includes(gender) ? gender : "female";
    await this._ensureCatalog();
    const id = this._defaultIdForGender(next);
    if (!force && next === this.gender && id === this.avatarId && this.modelRoot) {
      return;
    }
    this.gender = next;
    window.localStorage.setItem(STORAGE_GENDER, next);
    return this.setAvatar(id, { gender: next, force: true });
  }

  async setAvatar(avatarId, options = {}) {
    await this._ensureCatalog();
    const entry = this._entryById(avatarId);
    if (!entry) {
      const fallbackId = this._defaultIdForGender(options.gender || this.gender);
      if (fallbackId !== avatarId) {
        return this.setAvatar(fallbackId, { ...options, force: true });
      }
      throw new Error(`Unknown avatar id: ${avatarId}`);
    }

    const gender = entry.gender || options.gender || this.gender;
    if (!options.force && entry.id === this.avatarId && this.modelRoot) {
      return;
    }

    this.gender = GENDERS.includes(gender) ? gender : this.gender;
    this.avatarId = entry.id;
    window.localStorage.setItem(STORAGE_GENDER, this.gender);
    window.localStorage.setItem(STORAGE_AVATAR_ID, entry.id);

    if (!this.scene || !this.renderer) return;

    const token = ++this._loadToken;
    this.ready = false;
    this._disposeModel();

    const url = this._resolveAvatarFileUrl(entry.file);
    try {
      await this._loadAvatar(url, entry, token);
    } catch (err) {
      console.error("Avatar load failed", err);
      this._showLoadError(err);
      this.ready = false;
    }
  }

  _resolveAvatarFileUrl(relFile) {
    const rel = `avatars/${String(relFile || "").replace(/^\/+/, "")}`;
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

  async _loadAvatar(url, entry, token) {
    const format = String(entry.format || "").toLowerCase() || (url.endsWith(".vrm") ? "vrm" : "glb");
    const loader = new GLTFLoader();
    loader.register((parser) => {
      const texLoader = new THREE.TextureLoader(parser.options.manager);
      texLoader.setCrossOrigin(parser.options.crossOrigin);
      if (parser.options.requestHeader && texLoader.setRequestHeader) {
        texLoader.setRequestHeader(parser.options.requestHeader);
      }
      parser.textureLoader = texLoader;
      if (format === "vrm") {
        return new VRMLoaderPlugin(parser);
      }
      return { name: "PersonaTextureLoader" };
    });

    const gltf = await new Promise((resolve, reject) => {
      loader.load(url, resolve, undefined, reject);
    });
    if (token !== this._loadToken) return;

    let root = gltf.scene;
    let vrm = null;
    if (format === "vrm") {
      vrm = gltf.userData.vrm;
      if (!vrm) {
        throw new Error("VRM plugin did not produce userData.vrm");
      }
      try {
        VRMUtils.combineSkeletons?.(vrm.scene);
      } catch (_e) {
        /* optional */
      }
      // VRM 0.x faces -Z; this spins the scene to +Z. VRM 1.x already faces +Z — no-op.
      try {
        VRMUtils.rotateVRM0?.(vrm);
      } catch (_e) {
        /* ignore */
      }
      root = vrm.scene;
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

    this.vrm = vrm;
    this.avatar = root;
    this.modelRoot = new THREE.Group();
    // Camera sits on +Z looking at the head. After rotateVRM0, models face +Z — do not yaw 180°.
    this.modelRoot.rotation.y = 0;
    this.modelRoot.add(root);
    this.scene.add(this.modelRoot);
    this.host?.querySelector(".avatar3d-error")?.remove();

    await new Promise((r) => setTimeout(r, 50));
    if (token !== this._loadToken) return;

    this._cacheBones();
    this._cacheMouthDrivers();
    this._applyIdlePose();
    if (this.vrm) this.vrm.update(0);
    this._applyIdlePose();
    this._frameOnHead();
    this.ready = true;
    this.resetMouth();
    console.info("[Avatar3D] Loaded", entry.id, url, {
      format,
      expressions: this._expressionNames(),
      mouthMeshes: this._mouthMeshes.length,
    });
  }

  _cacheBones() {
    this._bones = Object.create(null);
    if (this.vrm?.humanoid) {
      const h = this.vrm.humanoid;
      const map = {
        Head: "head",
        Neck: "neck",
        Spine2: "upperChest",
        Spine1: "chest",
        Spine: "spine",
        LeftArm: "leftUpperArm",
        RightArm: "rightUpperArm",
        LeftForeArm: "leftLowerArm",
        RightForeArm: "rightLowerArm",
      };
      for (const [key, human] of Object.entries(map)) {
        const node =
          h.getNormalizedBoneNode?.(human) || h.getBoneNode?.(human) || null;
        if (node) this._bones[key] = node;
      }
      return;
    }
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
      "J_Bip_C_Head",
      "J_Bip_C_Neck",
      "J_Bip_C_UpperChest",
      "J_Bip_C_Chest",
      "J_Bip_L_UpperArm",
      "J_Bip_R_UpperArm",
      "J_Bip_L_LowerArm",
      "J_Bip_R_LowerArm",
    ]);
    this.avatar.traverse((obj) => {
      if (obj.name && wanted.has(obj.name) && !this._bones[obj.name]) {
        this._bones[obj.name] = obj;
      }
    });
    // Aliases for framing helpers
    if (!this._bones.Head && this._bones.J_Bip_C_Head) this._bones.Head = this._bones.J_Bip_C_Head;
    if (!this._bones.Neck && this._bones.J_Bip_C_Neck) this._bones.Neck = this._bones.J_Bip_C_Neck;
    if (!this._bones.Spine2 && this._bones.J_Bip_C_UpperChest) {
      this._bones.Spine2 = this._bones.J_Bip_C_UpperChest;
    }
    if (!this._bones.LeftArm && this._bones.J_Bip_L_UpperArm) {
      this._bones.LeftArm = this._bones.J_Bip_L_UpperArm;
    }
    if (!this._bones.RightArm && this._bones.J_Bip_R_UpperArm) {
      this._bones.RightArm = this._bones.J_Bip_R_UpperArm;
    }
    if (!this._bones.LeftForeArm && this._bones.J_Bip_L_LowerArm) {
      this._bones.LeftForeArm = this._bones.J_Bip_L_LowerArm;
    }
    if (!this._bones.RightForeArm && this._bones.J_Bip_R_LowerArm) {
      this._bones.RightForeArm = this._bones.J_Bip_R_LowerArm;
    }
  }

  _bone(...names) {
    for (const name of names) {
      if (this._bones[name]) return this._bones[name];
    }
    return null;
  }

  /** Fold T/A-pose arms down beside the torso. */
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

  _expressionNames() {
    const mgr = this.vrm?.expressionManager;
    if (!mgr) return [];
    if (mgr.expressionMap) return Object.keys(mgr.expressionMap);
    return (mgr.expressions || []).map((e) => e?.expressionName || e?.name).filter(Boolean);
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
    const chest = this._bone("Spine2", "Spine1", "Spine", "J_Bip_C_Chest");

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

    // Head + shoulders: crown margin, shoulders in frame
    const crownY = headPos.y + 0.2;
    const chinBeltY = neckPos.y - 0.02;
    const shoulderHintY = chestPos.y + 0.04;
    const bottomY = Math.min(chinBeltY, shoulderHintY);
    const topY = crownY;
    const lookAtY = (topY + bottomY) * 0.5;
    const halfHeight = Math.max(0.14, (topY - bottomY) * 0.5);

    this.camera.fov = 26;
    this.camera.near = 0.05;
    this.camera.far = 20;
    const vFov = THREE.MathUtils.degToRad(this.camera.fov);
    const distance = (halfHeight * 1.15) / Math.tan(vFov / 2);

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
    if (this.vrm) this.vrm.update(1 / 60);
    this._applyDirectMorphs(this._mouthValues);
    return {
      ready: this.ready,
      avatarId: this.avatarId,
      expressions: this._expressionNames(),
      mouthMeshes: this._mouthMeshes.length,
      open: this.mouthOpen,
    };
  }

  _applyMouth(open, visemeKey) {
    if (!this.avatar && !this.vrm) return;
    this._mouthValues = this._computeMouthValues(open, visemeKey);
    const mgr = this.vrm?.expressionManager;
    if (mgr) {
      for (const name of ["aa", "ih", "ou", "ee", "oh"]) {
        mgr.setValue(name, this._mouthValues[name] || 0);
      }
    }
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
    if (this.vrm) {
      try {
        VRMUtils.deepDispose?.(this.vrm.scene);
      } catch (_e) {
        /* fallback below */
      }
    }
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
    this.vrm = null;
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
    const delta = this._clock.getDelta();
    const t = this._clock.elapsedTime;

    this.mouthOpen += (this.targetMouthOpen - this.mouthOpen) * 0.45;
    this._applyMouth(this.mouthOpen, this.targetViseme);

    if (this.vrm || this.avatar) {
      if (this.vrm) this.vrm.update(delta);
      this._applyIdlePose();
      this._applyDirectMorphs(this._mouthValues);
      if (this.modelRoot) {
        // Subtle idle yaw only — keep facing the camera (+Z).
        this.modelRoot.rotation.y = Math.sin(t * 0.25) * 0.03;
      }
    }

    this.renderer.render(this.scene, this.camera);
  }
}

const avatar3d = new Avatar3D();
const storedGender = window.localStorage.getItem(STORAGE_GENDER);
if (storedGender === "female" || storedGender === "male") {
  avatar3d.gender = storedGender;
}
const storedAvatarId = window.localStorage.getItem(STORAGE_AVATAR_ID);
if (storedAvatarId) {
  avatar3d.avatarId = storedAvatarId;
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
  setAvatar(id) {
    return avatar3d.setAvatar(id);
  },
  getGender() {
    return avatar3d.gender;
  },
  getAvatarId() {
    return avatar3d.avatarId;
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
