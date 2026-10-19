"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Html, RoundedBox } from "@react-three/drei";
import { useMemo, useRef, type ReactNode } from "react";
import * as THREE from "three";
import { TEAM } from "@/lib/team";

const C = {
  floor: "#e9d6be",
  wallL: "#f2e4d1",
  wallB: "#ead8c2",
  rug: "#c4532d",
  wood: "#c99a6b",
  desk: "#fbf3e8",
  screen: "#2a1f17",
  ink: "#2a1f17",
  paper: "#fffdf8",
  leaf: "#6fa877",
  pot: "#d98b62",
};

// Two rows of three desks; agents sit on the +z side of each desk.
const DESKS: [number, number][] = [
  [-3.1, -1.4], [0, -1.4], [3.1, -1.4],
  [-3.1, 2.0], [0, 2.0], [3.1, 2.0],
];

function Box({ args, color, radius = 0.06, rough = 0.85, ...rest }: {
  args: [number, number, number]; color: string; radius?: number; rough?: number;
} & Omit<React.ComponentProps<typeof RoundedBox>, "args">) {
  return (
    <RoundedBox args={args} radius={radius} smoothness={4} castShadow receiveShadow {...rest}>
      <meshStandardMaterial color={color} roughness={rough} />
    </RoundedBox>
  );
}

function Plant({ position, scale = 1 }: { position: [number, number, number]; scale?: number }) {
  return (
    <group position={position} scale={scale}>
      <Box args={[0.8, 0.7, 0.8]} radius={0.14} color={C.pot} position={[0, 0.35, 0]} />
      {[0, 1, 2, 3, 4, 5].map((k) => (
        <mesh key={k} castShadow position={[Math.cos(k * 1.2) * 0.28, 1.0 + k * 0.16, Math.sin(k * 1.2) * 0.28]} scale={[1, 1.35, 1]}>
          <sphereGeometry args={[0.4, 24, 24]} />
          <meshStandardMaterial color={k % 2 ? C.leaf : "#5f9868"} roughness={0.9} />
        </mesh>
      ))}
    </group>
  );
}

function Room() {
  const notes = ["#f6c453", "#ff9f80", "#9ad0c2", "#b7a4f2", "#86b6f6", "#f6c453", "#ff9f80", "#9ad0c2"];
  const books = ["#c4532d", "#3f6b4f", "#e8b84a", "#7fa7d9", "#2a1f17", "#e391ad", "#8fc4b5", "#c99a6b"];
  return (
    <group>
      <Box args={[12, 0.5, 9.4]} radius={0.2} color={C.floor} position={[0, -0.25, 0.3]} />
      <Box args={[0.4, 4.4, 9.4]} radius={0.12} color={C.wallL} position={[-6.2, 1.95, 0.3]} />
      <Box args={[12.4, 4.4, 0.4]} radius={0.12} color={C.wallB} position={[0, 1.95, -4.6]} />

      {/* window with frame */}
      <Box args={[3.2, 2, 0.08]} radius={0.06} color="#cfe3ea" rough={0.25} position={[2.6, 2.5, -4.37]} />
      <Box args={[0.08, 2, 0.12]} radius={0.02} color={C.paper} position={[2.6, 2.5, -4.33]} />
      <Box args={[3.2, 0.08, 0.12]} radius={0.02} color={C.paper} position={[2.6, 2.5, -4.33]} />
      <Box args={[3.5, 0.14, 0.4]} radius={0.04} color={C.wood} position={[2.6, 1.45, -4.2]} />
      <Plant position={[1.7, 1.52, -4.2]} scale={0.38} />
      <Plant position={[3.5, 1.52, -4.2]} scale={0.3} />

      {/* whiteboard: the project plan as sticky notes */}
      <Box args={[3, 1.7, 0.08]} radius={0.05} color="#fbfaf6" rough={0.6} position={[-2.2, 2.5, -4.36]} />
      {notes.map((c, i) => (
        <Box key={i} args={[0.42, 0.42, 0.03]} radius={0.02} color={c}
          position={[-3.25 + (i % 4) * 0.7, 2.85 - Math.floor(i / 4) * 0.65, -4.3]} rotation={[0, 0, i % 2 ? 0.08 : -0.06]} />
      ))}

      {/* shelf with books on the left wall */}
      <Box args={[0.45, 0.12, 3]} radius={0.03} color={C.wood} position={[-5.8, 2.8, -1.4]} />
      {books.map((c, i) => {
        const h = 0.5 + ((i * 37) % 5) * 0.06;
        return <Box key={i} args={[0.34, h, 0.2]} radius={0.03} color={c} position={[-5.78, 2.86 + h / 2, -2.6 + i * 0.32]} />;
      })}
      {/* framed poster */}
      <Box args={[0.06, 1.2, 1.6]} radius={0.03} color={C.ink} position={[-5.97, 2.4, 2.2]} />
      <Box args={[0.04, 1.0, 1.4]} radius={0.02} color="#e8b84a" position={[-5.93, 2.4, 2.2]} />

      {/* coffee counter in the back corner */}
      <Box args={[1.6, 1, 0.9]} radius={0.08} color={C.wood} position={[-4.9, 0.5, -3.7]} />
      <Box args={[0.55, 0.65, 0.45]} radius={0.08} color={C.ink} position={[-5.2, 1.33, -3.75]} />
      <mesh position={[-4.5, 1.1, -3.6]} castShadow>
        <cylinderGeometry args={[0.1, 0.1, 0.2, 20]} />
        <meshStandardMaterial color={C.paper} />
      </mesh>

      {/* rug and floor plants */}
      <mesh position={[0, 0.02, 0.3]} receiveShadow>
        <cylinderGeometry args={[2.5, 2.5, 0.04, 64]} />
        <meshStandardMaterial color={C.rug} roughness={1} />
      </mesh>
      <Plant position={[-5.2, 0, 4.1]} />
      <Plant position={[5.3, 0, -3.8]} scale={1.1} />
    </group>
  );
}

