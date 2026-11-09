import { useEffect, useRef, useState } from "preact/hooks";

type Run = {
  meta: { layout: string; n: number; seed: number; service_mean: number; dt: number };
  geometry: {
    domain: number[][];
    walls: number[][];
    gates: number[][];
    bars: number[][];
    fences: number[][][];
    service: number[][];
    bar_size: number[];
  };
  buyer: number[];
  frames: number[][];
  density: number[];
  evacuated: number[];
  metrics: Record<string, number | boolean>;
};

const W = 80, H = 50, PAD = 2, DH = 0.5, SIGMA = 0.7;
const C = {
  floor: "#eef1f4",
  wall: "#1f2933",
  gate: "#1a9850",
  bar: "#d95f02",
  fence: "#7570b3",
  buyer: "#d7191c",
  walker: "#2c7bb6",
};

function label(name: string) {
  const m = name.match(/^([a-z]+)_n(\d+)_s(\d+)(?:_t([\d.]+))?/);
  if (!m) return name;
  const extra = m[4] && m[4] !== "16.4" ? `, atención ${m[4]} s` : "";
  const fresh = name.includes("(nueva)") ? " (nueva)" : "";
  return `${m[1] === "base" ? "Base" : "PSO"}, ${m[2]} personas, semilla ${m[3]}${extra}${fresh}`;
}

function densityGrid(frame: number[]) {
  const nx = W / DH, ny = H / DH, g = new Float32Array(nx * ny);
  const s2 = 2 * SIGMA * SIGMA, norm = 1 / (Math.PI * s2), r = Math.ceil(3 * SIGMA / DH);
  for (let i = 0; i < frame.length; i += 2) {
    if (frame[i] < 0) continue;
    const x = frame[i] / 10, y = frame[i + 1] / 10, ci = Math.floor(x / DH), cj = Math.floor(y / DH);
    for (let a = Math.max(ci - r, 0); a < Math.min(ci + r + 1, nx); a++) {
      const wx = Math.exp(-(((a + 0.5) * DH - x) ** 2) / s2);
      for (let b = Math.max(cj - r, 0); b < Math.min(cj + r + 1, ny); b++) {
        g[a * ny + b] += norm * wx * Math.exp(-(((b + 0.5) * DH - y) ** 2) / s2);
      }
    }
  }
  return { g, nx, ny };
}

function draw(cv: HTMLCanvasElement, run: Run, k: number, showDensity: boolean, dpr: number) {
  const ctx = cv.getContext("2d");
  if (!ctx) return;
  const s = cv.width / (W + 2 * PAD);
  const X = (x: number) => (x + PAD) * s, Y = (y: number) => cv.height - (y + PAD) * s;
  const geo = run.geometry;
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.fillStyle = C.floor;
  ctx.beginPath();
  geo.domain.forEach(([x, y], i) => i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y)));
  ctx.fill();
  const frame = run.frames[Math.max(0, Math.min(k, run.frames.length - 1))] ?? [];
  if (showDensity) {
    const { g, nx, ny } = densityGrid(frame);
    for (let a = 0; a < nx; a++) {
      for (let b = 0; b < ny; b++) {
        const v = g[a * ny + b];
        if (v < 1) continue;
        const t = Math.min((v - 1) / 3, 1);
        ctx.fillStyle = `rgba(${Math.round(255 * Math.min(1, 2 * t))},${Math.round(200 * (1 - t))},0,${
          0.15 + 0.6 * t
        })`;
        ctx.fillRect(X(a * DH), Y((b + 1) * DH), DH * s + 0.5, DH * s + 0.5);
      }
    }
  }
  const seg = (p: number[], color: string, width: number) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = width * dpr;
    ctx.beginPath();
    ctx.moveTo(X(p[0]), Y(p[1]));
    ctx.lineTo(X(p[2]), Y(p[3]));
    ctx.stroke();
  };
  geo.walls.forEach((w) => seg(w, C.wall, 2));
  geo.gates.forEach((g) => seg(g, C.gate, 5));
  geo.fences.forEach((f) => seg([...f[0], ...f[1]], C.fence, 4));
  ctx.fillStyle = C.bar;
  const [bw, bh] = geo.bar_size;
  geo.bars.forEach(([x, y]) => ctx.fillRect(X(x - bw / 2), Y(y + bh / 2), bw * s, bh * s));
  const r = Math.max(1.5 * dpr, 0.27 * s);
  ctx.lineCap = "round";
  for (let i = 0; i < frame.length; i += 2) {
    if (frame[i] < 0) continue;
    ctx.fillStyle = run.buyer[i / 2] ? C.buyer : C.walker;
    ctx.beginPath();
    ctx.arc(X(frame[i] / 10), Y(frame[i + 1] / 10), r, 0, 2 * Math.PI);
    ctx.fill();
  }
}

