const { app, BrowserWindow, ipcMain, Menu, shell } = require('electron');
const path = require('node:path');

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL);
let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 920,
    minHeight: 680,
    frame: false,
    autoHideMenuBar: true,
    backgroundColor: '#0D0D0D',
    title: 'Agent',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  if (isDev) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
    return;
  }

  mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createWindow();

  ipcMain.handle('window:minimize', () => {
    if (!mainWindow) {
      return false;
    }

    mainWindow.minimize();
    return true;
  });

  ipcMain.handle('window:toggle-maximize', () => {
    if (!mainWindow) {
      return false;
    }

    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }

    return mainWindow.isMaximized();
  });

  ipcMain.handle('window:close', () => {
    if (!mainWindow) {
      return false;
    }

    mainWindow.close();
    return true;
  });

  ipcMain.handle('shell:open-external', async (_event, url) => {
    try {
      const parsedUrl = new URL(url);
      if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
        return false;
      }

      await shell.openExternal(parsedUrl.toString());
      return true;
    } catch {
      return false;
    }
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
