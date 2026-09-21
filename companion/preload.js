const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("fifaApi", {
  searchPlayers: (filters) => ipcRenderer.invoke("search-players", filters),
  listSaves: () => ipcRenderer.invoke("list-saves"),
});