function Chart({ runs, k }: { runs: Run[]; k: number }) {
  const n = Math.max(...runs.map((r) => r.evacuated.length));
  const w = 1200, h = 140, x = (i: number) => (i / Math.max(n - 1, 1)) * w;
  const colors = ["#2c7bb6", "#d95f02"];
  return (
    <svg viewBox={`0 0 ${w} ${h + 20}`} class="chart">
      {runs.map((r, j) => (
        <polyline
          key={j}
          fill="none"
          stroke={colors[j]}
          stroke-width="2"
          points={r.evacuated.map((v, i) => `${x(i)},${h - (v / r.meta.n) * h}`).join(" ")}
        />
      ))}
      <line x1={x(k)} x2={x(k)} y1="0" y2={h} stroke="#999" stroke-dasharray="4 3" />
      <text x="4" y={h + 16}>0 s</text>
      <text x={w - 4} y={h + 16} text-anchor="end">{((n - 1) * 0.5).toFixed(0)} s</text>
      <text x="4" y="12">% evacuado</text>
    </svg>
  );
}

function Panel({ run, k, showDensity }: { run: Run | null; k: number; showDensity: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  const ref = useRef<HTMLCanvasElement>(null);
  const [cssWidth, setCssWidth] = useState(0);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const fit = () => setCssWidth(Math.floor(el.clientWidth));
    fit();
    const obs = new ResizeObserver(fit);
    obs.observe(el);
    return () => obs.disconnect();
  }, [run !== null]);
  useEffect(() => {
    const cv = ref.current;
    if (!cv || !run || cssWidth <= 0) return;
    const dpr = Math.min(Math.max(globalThis.devicePixelRatio || 1, 1), 3);
    const width = Math.min(Math.round(cssWidth * dpr), 3000);
    if (cv.width !== width) {
      cv.width = width;
      cv.height = Math.round(width * (H + 2 * PAD) / (W + 2 * PAD));
    }
    try {
      draw(cv, run, k, showDensity, width / cssWidth);
    } catch (err) {
      console.error("No se pudo dibujar el cuadro", err);
    }
  }, [run, k, showDensity, cssWidth]);
  if (!run) return <div class="panel empty">Elige una corrida</div>;
  const kk = Math.max(0, Math.min(k, run.frames.length - 1)), m = run.metrics;
  return (
    <div class="panel">
      <div ref={box}>
        <canvas ref={ref} />
      </div>
      <dl class="stats">
        <div>
          <dt>Adentro</dt>
          <dd>{run.meta.n - run.evacuated[kk]}</dd>
        </div>
        <div>
          <dt>Densidad ahora</dt>
          <dd>{run.density[kk].toFixed(2)} p/m2</dd>
        </div>
        <div>
          <dt>Densidad pico</dt>
          <dd>{Number(m.d_max).toFixed(2)} p/m2</dd>
        </div>
        <div>
          <dt>T95</dt>
          <dd>{Number(m.t95).toFixed(1)} s</dd>
        </div>
        <div>
          <dt>Flujo pico</dt>
          <dd>{Number(m.peak_flow).toFixed(2)} p/(m s)</dd>
        </div>
        <div>
          <dt>Salieron sin comprar</dt>
          <dd>{m.left_unserved}</dd>
        </div>
      </dl>
    </div>
  );
}

