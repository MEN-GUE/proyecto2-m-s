import { define } from "../../utils.ts";

const ROOT = Deno.env.get("PROJECT_ROOT") ?? `${Deno.cwd()}/..`;
const PYTHON = Deno.env.get("PYTHON") ?? `${ROOT}/.venv/bin/python`;

function int(v: string | null, lo: number, hi: number, def: number) {
  const x = Number(v ?? def);
  return Number.isInteger(x) && x >= lo && x <= hi ? x : null;
}

export const handler = define.handlers({
  async GET(ctx) {
    const q = ctx.url.searchParams;
    const layout = q.get("layout") ?? "base";
    const n = int(q.get("n"), 50, 800, 500);
    const seed = int(q.get("seed"), 0, 999999, 1001);
    const service = Number(q.get("service") ?? 16.4);
    if (!["base", "pso"].includes(layout) || n === null || seed === null || !(service > 0 && service <= 120)) {
      return Response.json({ error: "Parámetros inválidos" }, { status: 400 });
    }
    const cmd = new Deno.Command(PYTHON, {
      args: [
        "-m",
        "src.visualization.export_web",
        "--layout",
        layout,
        "--n",
        `${n}`,
        "--seed",
        `${seed}`,
        "--service",
        `${service}`,
        "--stdout",
      ],
      cwd: ROOT,
    });
    const { code, stdout, stderr } = await cmd.output();
    if (code !== 0) {
      return Response.json({ error: new TextDecoder().decode(stderr).slice(-500) }, { status: 500 });
    }
    return new Response(stdout, { headers: { "content-type": "application/json" } });
  },
});
