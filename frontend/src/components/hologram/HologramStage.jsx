import { useEffect, useRef } from "react";
import * as THREE from "three";

const LOW_EFFECTS = true;
const NODE_LIMIT = LOW_EFFECTS ? 6 : 8;
const PARTICLE_COUNT = LOW_EFFECTS ? 48 : 120;
const MAX_PIXEL_RATIO = LOW_EFFECTS ? 1.25 : 2;

function positionToVector(position, index) {
  const jitter = (index % 3 - 1) * 0.35;
  const map = {
    "画面左上": [-1.8, 1.1 + jitter, -0.65],
    "画面上方": [0 + jitter, 1.18, -0.8],
    "画面右上": [1.8, 1.1 + jitter, -0.65],
    "画面左侧": [-1.9, 0.15 + jitter, 0],
    "画面中央": [0 + jitter, 0.32, 0],
    "画面右侧": [1.9, 0.15 + jitter, 0],
    "画面左下": [-1.8, -0.72 + jitter, 0.8],
    "画面下方": [0 + jitter, -0.82, 0.9],
    "画面右下": [1.8, -0.72 + jitter, 0.8],
  };
  return map[position] || map["画面中央"];
}

function makeTextSprite(text, active) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 96;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.font = "600 34px 'Microsoft YaHei', sans-serif";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillStyle = active ? "#fff8ec" : "#d8c2a0";
  context.shadowColor = active ? "#d6a85a" : "#6d5130";
  context.shadowBlur = active ? 18 : 8;
  context.fillText(text || "未知物体", canvas.width / 2, canvas.height / 2);
  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(1.45, 0.54, 1);
  sprite.userData.texture = texture;
  return sprite;
}

function disposeNode(node) {
  node.traverse?.((item) => {
    item.geometry?.dispose?.();
    item.material?.map?.dispose?.();
    item.material?.dispose?.();
    item.userData?.texture?.dispose?.();
  });
}

function createMemoryNode(item, index, active, locked, focused, showLabel) {
  const stableScale = Math.min(1.55, 0.75 + (item.seen_count || 1) * 0.08);
  const confidence = Math.max(0.38, Math.min(1, item.confidence || 0.5));
  const node = new THREE.Group();
  const [x, y, z] = positionToVector(item.position, index);
  node.position.set(x, y, z);
  node.userData.signature = `${item.id}:${item.label_zh}:${item.position}:${item.seen_count}:${item.confidence}:${active}:${locked}:${focused}:${showLabel}`;
  const sphere = new THREE.Mesh(
    new THREE.SphereGeometry((focused ? 0.24 : active ? 0.2 : 0.14) * stableScale, LOW_EFFECTS ? 16 : 24, LOW_EFFECTS ? 16 : 24),
    new THREE.MeshStandardMaterial({
      color: active ? 0xf4efe7 : locked ? 0xffd66d : 0x8aa6b8,
      emissive: active ? 0x5f3e18 : locked ? 0x8a6412 : 0x171a1f,
      metalness: 0.2,
      roughness: 0.25,
      transparent: true,
      opacity: active || locked ? 0.96 : confidence * 0.58,
    }),
  );
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry((locked ? 0.42 : 0.28) * stableScale, locked ? 0.018 : 0.012, 8, LOW_EFFECTS ? 32 : 48),
    new THREE.MeshBasicMaterial({ color: locked ? 0xe2b86b : active ? 0xd6a85a : 0x8aa6b8, transparent: true, opacity: locked ? 0.95 : active ? 0.82 : 0.24 }),
  );
  ring.rotation.x = Math.PI / 2;
  const orbit = new THREE.Mesh(
    new THREE.TorusGeometry((focused ? 0.58 : 0.38) * stableScale, 0.006, 8, LOW_EFFECTS ? 40 : 64),
    new THREE.MeshBasicMaterial({ color: active ? 0xf0cf91 : 0x6f7781, transparent: true, opacity: active ? 0.72 : 0.18 }),
  );
  orbit.rotation.y = Math.PI / 2.5;
  node.add(sphere, ring, orbit);
  if (showLabel) {
    const label = makeTextSprite(item.label_zh, active || locked);
    label.position.y = 0.44 * stableScale;
    node.add(label);
  }
  return node;
}