export default function Player() {
  const [names, setNames] = useState<string[]>([]);
  const [runs, setRuns] = useState<Record<string, Run>>({});
  const [sel, setSel] = useState<[string, string]>(["", ""]);
  const [k, setK] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(4);
  const [showDensity, setShowDensity] = useState(true);
  const [form, setForm] = useState({ layout: "base", n: 500, seed: 1005, service: 16.4 });
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch("/data/index.json", { cache: "no-store" }).then((r) => r.json()).then((list: string[]) => {
      setNames(list);
      const base = list.find((x) => x.startsWith("base")) ?? list[0] ?? "";
      const pso = list.find((x) => x.startsWith("pso")) ?? "";
      setSel([base, pso]);
    }).catch(() => setStatus("No se pudo leer la lista de corridas guardadas"));
  }, []);

  useEffect(() => {
    sel.filter((s) => s && !runs[s]).forEach((s) =>
      fetch(`/data/${s}.json`, { cache: "no-store" }).then((r) => r.json())
        .then((d: Run) => setRuns((old) => ({ ...old, [s]: d })))
        .catch(() => setStatus(`No se pudo leer la corrida ${s}`))
    );
  }, [sel]);

  const shown = sel.map((s) => runs[s] ?? null);
  const total = Math.max(1, ...shown.filter(Boolean).map((r) => r!.frames.length));

  const kRef = useRef(0);
  kRef.current = k;

  useEffect(() => {
    if (!playing) return;
    let last = performance.now(), acc = 0, id = 0;
    const tick = (now: number) => {
      acc += ((now - last) / 1000) * speed / 0.5;
      last = now;
      const step = Math.floor(acc);
      acc -= step;
      if (step) {
        const next = Math.min(kRef.current + step, total - 1);
        kRef.current = next;
        setK(next);
        if (next >= total - 1) return setPlaying(false);
      }
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [playing, speed, total]);

  function togglePlay() {
    if (!playing && k >= total - 1) setK(0);
    setPlaying(!playing);
  }

  async function newRun() {
    setStatus("Simulando...");
    const q = new URLSearchParams(Object.entries(form).map(([a, b]) => [a, `${b}`]));
    const res = await fetch(`/api/run?${q}`);
    const data = await res.json();
    if (!res.ok) return setStatus(`Error: ${data.error}`);
    const name = `${form.layout}_n${form.n}_s${form.seed}_t${form.service} (nueva)`;
    setRuns((old) => ({ ...old, [name]: data }));
    setNames((old) => [...old, name]);
    setSel(([a]) => [a, name]);
    setK(0);
    setStatus(`Listo: T95 = ${data.metrics.t95} s, densidad pico = ${data.metrics.d_max} p/m2`);
  }

  return (
    <section>
      <div class="controls">
        <button type="button" onClick={togglePlay}>{playing ? "Pausa" : "Reproducir"}</button>
        <button type="button" onClick={() => (setK(0), setPlaying(false))}>Reiniciar</button>
        <label>
          Velocidad
          <select value={speed} onChange={(e) => setSpeed(Number(e.currentTarget.value))}>
            {[1, 2, 4, 8, 16].map((v) => <option key={v} value={v}>{v}x</option>)}
          </select>
        </label>
        <label>
          <input type="checkbox" checked={showDensity} onChange={(e) => setShowDensity(e.currentTarget.checked)} />
          Densidad (rojo intenso = 4 p/m2)
        </label>
        <input
          type="range"
          min="0"
          max={total - 1}
          value={k}
          onInput={(e) => setK(Math.min(Number(e.currentTarget.value), total - 1))}
        />
        <span class="time">t = {(k * 0.5).toFixed(1)} s</span>
      </div>
      <div class="panels">
        {[0, 1].map((j) => (
          <div key={j} class="col">
            <select
              value={sel[j]}
              onChange={(e) => {
                const v = e.currentTarget.value;
                setSel((old) => (j ? [old[0], v] : [v, old[1]]));
              }}
            >
              <option value="">(ninguna)</option>
              {names.map((nm) => <option key={nm} value={nm}>{label(nm)}</option>)}
            </select>
            <Panel run={shown[j]} k={k} showDensity={showDensity} />
          </div>
        ))}
      </div>
      {shown.some(Boolean) && <Chart runs={shown.filter(Boolean) as Run[]} k={k} />}
      <form
        class="newrun"
        onSubmit={(e) => {
          e.preventDefault();
          newRun();
        }}
      >
        <strong>Nueva corrida</strong>
        <label>
          Montaje
          <select value={form.layout} onChange={(e) => setForm({ ...form, layout: e.currentTarget.value })}>
            <option value="base">Base</option>
            <option value="pso">PSO</option>
          </select>
        </label>
        <label>
          Aforo
          <input
            type="number"
            min="50"
            max="800"
            value={form.n}
            onInput={(e) => setForm({ ...form, n: Number(e.currentTarget.value) })}
          />
        </label>
        <label>
          Semilla
          <input
            type="number"
            min="0"
            value={form.seed}
            onInput={(e) => setForm({ ...form, seed: Number(e.currentTarget.value) })}
          />
        </label>
        <label>
          Atención media (s)
          <input
            type="number"
            step="0.1"
            min="1"
            max="120"
            value={form.service}
            onInput={(e) => setForm({ ...form, service: Number(e.currentTarget.value) })}
          />
        </label>
        <button type="submit">Simular</button>
        <span class="status">{status}</span>
      </form>
    </section>
  );
}