function Desk({ x, z, color }: { x: number; z: number; color: string }) {
  return (
    <group position={[x, 0, z]}>
      <Box args={[2.2, 0.18, 1.2]} color={C.desk} position={[0, 0.85, 0]} />
      {[[-0.95, -0.45], [0.95, -0.45], [-0.95, 0.45], [0.95, 0.45]].map(([lx, lz], i) => (
        <Box key={i} args={[0.1, 0.78, 0.1]} radius={0.03} color={C.wood} position={[lx, 0.4, lz]} />
      ))}
      <Box args={[1.1, 0.72, 0.08]} radius={0.04} color={C.screen} rough={0.4} position={[0, 1.38, -0.35]} />
      <mesh position={[0, 1.38, -0.305]}>
        <planeGeometry args={[0.96, 0.58]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
      {/* "content" lines on the screen */}
      {[0.14, 0.02, -0.1].map((y, i) => (
        <mesh key={i} position={[-0.12 + i * 0.04, 1.38 + y, -0.3]}>
          <planeGeometry args={[0.6 - i * 0.12, 0.05]} />
          <meshBasicMaterial color="#fffaf2" transparent opacity={0.85} toneMapped={false} />
        </mesh>
      ))}
      <Box args={[0.09, 0.32, 0.09]} radius={0.03} color={C.screen} position={[0, 1.05, -0.37]} />
      <mesh position={[0.75, 1.04, 0.15]} castShadow>
        <cylinderGeometry args={[0.1, 0.1, 0.2, 20]} />
        <meshStandardMaterial color={color} roughness={0.7} />
      </mesh>
      <Box args={[0.4, 0.02, 0.5]} radius={0.01} color={C.paper} position={[-0.6, 0.95, 0.15]} rotation={[0, 0.2, 0]} />
      <Box args={[0.7, 0.14, 0.7]} radius={0.07} color={color} position={[0, 0.55, 0.85]} />
      <Box args={[0.7, 0.62, 0.12]} radius={0.06} color={color} position={[0, 0.88, 1.18]} />
    </group>
  );
}

function Prop({ i }: { i: number }) {
  const ink = <meshStandardMaterial color={C.ink} roughness={0.6} />;
  switch (i) {
    case 0: // magnifying glass
      return (
        <group position={[0.42, 0.62, 0.18]}>
          <mesh><torusGeometry args={[0.13, 0.03, 12, 28]} />{ink}</mesh>
          <mesh position={[0, -0.2, 0]}><cylinderGeometry args={[0.025, 0.025, 0.22, 10]} />{ink}</mesh>
        </group>
      );
    case 1: // clipboard
      return (
        <group position={[0.42, 0.6, 0.16]}>
          <Box args={[0.28, 0.36, 0.03]} radius={0.02} color={C.wood} />
          <Box args={[0.22, 0.26, 0.01]} radius={0.005} color={C.paper} position={[0, -0.02, 0.02]} />
        </group>
      );
    case 2: // beret
      return (
        <mesh position={[0, 1.08, -0.04]} scale={[1, 0.35, 1]} castShadow>
          <sphereGeometry args={[0.3, 24, 14]} />{ink}
        </mesh>
      );
    case 3: // pencil
      return (
        <mesh position={[0.42, 0.62, 0.16]} rotation={[0, 0, 0.5]}>
          <cylinderGeometry args={[0.03, 0.03, 0.42, 10]} />
          <meshStandardMaterial color="#e8b84a" />
        </mesh>
      );
    case 4: // headphones
      return (
        <mesh position={[0, 0.88, 0]}>
          <torusGeometry args={[0.36, 0.045, 12, 32, Math.PI]} />{ink}
        </mesh>
      );
    default: // glasses
      return (
        <group position={[0, 0.86, 0.33]}>
          <mesh position={[-0.12, 0, 0]}><torusGeometry args={[0.085, 0.02, 8, 20]} />{ink}</mesh>
          <mesh position={[0.12, 0, 0]}><torusGeometry args={[0.085, 0.02, 8, 20]} />{ink}</mesh>
        </group>
      );
  }
}

type AgentState = { mode: "work" | "go" | "back"; timer: number; t: number; from: THREE.Vector3; to: THREE.Vector3 };
const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

function Agents() {
  const homes = useMemo(() => DESKS.map(([x, z]) => new THREE.Vector3(x, 0, z + 0.85)), []);
  const groups = useRef<(THREE.Group | null)[]>([]);
  const bodies = useRef<(THREE.Mesh | null)[]>([]);
  const cards = useRef<(THREE.Group | null)[]>([]);
  const feet = useRef<(THREE.Mesh | null)[][]>(TEAM.map(() => []));
  const states = useRef<AgentState[]>(
    homes.map((h, i) => ({ mode: "work", timer: 1.5 + i * 1.6, t: 0, from: h.clone(), to: h.clone() })),
  );
  // Label text is written straight to the DOM; re-rendering <Html> every frame makes React unmount roots mid-render.
  const labels = useRef<(HTMLSpanElement | null)[]>([]);
  const setLabel = (i: number, text: string) => { const el = labels.current[i]; if (el) el.textContent = `· ${text}`; };

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.05);
    const time = state.clock.elapsedTime;

    states.current.forEach((s, i) => {
      const g = groups.current[i];
      const body = bodies.current[i];
      if (!g || !body) return;
      s.timer -= dt;

      if (s.mode === "work") {
        body.scale.y = 1 + Math.sin(time * 2.2 + i) * 0.03;
        g.rotation.y = THREE.MathUtils.lerp(g.rotation.y, Math.PI, 0.08);
        if (s.timer <= 0) {
          // walk the current draft over to the next agent in the pipeline
          s.mode = "go"; s.t = 0;
          s.from.copy(g.position);
          s.to.copy(homes[(i + 1) % homes.length]).add(new THREE.Vector3(0.85, 0, 0.15));
          if (cards.current[i]) cards.current[i]!.visible = true;
          setLabel(i, "handing over");
        }
        return;
      }

      s.t = Math.min(1, s.t + dt * 0.3);
      const p = new THREE.Vector3().lerpVectors(s.from, s.to, easeInOut(s.t));
      const step = Math.sin(s.t * Math.PI * 14);
      p.y = Math.abs(step) * 0.1;
      g.position.copy(p);
      const dir = s.to.clone().sub(s.from);
      g.rotation.y = Math.atan2(dir.x, dir.z);
      feet.current[i].forEach((f, k) => { if (f) f.position.z = (k ? 1 : -1) * step * 0.12; });

      if (s.t >= 1) {
        if (s.mode === "go") {
          s.mode = "back"; s.t = 0; s.from.copy(g.position); s.to.copy(homes[i]);
          if (cards.current[i]) cards.current[i]!.visible = false;
          setLabel(i, "back to work");
        } else {
          s.mode = "work"; s.timer = 6 + Math.random() * 7;
          setLabel(i, TEAM[i].doing);
        }
      }
    });
  });

  return (
    <>
      {TEAM.map((a, i) => (
        <group key={a.role} ref={(el) => { groups.current[i] = el; }} position={homes[i].toArray()} rotation={[0, Math.PI, 0]} scale={1.45}>
          <mesh ref={(el) => { bodies.current[i] = el; }} position={[0, 0.62, 0]} castShadow>
            <capsuleGeometry args={[0.34, 0.46, 12, 32]} />
            <meshStandardMaterial color={a.color} roughness={0.75} />
          </mesh>
          {[-0.12, 0.12].map((x) => (
            <mesh key={x} position={[x, 0.84, 0.31]}>
              <sphereGeometry args={[0.05, 14, 14]} />
              <meshBasicMaterial color={C.ink} />
            </mesh>
          ))}
          {[-0.2, 0.2].map((x) => (
            <mesh key={`b${x}`} position={[x, 0.72, 0.29]} scale={[1, 0.6, 0.4]}>
              <sphereGeometry args={[0.06, 12, 12]} />
              <meshBasicMaterial color="#f7a58f" transparent opacity={0.7} />
            </mesh>
          ))}
          {[-0.13, 0.13].map((x, k) => (
            <mesh key={`f${x}`} ref={(el) => { feet.current[i][k] = el; }} position={[x, 0.08, 0]} castShadow>
              <sphereGeometry args={[0.1, 14, 14]} />
              <meshStandardMaterial color={a.color} roughness={0.8} />
            </mesh>
          ))}
          <Prop i={i} />
          <group ref={(el) => { cards.current[i] = el; }} position={[0, 0.55, 0.42]} visible={false}>
            <Box args={[0.36, 0.46, 0.03]} radius={0.015} color={C.paper} />
            <Box args={[0.24, 0.04, 0.01]} radius={0.005} color={a.color} position={[0, 0.12, 0.02]} />
          </group>
          <Html position={[0, 1.55, 0]} zIndexRange={[10, 0]}>
            <div className="agent-tag">
              <i style={{ background: a.color }} />
              {a.role} <span ref={(el) => { labels.current[i] = el; }}>· {a.doing}</span>
            </div>
          </Html>
        </group>
      ))}
    </>
  );
}

