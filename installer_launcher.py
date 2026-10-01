import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import messagebox

APP_NAME = "Confeitaria Deise Brandao"
INSTALL_ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
INSTALL_DIR = Path(os.environ.get("CONFEITARIA_INSTALL_DIR", str(INSTALL_ROOT / APP_NAME)))
CREATE_SHORTCUTS = os.environ.get("CONFEITARIA_SHORTCUTS", "1") != "0"
AUTO_LAUNCH = os.environ.get("CONFEITARIA_AUTO_LAUNCH", "1") != "0"
LOG_PATH = Path(os.environ.get("CONFEITARIA_INSTALL_LOG", str(Path(os.environ.get("TEMP", str(Path.home()))) / "confeitaria_installer.log")))


def logar(mensagem: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as arquivo:
            arquivo.write(mensagem + "\n")
    except Exception:
        pass


def obter_base():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


BASE_DIR = obter_base()
PACKAGE_ZIP = BASE_DIR / "installer_app_package.zip"


def escrever_desinstalador(destino: Path) -> None:
    linhas = [
        "@echo off",
        "setlocal",
        f'set "APP_NAME={APP_NAME}"',
        'set "TARGET_DIR=%LOCALAPPDATA%\\%APP_NAME%"',
        f'set "DESKTOP_SHORTCUT=%USERPROFILE%\\Desktop\\{APP_NAME}.lnk"',
        f'set "STARTMENU_SHORTCUT=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\{APP_NAME}.lnk"',
        "",
        'if exist "%DESKTOP_SHORTCUT%" del /F /Q "%DESKTOP_SHORTCUT%"',
        'if exist "%STARTMENU_SHORTCUT%" del /F /Q "%STARTMENU_SHORTCUT%"',
        'if exist "%TARGET_DIR%" rmdir /S /Q "%TARGET_DIR%"',
        "",
        "echo Aplicativo removido.",
        "pause",
        "",
    ]
    (destino / f"Desinstalar {APP_NAME}.bat").write_text("\n".join(linhas), encoding="utf-8")


def criar_atalhos(exe_path: str) -> None:
    if not CREATE_SHORTCUTS:
        logar("Atalhos desativados por configuracao.")
        return

    script = f"""
$shell = New-Object -ComObject WScript.Shell
$target = '{exe_path}'
$work = Split-Path $target
$desktop = [Environment]::GetFolderPath('Desktop')
$startMenu = Join-Path $env:APPDATA 'Microsoft\\Windows\\Start Menu\\Programs'
foreach ($shortcutPath in @((Join-Path $desktop '{APP_NAME}.lnk'), (Join-Path $startMenu '{APP_NAME}.lnk'))) {{
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $work
    $shortcut.IconLocation = $target + ',0'
    $shortcut.Save()
}}
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logar("Atalhos criados com sucesso.")


def instalar_aplicativo() -> Path:
    logar(f"Inicio da instalacao. Base: {BASE_DIR}")
    logar(f"Pacote esperado: {PACKAGE_ZIP}")
    logar(f"Destino: {INSTALL_DIR}")

    if not PACKAGE_ZIP.exists():
        raise FileNotFoundError(f"Pacote nao encontrado: {PACKAGE_ZIP}")

    INSTALL_DIR.parent.mkdir(parents=True, exist_ok=True)
    if INSTALL_DIR.exists():
        logar("Removendo instalacao anterior.")
        shutil.rmtree(INSTALL_DIR)

    staging_dir = INSTALL_DIR.parent / f"{APP_NAME}__tmp"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(PACKAGE_ZIP, "r") as pacote:
        pacote.extractall(staging_dir)
    logar("Arquivos extraidos para a pasta temporaria.")

    exe_nome = f"{APP_NAME}.exe"
    source_dir = None

    exe_raiz = staging_dir / exe_nome
    exe_em_pasta = staging_dir / APP_NAME / exe_nome
    if exe_raiz.exists():
        source_dir = staging_dir
    elif exe_em_pasta.exists():
        source_dir = staging_dir / APP_NAME
    else:
        encontrados = list(staging_dir.rglob(exe_nome))
        if encontrados:
            source_dir = encontrados[0].parent

    if source_dir is None:
        raise FileNotFoundError(f"Executavel nao encontrado dentro do pacote: {exe_nome}")

    if source_dir == staging_dir:
        shutil.move(str(staging_dir), str(INSTALL_DIR))
    else:
        shutil.move(str(source_dir), str(INSTALL_DIR))
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
    logar("Conteudo movido para o destino final.")

    exe_path = INSTALL_DIR / exe_nome
    if not exe_path.exists():
        raise FileNotFoundError(f"Executavel nao encontrado apos a instalacao: {exe_path}")

    escrever_desinstalador(INSTALL_DIR)
    logar("Desinstalador criado.")
    criar_atalhos(str(exe_path))
    logar(f"Instalacao concluida. Executavel: {exe_path}")
    return exe_path


class InstallerUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Instalador - Confeitaria Deise Brandao")
        self.root.geometry("520x300")
        self.root.resizable(False, False)
        self.root.configure(bg="#fff8fc")

        self.status_var = tk.StringVar(value="Pronto para instalar o sistema.")
        self.path_var = tk.StringVar(value=f"Local de instalacao: {INSTALL_DIR}")
        self.installed_exe = None

        frame = tk.Frame(root, bg="#fff8fc", padx=24, pady=24)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Confeitaria Deise Brandao", font=("Segoe UI", 18, "bold"), fg="#9f216d", bg="#fff8fc").pack(anchor="w")
        tk.Label(frame, text="Instalador do sistema de vendas e fluxo de caixa", font=("Segoe UI", 10), fg="#8a5573", bg="#fff8fc").pack(anchor="w", pady=(4, 18))
        tk.Label(frame, textvariable=self.status_var, font=("Segoe UI", 10, "bold"), fg="#6f2a5a", bg="#fff8fc", wraplength=450, justify="left").pack(anchor="w", pady=(0, 10))
        tk.Label(frame, textvariable=self.path_var, font=("Segoe UI", 9), fg="#8a5573", bg="#fff8fc", wraplength=450, justify="left").pack(anchor="w", pady=(0, 20))

        self.progress = tk.Label(frame, text="O instalador cria atalhos e abre o sistema ao final.", font=("Segoe UI", 9), fg="#8a5573", bg="#fff8fc", wraplength=450, justify="left")
        self.progress.pack(anchor="w", pady=(0, 20))

        self.btn_install = tk.Button(frame, text="Instalar agora", command=self.iniciar_instalacao, bg="#cf2f92", fg="white", activebackground="#9f216d", activeforeground="white", relief="flat", padx=14, pady=10, cursor="hand2")
        self.btn_install.pack(fill="x", pady=(0, 10))

        self.btn_close = tk.Button(frame, text="Fechar", command=self.root.destroy, bg="#fbe7f4", fg="#9f216d", relief="flat", padx=14, pady=10, cursor="hand2")
        self.btn_close.pack(fill="x")

    def iniciar_instalacao(self) -> None:
        self.btn_install.config(state="disabled")
        self.status_var.set("Instalando, aguarde...")
        self.progress.config(text="Copiando arquivos e criando atalhos...")
        threading.Thread(target=self._instalar, daemon=True).start()

    def _instalar(self) -> None:
        try:
            exe_path = instalar_aplicativo()
            self.installed_exe = exe_path
            self.root.after(0, self.instalacao_ok)
        except Exception as erro:
            logar(f"Erro na instalacao: {erro}")
            self.root.after(0, lambda: self.instalacao_erro(erro))

    def instalacao_ok(self) -> None:
        self.status_var.set("Instalacao concluida com sucesso.")
        self.progress.config(text="Voce ja pode abrir pelo atalho criado na area de trabalho.")
        self.btn_install.config(text="Abrir sistema", state="normal", command=self.abrir_sistema)
        if AUTO_LAUNCH:
            self.abrir_sistema()

    def instalacao_erro(self, erro: Exception) -> None:
        self.status_var.set("Falha na instalacao.")
        self.progress.config(text="Revise a mensagem abaixo e tente novamente.")
        self.btn_install.config(state="normal")
        messagebox.showerror("Erro na instalacao", str(erro))

    def abrir_sistema(self) -> None:
        if self.installed_exe and Path(self.installed_exe).exists():
            os.startfile(str(self.installed_exe))


def executar_modo_silencioso() -> int:
    try:
        exe_path = instalar_aplicativo()
        if AUTO_LAUNCH:
            os.startfile(str(exe_path))
        return 0
    except Exception as erro:
        logar(f"Erro no modo silencioso: {erro}")
        return 1


def main() -> int:
    if "--install" in sys.argv or "--silent" in sys.argv:
        return executar_modo_silencioso()

    root = tk.Tk()
    InstallerUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
