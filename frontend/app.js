// Azar Sincronizado — frontend
// Se comunica con la API FastAPI que corre en el mismo host.

const API_BASE = window.location.origin;

// ---------- Navegación entre pestañas ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ---------- Estado de la API ----------
async function comprobarEstado() {
  const el = document.getElementById("estado-api");
  try {
    const res = await fetch(`${API_BASE}/estado`);
    if (!res.ok) throw new Error("respuesta no OK");
    const data = await res.json();
    el.textContent = `API activa · ${data.sorteos_registrados} sorteos en la base`;
    el.classList.add("ok");
  } catch (err) {
    el.textContent = "No se pudo conectar con la API";
    el.classList.add("error");
  }
}

// ---------- Consulta histórica ----------
async function cargarSorteos(params = {}) {
  const tbody = document.getElementById("tabla-sorteos-body");
  tbody.innerHTML = `<tr><td colspan="6" class="vacio">Cargando resultados…</td></tr>`;

  const url = new URL(`${API_BASE}/sorteos`);
  url.searchParams.set("limit", "200");
  Object.entries(params).forEach(([k, v]) => {
    if (v) url.searchParams.set(k, v);
  });

  try {
    const res = await fetch(url);
    const data = await res.json();

    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="vacio">
        No hay sorteos cargados todavía. Usa <code>POST /sorteos</code> o el script de carga para poblar la base.
      </td></tr>`;
      return;
    }

    tbody.innerHTML = data
      .map(
        (s) => `
        <tr>
          <td>${s.fecha}</td>
          <td>${s.numero_sorteo ?? "—"}</td>
          <td><span class="premio-mayor">${s.numero}</span></td>
          <td>${s.serie ?? "—"}</td>
          <td>${s.fuente ?? "—"}</td>
          <td><span class="chip-verificado ${s.verificado ? "si" : "no"}">${s.verificado ? "Verificado" : "Sin verificar"}</span></td>
        </tr>`
      )
      .join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="vacio">Error al consultar la API.</td></tr>`;
  }
}

document.getElementById("form-filtros").addEventListener("submit", (e) => {
  e.preventDefault();
  cargarSorteos({
    anio_desde: document.getElementById("f-anio-desde").value,
    anio_hasta: document.getElementById("f-anio-hasta").value,
  });
});

document.getElementById("btn-limpiar").addEventListener("click", () => {
  document.getElementById("f-anio-desde").value = "";
  document.getElementById("f-anio-hasta").value = "";
  cargarSorteos();
});

// ---------- Estadísticas ----------
async function cargarEstadisticas() {
  try {
    const res = await fetch(`${API_BASE}/estadisticas/resumen`);
    const data = await res.json();

    document.getElementById("r-total").textContent = data.total_sorteos ?? 0;
    document.getElementById("r-min").textContent = data.anio_min ?? "—";
    document.getElementById("r-max").textContent = data.anio_max ?? "—";

    const cont = document.getElementById("frecuentes-list");
    if (!data.numeros_mas_frecuentes?.length) {
      cont.innerHTML = `<p class="hint">Aún no hay suficientes datos para calcular frecuencias.</p>`;
      return;
    }
    cont.innerHTML = data.numeros_mas_frecuentes
      .map(
        (n) => `<div class="bolilla">${n.numero}<span class="veces">${n.veces}×</span></div>`
      )
      .join("");
  } catch (err) {
    console.error("Error cargando estadísticas", err);
  }
}

// ---------- Ciclos del siete ----------
document.getElementById("form-ciclos").addEventListener("submit", async (e) => {
  e.preventDefault();
  const tipo = document.getElementById("f-tipo-ciclo").value;
  const tbody = document.getElementById("tabla-ciclos-body");
  tbody.innerHTML = `<tr><td colspan="5" class="vacio">Buscando coincidencias…</td></tr>`;

  const url = new URL(`${API_BASE}/estadisticas/ciclos-siete`);
  if (tipo) url.searchParams.set("tipo", tipo);

  try {
    const res = await fetch(url);
    const data = await res.json();

    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="vacio">
        No se encontraron coincidencias (o aún no hay suficientes datos cargados).
      </td></tr>`;
      return;
    }

    tbody.innerHTML = data
      .map(
        (c) => `
        <tr>
          <td>${c.tipo.replaceAll("_", " ")}</td>
          <td><span class="premio-mayor">${c.valor}</span></td>
          <td>${c.ciclo_anios} años</td>
          <td>${c.anio_origen}</td>
          <td>${c.anio_repite}</td>
        </tr>`
      )
      .join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="vacio">Error al consultar la API.</td></tr>`;
  }
});

// ---------- OCR de recortes de periódico ----------
document.getElementById("form-ocr").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("f-ocr-imagen");
  if (!input.files.length) return;

  const boton = e.target.querySelector("button");
  boton.disabled = true;
  boton.textContent = "Analizando…";

  const formData = new FormData();
  formData.append("archivo", input.files[0]);

  try {
    const res = await fetch(`${API_BASE}/ocr/procesar`, { method: "POST", body: formData });
    if (!res.ok) throw new Error("fallo OCR");
    const data = await res.json();

    document.getElementById("ocr-resultado").hidden = false;
    document.getElementById("ocr-fecha").value = data.fecha_candidata ?? "";
    document.getElementById("ocr-numero").value = (data.numeros_candidatos && data.numeros_candidatos[0]) || "";
    document.getElementById("ocr-serie").value = data.serie_candidata ?? "";
    document.getElementById("ocr-texto-crudo").textContent = data.texto_detectado || "(sin texto detectado)";

    const otros = (data.numeros_candidatos || []).slice(1);
    document.getElementById("ocr-candidatos-numeros").textContent = otros.length
      ? `Otros números detectados en la imagen, por si el primero no es el correcto: ${otros.join(", ")}`
      : "";
  } catch (err) {
    alert("No se pudo analizar la imagen. Verifica que el archivo sea una foto/escaneo legible.");
  } finally {
    boton.disabled = false;
    boton.textContent = "Analizar con OCR";
  }
});

document.getElementById("form-confirmar-ocr").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    loteria: "Lotería de Bogotá",
    fecha: document.getElementById("ocr-fecha").value,
    numero: document.getElementById("ocr-numero").value,
    serie: document.getElementById("ocr-serie").value || null,
    fuente: "OCR de periódico (pendiente de verificación)",
    verificado: false,
  };

  try {
    const res = await fetch(`${API_BASE}/sorteos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Error al guardar");
    }
    alert("Sorteo guardado correctamente (marcado como no verificado hasta confirmar con una segunda fuente).");
    document.getElementById("ocr-resultado").hidden = true;
    document.getElementById("form-ocr").reset();
    cargarSorteos();
    cargarEstadisticas();
  } catch (err) {
    alert(`No se pudo guardar: ${err.message}`);
  }
});

// ---------- Inicialización ----------
comprobarEstado();
cargarSorteos();
cargarEstadisticas();