export default function HologramStage({ memory, touch, apiOnline, selectedId, lockedId, detailId, stageAction, interaction }) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, mount.clientWidth / mount.clientHeight, 0.1, 100);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, MAX_PIXEL_RATIO));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    camera.position.set(0, 1.2, 5);
    const group = new THREE.Group();
    scene.add(group);
    const nodeGroup = new THREE.Group();
    scene.add(nodeGroup);
    const readyRing = new THREE.Mesh(
      new THREE.TorusGeometry(1.55, 0.018, 8, 96),
      new THREE.MeshBasicMaterial({ color: 0xd6a85a, transparent: true, opacity: 0 }),
    );
    readyRing.rotation.x = Math.PI / 2;
    readyRing.position.y = -1.02;
    scene.add(readyRing);
    const crystal = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.72, 2),
      new THREE.MeshStandardMaterial({ color: 0xd6a85a, emissive: 0x2a1b09, metalness: 0.38, roughness: 0.18, transparent: true, opacity: 0.72, wireframe: true }),
    );
    group.add(crystal);
    const coreRing = new THREE.Mesh(
      new THREE.TorusGeometry(1.02, 0.014, 10, LOW_EFFECTS ? 64 : 96),
      new THREE.MeshBasicMaterial({ color: 0xd6a85a, transparent: true, opacity: LOW_EFFECTS ? 0.34 : 0.55 }),
    );
    coreRing.rotation.x = Math.PI / 2;
    group.add(coreRing);
    const tiltedRing = new THREE.Mesh(
      new THREE.TorusGeometry(1.26, 0.008, 8, LOW_EFFECTS ? 64 : 128),
      new THREE.MeshBasicMaterial({ color: 0x8a6b3c, transparent: true, opacity: LOW_EFFECTS ? 0.26 : 0.42 }),
    );
    tiltedRing.rotation.set(Math.PI / 3.2, 0, Math.PI / 5);
    group.add(tiltedRing);
    const particleGeometry = new THREE.BufferGeometry();
    const particlePositions = [];
    for (let index = 0; index < PARTICLE_COUNT; index += 1) {
      const radius = 0.52 + Math.random() * 1.2;
      const angle = Math.random() * Math.PI * 2;
      const height = (Math.random() - 0.5) * 1.4;
      particlePositions.push(Math.cos(angle) * radius, height, Math.sin(angle) * radius);
    }
    particleGeometry.setAttribute("position", new THREE.Float32BufferAttribute(particlePositions, 3));
    const particles = new THREE.Points(
      particleGeometry,
      new THREE.PointsMaterial({ color: 0xe6c17d, size: LOW_EFFECTS ? 0.014 : 0.018, transparent: true, opacity: LOW_EFFECTS ? 0.32 : 0.52 }),
    );
    group.add(particles);
    const chip = new THREE.Mesh(
      new THREE.BoxGeometry(1.7, 0.08, 1.7),
      new THREE.MeshStandardMaterial({ color: 0x18191f, emissive: 0x0a0a0d, metalness: 0.55, roughness: 0.35 }),
    );
    chip.position.y = -1.15;
    group.add(chip);
    const grid = new THREE.GridHelper(7, LOW_EFFECTS ? 12 : 18, 0x6a5840, 0x27282d);
    grid.position.y = -1.25;
    scene.add(grid);
    scene.add(new THREE.AmbientLight(0xf4efe7, 0.42));
    const light = new THREE.PointLight(0xd6a85a, LOW_EFFECTS ? 1.2 : 1.8, 10);
    light.position.set(2, 3, 3);
    scene.add(light);
    sceneRef.current = { group, crystal, nodeGroup, readyRing, nodes: new Map(), renderer, camera, scene };

    let frameId = 0;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      group.rotation.y += LOW_EFFECTS ? 0.004 : 0.008;
      crystal.rotation.x += LOW_EFFECTS ? 0.005 : 0.01;
      tiltedRing.rotation.z += LOW_EFFECTS ? 0.002 : 0.004;
      particles.rotation.y -= LOW_EFFECTS ? 0.0015 : 0.003;
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("resize", onResize);
      sceneRef.current?.nodes?.forEach((node) => disposeNode(node));
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  useEffect(() => {
    const stage = sceneRef.current;
    if (!stage) return;
    const memories = (memory.memories || [])
      .filter((item) => item.label !== "unknown")
      .sort((left, right) => (right.confidence || 0) - (left.confidence || 0))
      .slice(0, NODE_LIMIT);
    const labelIds = new Set([
      selectedId,
      lockedId,
      detailId,
      memory.latest_memory?.id,
      ...memories.slice().sort((left, right) => (right.seen_count || 0) - (left.seen_count || 0)).slice(0, 1).map((item) => item.id),
    ].filter(Boolean).slice(0, 3));
    const visibleIds = new Set(memories.map((item) => item.id));
    stage.nodes.forEach((node, id) => {
      if (!visibleIds.has(id)) {
        stage.nodeGroup.remove(node);
        disposeNode(node);
        stage.nodes.delete(id);
      }
    });
    memories.forEach((item, index) => {
      const active = item.id === selectedId || index === 0;
      const locked = item.id === lockedId;
      const focused = item.id === detailId;
      const showLabel = labelIds.has(item.id);
      const signature = `${item.id}:${item.label_zh}:${item.position}:${item.seen_count}:${item.confidence}:${active}:${locked}:${focused}:${showLabel}`;
      const existing = stage.nodes.get(item.id);
      if (existing?.userData.signature === signature) return;
      if (existing) {
        stage.nodeGroup.remove(existing);
        disposeNode(existing);
      }
      const node = createMemoryNode(item, index, active, locked, focused, showLabel);
      stage.nodes.set(item.id, node);
      stage.nodeGroup.add(node);
    });
  }, [memory.memories, memory.latest_memory, selectedId, lockedId, detailId]);

  useEffect(() => {
    const stage = sceneRef.current;
    if (!stage) return;
    stage.group.rotation.x = ((touch.cursor?.y || 0.5) - 0.5) * 0.8;
    stage.group.rotation.z = ((touch.cursor?.x || 0.5) - 0.5) * -0.8;
    const isClick = touch.state === "CLICK";
    stage.crystal.scale.setScalar(isClick ? 1.35 : memory.memory_count > 0 ? 1.12 : 1);
    stage.crystal.material.emissive.setHex(isClick ? 0x6b4a18 : 0x2a1b09);
    stage.readyRing.material.opacity = interaction?.hand_ready ? 0.72 : 0;
    stage.readyRing.rotation.z += interaction?.hand_ready ? 0.035 : 0.01;
    stage.nodeGroup.children.forEach((node) => {
      node.rotation.y -= 0.01;
    });
  }, [touch, memory.memory_count, interaction]);

  return (
    <section className="hologram-stage">
      <div className="stage-canvas" ref={mountRef} />
      <div className="stage-overlay">
        <p className="eyebrow">Memory Space</p>
        <h2>{memory.latest_memory ? `当前记忆：${memory.latest_memory.label_zh}` : "等待目标进入画面"}</h2>
        <p className="stage-status">手势状态：{interaction?.hand_state || touch.state || "IDLE"}</p>
        <span className={apiOnline ? "ok" : "warn"}>{apiOnline ? "API Linked" : "API Waiting"}</span>
      </div>
      {stageAction && <div className="stage-action">{stageAction === "previous" ? "← 上一条" : "下一条 →"}</div>}
    </section>
  );
}
