// Processo principal do Electron.
//
// Responsabilidades:
// - Criar a janela da interface (escondida por padrão).
// - Registrar um atalho de teclado global (funciona mesmo com o
//   FIFA em foco) para abrir/fechar a janela.
// - Encaminhar pedidos de busca (do renderer) para o script Python
//   fifa16_search.py via subprocess, retornando o JSON decodificado.
//
// NOTA sobre o atalho de CONTROLE (gamepad): globalShortcut do
// Electron só cobre teclado. Suporte a atalho via controle físico
// (XInput) é feito por um processo Python separado
// (gamepad_watcher.py) que sinaliza este processo via arquivo -- ver
// seção "Gamepad watcher" mais abaixo.

const { app, BrowserWindow, globalShortcut, ipcMain } = require("electron");
const path = require("node:path");
const { spawn } = require("node:child_process");
const fs = require("node:fs");

// Caminho para a pasta raiz do projeto Python (fifa16_search.py etc)
const PYTHON_PROJECT_DIR = path.join(__dirname, "..");
const PYTHON_EXECUTABLE = "python"; // assume python no PATH

// Atalho de teclado para abrir/fechar a janela (fallback enquanto o
// gamepad watcher não está ativo, e útil para testes de desktop).
const TOGGLE_HOTKEY = "CommandOrControl+Shift+P";

// Arquivo usado como sinal simples de IPC entre o gamepad_watcher.py
// (processo Python separado, monitorando XInput) e este processo
// Electron. O watcher escreve um timestamp/comando no arquivo; aqui
// nós observamos mudanças (fs.watch) e reagimos.
const GAMEPAD_SIGNAL_FILE = path.join(__dirname, "..", "fifa_process_identifier", "gamepad_signal.txt");

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    show: false,
    alwaysOnTop: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  // Esconde em vez de fechar quando o usuário clica no X, para reabrir
  // rápido sem reprocessar dados.
  mainWindow.on("close", (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

function toggleWindow() {
  if (!mainWindow) return;

  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
}

function watchGamepadSignal() {
  const dir = path.dirname(GAMEPAD_SIGNAL_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  if (!fs.existsSync(GAMEPAD_SIGNAL_FILE)) {
    fs.writeFileSync(GAMEPAD_SIGNAL_FILE, "");
  }

  // O watcher Python escreve "toggle:<timestamp_ns>" a cada
  // ativação do combo — o timestamp garante que o conteúdo do
  // arquivo mude a cada sinal (mesmo em ativações consecutivas),
  // permitindo detectar de forma confiável via comparação de
  // conteúdo. Guardamos apenas o último timestamp já processado.
  let lastTimestamp = "";
  try {
    const initial = fs.readFileSync(GAMEPAD_SIGNAL_FILE, "utf-8");
    if (initial.startsWith("toggle:")) {
      lastTimestamp = initial.slice("toggle:".length).trim();
    }
  } catch {
    // arquivo vazio/inexistente na primeira vez, ok.
  }

  // fs.watch no Windows costuma disparar o evento "change" mais de
  // uma vez para uma única escrita de arquivo — debounce adicional
  // aqui evita processar o mesmo sinal duas vezes rapidamente (o que
  // causaria show() seguido de hide() quase instantâneo, parecendo
  // um "piscar" da janela em vez de abrir de fato).
  let debounceTimer = null;

  fs.watch(GAMEPAD_SIGNAL_FILE, () => {
    if (debounceTimer) return;

    debounceTimer = setTimeout(() => {
      debounceTimer = null;
    }, 250);

    try {
      const content = fs.readFileSync(GAMEPAD_SIGNAL_FILE, "utf-8").trim();
      if (!content.startsWith("toggle:")) return;

      const timestamp = content.slice("toggle:".length);
      if (timestamp !== lastTimestamp) {
        lastTimestamp = timestamp;
        toggleWindow();
      }
    } catch (err) {
      // arquivo pode estar sendo escrito no exato momento; ignora e
      // tenta na próxima mudança.
    }
  });
}

app.whenReady().then(() => {
  createWindow();

  // A janela inicia escondida por padrão (uso real: o app roda em
  // segundo plano e só aparece quando o usuário aciona o atalho de
  // teclado ou o combo do controle). Defina SHOW_ON_STARTUP=1 para
  // depurar visualmente durante desenvolvimento.
  if (process.env.SHOW_ON_STARTUP === "1") {
    mainWindow.once("ready-to-show", () => {
      mainWindow.show();
    });
  }

  const registered = globalShortcut.register(TOGGLE_HOTKEY, toggleWindow);
  if (!registered) {
    console.error(`Falha ao registrar o atalho ${TOGGLE_HOTKEY}`);
  }

  watchGamepadSignal();
});

app.on("before-quit", () => {
  app.isQuitting = true;
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

// ----------------------------------------------------------------------
// IPC: busca de jogadores via subprocess Python
// ----------------------------------------------------------------------

ipcMain.handle("search-players", async (_event, filters) => {
  return runPythonSearch(filters);
});

ipcMain.handle("list-saves", async () => {
  return runPythonListSaves();
});

function buildArgs(filters) {
  const args = ["fifa16_search.py"];

  const mapping = {
    name: "--name",
    position: "--position",
    minOverall: "--min-overall",
    maxOverall: "--max-overall",
    minPotential: "--min-potential",
    maxPotential: "--max-potential",
    nationality: "--nationality",
    foot: "--foot",
    minAge: "--min-age",
    maxAge: "--max-age",
    limit: "--limit",
    sortBy: "--sort-by",
    saveDir: "--save-dir",
  };

  for (const [key, flag] of Object.entries(mapping)) {
    const value = filters?.[key];
    if (value !== undefined && value !== null && value !== "") {
      args.push(flag, String(value));
    }
  }

  return args;
}

function runPythonSearch(filters) {
  return new Promise((resolve) => {
    const args = buildArgs(filters);
    const proc = spawn(PYTHON_EXECUTABLE, args, {
      cwd: PYTHON_PROJECT_DIR,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });

    let stdout = Buffer.alloc(0);
    let stderr = Buffer.alloc(0);

    proc.stdout.on("data", (chunk) => {
      stdout = Buffer.concat([stdout, chunk]);
    });
    proc.stderr.on("data", (chunk) => {
      stderr = Buffer.concat([stderr, chunk]);
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        resolve({
          error: stderr.toString("utf-8") || `python exited with code ${code}`,
        });
        return;
      }
      try {
        const data = JSON.parse(stdout.toString("utf-8"));
        resolve({ players: data });
      } catch (err) {
        resolve({ error: `Falha ao parsear JSON: ${err.message}` });
      }
    });

    proc.on("error", (err) => {
      resolve({ error: `Falha ao executar python: ${err.message}` });
    });
  });
}

function runPythonListSaves() {
  return new Promise((resolve) => {
    const proc = spawn(PYTHON_EXECUTABLE, ["fifa16_search.py", "--list-saves"], {
      cwd: PYTHON_PROJECT_DIR,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });

    let stdout = Buffer.alloc(0);

    proc.stdout.on("data", (chunk) => {
      stdout = Buffer.concat([stdout, chunk]);
    });

    proc.on("close", () => {
      try {
        resolve(JSON.parse(stdout.toString("utf-8")));
      } catch {
        resolve([]);
      }
    });
  });
}
