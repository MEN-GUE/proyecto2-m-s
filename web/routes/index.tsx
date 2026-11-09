import { define } from "../utils.ts";
import Player from "../islands/Player.tsx";

export default define.page(function Home() {
  return (
    <main>
      <header>
        <h1>Salida de público al cierre de un concierto</h1>
        <p>
          Zona sur de la Explanada Cayalá, 80 x 50 m. Cada punto es una persona: azul si camina directo a un portón,
          rojo si pasa antes por una barra cashless.
        </p>
      </header>
      <Player />
    </main>
  );
});