// Fits the orthographic zoom to the container and adds a gentle pointer parallax.
function Rig({ children }: { children: ReactNode }) {
  const group = useRef<THREE.Group>(null);
  useFrame((state) => {
    // Fit the room (about 16 x 12.5 world units, with a small margin so walls never clip on screen) to the container, nearly edge to edge.
    const zoom = Math.min(state.size.width / 16.2, state.size.height / 12.6);
    if (state.camera.zoom !== zoom) {
      state.camera.zoom = zoom;
      state.camera.updateProjectionMatrix();
    }
    if (!group.current) return;
    const { x, y } = state.pointer;
    const idle = Math.sin(state.clock.elapsedTime * 0.25) * 0.05;
    group.current.rotation.y = THREE.MathUtils.lerp(group.current.rotation.y, x * 0.08 + idle, 0.04);
    group.current.position.y = THREE.MathUtils.lerp(group.current.position.y, y * 0.15, 0.04);
  });
  return <group ref={group}>{children}</group>;
}

export default function Diorama() {
  return (
    <Canvas
      orthographic
      shadows
      dpr={[1, 2]}
      camera={{ position: [14, 12.5, 14], zoom: 60, near: 0.1, far: 100 }}
      onCreated={({ camera }) => camera.lookAt(-0.2, 1.1, -0.2)}
      gl={{ antialias: true, alpha: true }}
    >
      <hemisphereLight args={["#fff7ec", "#d9bfa0", 1.15]} />
      <directionalLight
        position={[8, 15, 10]}
        intensity={2.1}
        color="#fff0da"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-11}
        shadow-camera-right={11}
        shadow-camera-top={11}
        shadow-camera-bottom={-11}
        shadow-bias={-0.0005}
      />
      <Rig>
        <Room />
        {DESKS.map(([x, z], i) => <Desk key={i} x={x} z={z} color={TEAM[i].color} />)}
        <Agents />
      </Rig>
    </Canvas>
  );
}
