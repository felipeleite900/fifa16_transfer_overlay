const form = document.getElementById("filters-form");
const statusEl = document.getElementById("status");
const resultsBody = document.getElementById("results-body");
const saveInfoEl = document.getElementById("save-info");

function getFilters() {
  return {
    name: document.getElementById("name").value.trim(),
    position: document.getElementById("position").value,
    minAge: document.getElementById("min-age").value,
    maxAge: document.getElementById("max-age").value,
    minOverall: document.getElementById("min-overall").value,
    maxOverall: document.getElementById("max-overall").value,
    minPotential: document.getElementById("min-potential").value,
    maxPotential: document.getElementById("max-potential").value,
    nationality: document.getElementById("nationality").value.trim(),
    foot: document.getElementById("foot").value,
    sortBy: document.getElementById("sort-by").value,
    limit: 200,
  };
}

function renderResults(players) {
  resultsBody.innerHTML = "";

  for (const p of players) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(p.name)}</td>
      <td>${p.age ?? "-"}</td>
      <td>${p.position}</td>
      <td>${p.overall}</td>
      <td>${p.potential}</td>
      <td>${escapeHtml(p.nationality)}</td>
      <td>${p.preferred_foot}</td>
      <td>${p.height}cm</td>
    `;
    resultsBody.appendChild(tr);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

async function runSearch(event) {
  event.preventDefault();

  statusEl.textContent = "Buscando...";
  resultsBody.innerHTML = "";

  const filters = getFilters();
  const result = await window.fifaApi.searchPlayers(filters);

  if (result.error) {
    statusEl.textContent = `Erro: ${result.error}`;
    return;
  }

  statusEl.textContent = `${result.players.length} jogador(es) encontrado(s).`;
  renderResults(result.players);
}

form.addEventListener("submit", runSearch);

// Busca inicial ao abrir (sem filtros, ordenado por potencial) para já
// mostrar algo na tela.
window.addEventListener("DOMContentLoaded", async () => {
  const saves = await window.fifaApi.listSaves();
  if (saves.length > 0) {
    const latest = saves[0].split("\\").pop();
    saveInfoEl.textContent = `save: ...${latest}`;
  } else {
    saveInfoEl.textContent = "nenhum save encontrado";
  }

  runSearch(new Event("submit"));
});
