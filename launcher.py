import socket
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox

from werkzeug.serving import make_server

from app import DATABASE, DATA_DIR, app, init_db

HOST = "127.0.0.1"


def encontrar_porta_livre(porta_preferida=5000):
    for porta in [porta_preferida, 5001, 5002, 8000, 8080]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((HOST, porta))
                return porta
            except OSError:
                continue

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


class ServidorThread(threading.Thread):
    def __init__(self, flask_app, host, port):
        super().__init__(daemon=True)
        self.server = make_server(host, port, flask_app, threaded=True)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Confeitaria Deise Brandão")
        self.root.geometry("470x260")
        self.root.resizable(False, False)
        self.root.configure(bg="#fff8fc")
        self.root.protocol("WM_DELETE_WINDOW", self.fechar_tudo)

        self.server_thread = None
        self.porta = None
        self.url = None

        self.status_var = tk.StringVar(value="Pronto para iniciar o sistema.")
        self.info_var = tk.StringVar(value=f"Banco de dados: {DATABASE}")

        frame = tk.Frame(root, bg="#fff8fc", padx=24, pady=22)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Deise Brandão Confeitaria",
            font=("Segoe UI", 18, "bold"),
            fg="#9f216d",
            bg="#fff8fc",
        ).pack(anchor="w")

        tk.Label(
            frame,
            text="Sistema de vendas e fluxo de caixa",
            font=("Segoe UI", 10),
            fg="#8a5573",
            bg="#fff8fc",
        ).pack(anchor="w", pady=(4, 18))

        tk.Label(
            frame,
            textvariable=self.status_var,
            font=("Segoe UI", 10, "bold"),
            fg="#6f2a5a",
            bg="#fff8fc",
            wraplength=400,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        tk.Label(
            frame,
            textvariable=self.info_var,
            font=("Segoe UI", 9),
            fg="#8a5573",
            bg="#fff8fc",
            wraplength=400,
            justify="left",
        ).pack(anchor="w", pady=(0, 18))

        botoes = tk.Frame(frame, bg="#fff8fc")
        botoes.pack(fill="x")

        self.btn_iniciar = tk.Button(
            botoes,
            text="Iniciar sistema",
            command=self.iniciar_sistema,
            bg="#cf2f92",
            fg="white",
            activebackground="#9f216d",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=10,
            cursor="hand2",
        )
        self.btn_iniciar.pack(fill="x", pady=(0, 10))

        self.btn_abrir = tk.Button(
            botoes,
            text="Abrir no navegador",
            command=self.abrir_navegador,
            bg="white",
            fg="#cf2f92",
            relief="solid",
            borderwidth=1,
            padx=14,
            pady=10,
            cursor="hand2",
            state="disabled",
        )
        self.btn_abrir.pack(fill="x", pady=(0, 10))

        self.btn_fechar = tk.Button(
            botoes,
            text="Fechar sistema",
            command=self.fechar_tudo,
            bg="#fbe7f4",
            fg="#9f216d",
            relief="flat",
            padx=14,
            pady=10,
            cursor="hand2",
        )
        self.btn_fechar.pack(fill="x")

        root.after(500, self.iniciar_sistema)

    def iniciar_sistema(self):
        if self.server_thread and self.server_thread.is_alive():
            self.abrir_navegador()
            return

        try:
            self.porta = encontrar_porta_livre()
            self.url = f"http://{HOST}:{self.porta}"

            with app.app_context():
                init_db()

            self.server_thread = ServidorThread(app, HOST, self.porta)
            self.server_thread.start()

            time.sleep(0.8)
            self.status_var.set(f"Sistema online em {self.url}")
            self.info_var.set(f"Banco salvo em: {DATABASE}")
            self.btn_abrir.config(state="normal")
            webbrowser.open(self.url)
        except Exception as erro:
            messagebox.showerror("Erro ao iniciar", f"Não foi possível iniciar o sistema.\n\n{erro}")
            self.status_var.set("Falha ao iniciar o sistema.")

    def abrir_navegador(self):
        if self.url:
            webbrowser.open(self.url)

    def fechar_tudo(self):
        try:
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.shutdown()
        finally:
            self.root.destroy()


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
