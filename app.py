import json
import os
import sqlite3
import threading
import webbrowser
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

from flask import Flask, Response, flash, g, jsonify, redirect, render_template, request, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", str(BASE_DIR / "confeitaria.db")))
LOGO_PATH = BASE_DIR / "static" / "img" / "logo.jpg"
FORMAS_PAGAMENTO = ["Dinheiro", "Pix", "Cartão de Débito", "Cartão de Crédito"]
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
RESET_PASSWORD = os.environ.get("RESET_PASSWORD", "chefinha")
APP_VERSION = "1.2.0"

BRAND_PRIMARY = colors.HexColor("#cf2f92")
BRAND_SECONDARY = colors.HexColor("#fbe7f4")
BRAND_TEXT = colors.HexColor("#6f2a5a")
BRAND_MUTED = colors.HexColor("#8f5a7a")
PDF_FONT_REGULAR = "Helvetica"
PDF_FONT_BOLD = "Helvetica-Bold"
PDF_FONTS_READY = False

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "confeitaria-flask-secret-key")
app.jinja_env.globals["APP_VERSION"] = APP_VERSION


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            preco_custo REAL NOT NULL CHECK (preco_custo >= 0),
            preco_venda REAL NOT NULL CHECK (preco_venda >= 0),
            estoque INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total REAL NOT NULL CHECK (total >= 0),
            forma_pagamento TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS itens_venda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL CHECK (quantidade > 0),
            preco_unitario REAL NOT NULL CHECK (preco_unitario >= 0),
            subtotal REAL NOT NULL CHECK (subtotal >= 0),
            FOREIGN KEY (venda_id) REFERENCES vendas (id) ON DELETE CASCADE,
            FOREIGN KEY (produto_id) REFERENCES produtos (id)
        );

        CREATE TABLE IF NOT EXISTS fluxo_caixa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK (tipo IN ('ENTRADA', 'SAIDA')),
            descricao TEXT NOT NULL,
            valor REAL NOT NULL CHECK (valor >= 0),
            referencia_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );
        """
    )

    colunas_fluxo = {col['name'] for col in db.execute("PRAGMA table_info(fluxo_caixa)").fetchall()}
    if 'data_operacao' not in colunas_fluxo:
        db.execute("ALTER TABLE fluxo_caixa ADD COLUMN data_operacao TEXT")

    colunas_vendas = {col['name'] for col in db.execute("PRAGMA table_info(vendas)").fetchall()}
    if 'data_operacao' not in colunas_vendas:
        db.execute("ALTER TABLE vendas ADD COLUMN data_operacao TEXT")

    db.execute(
        """
        INSERT INTO configuracoes (chave, valor)
        VALUES ('data_caixa_atual', ?)
        ON CONFLICT(chave) DO NOTHING
        """,
        (date.today().isoformat(),),
    )
    db.execute("UPDATE fluxo_caixa SET data_operacao = date(created_at) WHERE data_operacao IS NULL OR data_operacao = ''")
    db.execute("UPDATE vendas SET data_operacao = date(created_at) WHERE data_operacao IS NULL OR data_operacao = ''")
    db.commit()


def query_all(sql, params=()):
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def query_one(sql, params=()):
    cur = get_db().execute(sql, params)
    row = cur.fetchone()
    cur.close()
    return row


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}


@app.template_filter("moeda")
def moeda(valor):
    numero = float(valor or 0)
    texto = f"{numero:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


@app.template_filter("datahora")
def datahora(valor):
    return formatar_datahora(valor)


def formatar_datahora(valor):
    if not valor:
        return ""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(valor, fmt).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return str(valor)


def moeda_pdf(valor):
    return moeda(valor)


def resetar_programa(senha_admin):
    validar_senha_reset(senha_admin)

    db = get_db()
    try:
        db.execute("BEGIN")
        db.execute("DELETE FROM itens_venda")
        db.execute("DELETE FROM vendas")
        db.execute("DELETE FROM fluxo_caixa")
        db.execute("DELETE FROM produtos")
        db.execute("DELETE FROM configuracoes")
        db.execute(
            """
            INSERT INTO configuracoes (chave, valor)
            VALUES ('data_caixa_atual', ?)
            """,
            (date.today().isoformat(),),
        )
        db.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('produtos', 'vendas', 'itens_venda', 'fluxo_caixa')"
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


def obter_produtos():
    return query_all("SELECT * FROM produtos ORDER BY nome ASC")


def obter_produto_por_id(produto_id):
    return query_one("SELECT * FROM produtos WHERE id = ?", (produto_id,))


def normalizar_data_operacao(data_texto=None):
    valor = (data_texto or '').strip()
    if not valor:
        return obter_data_caixa_atual()
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValueError("Data do caixa inválida.")


def formatar_data_operacao(data_texto):
    return datetime.strptime(data_texto, "%Y-%m-%d").strftime("%d/%m/%Y")


def obter_data_caixa_atual():
    linha = query_one("SELECT valor FROM configuracoes WHERE chave = 'data_caixa_atual'")
    if linha and linha["valor"]:
        return linha["valor"]
    return date.today().isoformat()


def definir_data_caixa_atual(data_operacao):
    data_operacao = normalizar_data_operacao(data_operacao)
    db = get_db()
    db.execute(
        """
        INSERT INTO configuracoes (chave, valor)
        VALUES ('data_caixa_atual', ?)
        ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
        """,
        (data_operacao,),
    )
    db.commit()
    return data_operacao


def avancar_data_caixa(senha_admin):
    validar_senha_admin(senha_admin)
    atual = datetime.strptime(obter_data_caixa_atual(), "%Y-%m-%d").date()
    proxima = atual + timedelta(days=1)
    definir_data_caixa_atual(proxima.isoformat())
    return proxima.isoformat()


def obter_produtos():
    return query_all("SELECT * FROM produtos ORDER BY nome ASC")


def obter_produto_por_id(produto_id):
    return query_one("SELECT * FROM produtos WHERE id = ?", (produto_id,))


def obter_fluxo_caixa(data_operacao=None):
    data_operacao = normalizar_data_operacao(data_operacao)
    return query_all(
        """
        SELECT
            fc.id,
            fc.tipo,
            fc.descricao,
            fc.valor,
            fc.referencia_id,
            fc.created_at,
            fc.data_operacao,
            CASE
                WHEN fc.tipo = 'ENTRADA' THEN v.forma_pagamento
                ELSE NULL
            END AS forma_pagamento
        FROM fluxo_caixa fc
        LEFT JOIN vendas v ON v.id = fc.referencia_id
        WHERE fc.data_operacao = ?
        ORDER BY datetime(fc.created_at) DESC, fc.id DESC
        """,
        (data_operacao,),
    )


def obter_lancamento_por_id(lancamento_id):
    return query_one(
        """
        SELECT
            fc.id,
            fc.tipo,
            fc.descricao,
            fc.valor,
            fc.referencia_id,
            fc.created_at,
            fc.data_operacao,
            CASE
                WHEN fc.tipo = 'ENTRADA' THEN v.forma_pagamento
                ELSE NULL
            END AS forma_pagamento
        FROM fluxo_caixa fc
        LEFT JOIN vendas v ON v.id = fc.referencia_id
        WHERE fc.id = ?
        """,
        (lancamento_id,),
    )


def validar_senha_admin(senha_admin):
    if (senha_admin or "").strip() != ADMIN_PASSWORD:
        raise ValueError("Senha de administração inválida.")


def validar_senha_reset(senha_admin):
    if (senha_admin or "").strip() != RESET_PASSWORD:
        raise ValueError("Senha de reset inválida.")


def obter_totais_financeiro(data_operacao=None):
    data_operacao = normalizar_data_operacao(data_operacao)
    entradas = query_one(
        "SELECT COALESCE(SUM(valor), 0) AS total FROM fluxo_caixa WHERE tipo = 'ENTRADA' AND data_operacao = ?",
        (data_operacao,),
    )["total"]
    saidas = query_one(
        "SELECT COALESCE(SUM(valor), 0) AS total FROM fluxo_caixa WHERE tipo = 'SAIDA' AND data_operacao = ?",
        (data_operacao,),
    )["total"]
    return {
        "entradas": float(entradas),
        "saidas": float(saidas),
        "saldo": float(entradas) - float(saidas),
    }


def cadastrar_produto(nome, preco_custo, preco_venda, estoque):
    nome = (nome or "").strip()

    if not nome:
        raise ValueError("Informe o nome do produto.")

    try:
        preco_custo = float(str(preco_custo).replace(",", "."))
        preco_venda = float(str(preco_venda).replace(",", "."))
        estoque = int(estoque)
    except (TypeError, ValueError):
        raise ValueError("Preencha os valores do produto corretamente.")

    if preco_custo < 0 or preco_venda < 0 or estoque < 0:
        raise ValueError("Preço e estoque não podem ser negativos.")

    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO produtos (nome, preco_custo, preco_venda, estoque)
            VALUES (?, ?, ?, ?)
            """,
            (nome, preco_custo, preco_venda, estoque),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Já existe um produto com esse nome.")


def atualizar_produto(produto_id, nome, preco_custo, preco_venda, estoque):
    try:
        produto_id = int(produto_id)
    except (TypeError, ValueError):
        raise ValueError("Produto inválido.")

    nome = (nome or "").strip()

    if not nome:
        raise ValueError("Informe o nome do produto.")

    try:
        preco_custo = float(str(preco_custo).replace(",", "."))
        preco_venda = float(str(preco_venda).replace(",", "."))
        estoque = int(estoque)
    except (TypeError, ValueError):
        raise ValueError("Preencha os valores do produto corretamente.")

    if preco_custo < 0 or preco_venda < 0 or estoque < 0:
        raise ValueError("Preço e estoque não podem ser negativos.")

    db = get_db()
    produto = db.execute("SELECT id FROM produtos WHERE id = ?", (produto_id,)).fetchone()

    if not produto:
        raise ValueError("Produto não encontrado.")

    try:
        db.execute(
            """
            UPDATE produtos
            SET nome = ?, preco_custo = ?, preco_venda = ?, estoque = ?
            WHERE id = ?
            """,
            (nome, preco_custo, preco_venda, estoque, produto_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Já existe um produto com esse nome.")


def excluir_produto(produto_id):
    try:
        produto_id = int(produto_id)
    except (TypeError, ValueError):
        raise ValueError("Produto inválido.")

    db = get_db()
    produto = db.execute(
        "SELECT id, nome FROM produtos WHERE id = ?",
        (produto_id,),
    ).fetchone()

    if not produto:
        raise ValueError("Produto não encontrado.")

    venda_relacionada = db.execute(
        "SELECT 1 FROM itens_venda WHERE produto_id = ? LIMIT 1",
        (produto_id,),
    ).fetchone()

    if venda_relacionada:
        raise ValueError("Este produto já possui vendas registradas e não pode ser excluído.")

    db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    db.commit()


def registrar_venda(itens, forma_pagamento):
    forma_pagamento = (forma_pagamento or "").strip()

    if forma_pagamento not in FORMAS_PAGAMENTO:
        raise ValueError("Forma de pagamento inválida.")

    if not itens or not isinstance(itens, list):
        raise ValueError("Adicione ao menos um item na venda.")

    db = get_db()
    itens_processados = []
    total = 0.0
    data_operacao = obter_data_caixa_atual()

    try:
        db.execute("BEGIN")

        for item in itens:
            produto_id = int(item.get("produto_id", 0))
            quantidade = int(item.get("quantidade", 0))

            if produto_id <= 0 or quantidade <= 0:
                raise ValueError("Itens da venda inválidos.")

            produto = db.execute(
                """
                SELECT id, nome, preco_venda, estoque
                FROM produtos
                WHERE id = ?
                """,
                (produto_id,),
            ).fetchone()

            if not produto:
                raise ValueError(f"Produto ID {produto_id} não encontrado.")

            if produto["estoque"] < quantidade:
                raise ValueError(
                    f"Estoque insuficiente para '{produto['nome']}'. Disponível: {produto['estoque']}."
                )

            preco_unitario = float(produto["preco_venda"])
            subtotal = round(preco_unitario * quantidade, 2)
            total += subtotal

            itens_processados.append(
                {
                    "produto_id": produto["id"],
                    "nome": produto["nome"],
                    "quantidade": quantidade,
                    "preco_unitario": preco_unitario,
                    "subtotal": subtotal,
                }
            )

        total = round(total, 2)

        cur = db.execute(
            """
            INSERT INTO vendas (total, forma_pagamento, data_operacao)
            VALUES (?, ?, ?)
            """,
            (total, forma_pagamento, data_operacao),
        )
        venda_id = cur.lastrowid

        for item in itens_processados:
            db.execute(
                """
                INSERT INTO itens_venda (
                    venda_id, produto_id, quantidade, preco_unitario, subtotal
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    venda_id,
                    item["produto_id"],
                    item["quantidade"],
                    item["preco_unitario"],
                    item["subtotal"],
                ),
            )
            db.execute(
                """
                UPDATE produtos
                SET estoque = estoque - ?
                WHERE id = ?
                """,
                (item["quantidade"], item["produto_id"]),
            )

        db.execute(
            """
            INSERT INTO fluxo_caixa (tipo, descricao, valor, referencia_id, data_operacao)
            VALUES ('ENTRADA', ?, ?, ?, ?)
            """,
            (f"Venda #{venda_id}", total, venda_id, data_operacao),
        )

        db.commit()
        return venda_id

    except Exception:
        db.rollback()
        raise


def adicionar_saida(descricao, valor):
    descricao = (descricao or "").strip()

    if not descricao:
        raise ValueError("Informe a descrição da saída.")

    try:
        valor = float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError("Informe um valor válido para a saída.")

    if valor <= 0:
        raise ValueError("O valor da saída deve ser maior que zero.")

    db = get_db()
    db.execute(
        """
        INSERT INTO fluxo_caixa (tipo, descricao, valor, data_operacao)
        VALUES ('SAIDA', ?, ?, ?)
        """,
        (descricao, valor, obter_data_caixa_atual()),
    )
    db.commit()


def atualizar_lancamento_financeiro(lancamento_id, descricao, valor, forma_pagamento, senha_admin):
    validar_senha_admin(senha_admin)

    try:
        lancamento_id = int(lancamento_id)
    except (TypeError, ValueError):
        raise ValueError("Lançamento inválido.")

    descricao = (descricao or "").strip()
    if not descricao:
        raise ValueError("Informe a descrição do lançamento.")

    try:
        valor = float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError("Informe um valor válido para o lançamento.")

    if valor <= 0:
        raise ValueError("O valor do lançamento deve ser maior que zero.")

    db = get_db()
    lancamento = db.execute(
        """
        SELECT id, tipo, referencia_id
        FROM fluxo_caixa
        WHERE id = ?
        """,
        (lancamento_id,),
    ).fetchone()

    if not lancamento:
        raise ValueError("Lançamento não encontrado.")

    forma_pagamento = (forma_pagamento or "").strip()

    try:
        db.execute("BEGIN")

        if lancamento["tipo"] == "ENTRADA":
            if forma_pagamento not in FORMAS_PAGAMENTO:
                raise ValueError("Selecione uma forma de pagamento válida.")

            if lancamento["referencia_id"]:
                db.execute(
                    """
                    UPDATE vendas
                    SET total = ?, forma_pagamento = ?
                    WHERE id = ?
                    """,
                    (valor, forma_pagamento, lancamento["referencia_id"]),
                )

        db.execute(
            """
            UPDATE fluxo_caixa
            SET descricao = ?, valor = ?
            WHERE id = ?
            """,
            (descricao, valor, lancamento_id),
        )

        db.commit()
    except Exception:
        db.rollback()
        raise


def excluir_lancamento_financeiro(lancamento_id, senha_admin):
    validar_senha_admin(senha_admin)

    try:
        lancamento_id = int(lancamento_id)
    except (TypeError, ValueError):
        raise ValueError("Lançamento inválido.")

    db = get_db()
    lancamento = db.execute(
        """
        SELECT id, tipo, referencia_id
        FROM fluxo_caixa
        WHERE id = ?
        """,
        (lancamento_id,),
    ).fetchone()

    if not lancamento:
        raise ValueError("Lançamento não encontrado.")

    try:
        db.execute("BEGIN")

        if lancamento["tipo"] == "ENTRADA" and lancamento["referencia_id"]:
            itens_venda = db.execute(
                """
                SELECT produto_id, quantidade
                FROM itens_venda
                WHERE venda_id = ?
                """,
                (lancamento["referencia_id"],),
            ).fetchall()

            for item in itens_venda:
                db.execute(
                    """
                    UPDATE produtos
                    SET estoque = estoque + ?
                    WHERE id = ?
                    """,
                    (item["quantidade"], item["produto_id"]),
                )

            db.execute("DELETE FROM vendas WHERE id = ?", (lancamento["referencia_id"],))

        db.execute("DELETE FROM fluxo_caixa WHERE id = ?", (lancamento_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


def registrar_fontes_pdf():
    global PDF_FONT_REGULAR, PDF_FONT_BOLD, PDF_FONTS_READY

    if PDF_FONTS_READY:
        return

    candidatos = [
        (BASE_DIR / "static" / "fonts" / "DejaVuSans.ttf", BASE_DIR / "static" / "fonts" / "DejaVuSans-Bold.ttf"),
        (Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf", Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arialbd.ttf"),
    ]

    for fonte_regular, fonte_bold in candidatos:
        if not (fonte_regular.exists() and fonte_bold.exists()):
            continue

        try:
            pdfmetrics.registerFont(TTFont("ConfeitariaRegular", str(fonte_regular)))
            pdfmetrics.registerFont(TTFont("ConfeitariaBold", str(fonte_bold)))
            PDF_FONT_REGULAR = "ConfeitariaRegular"
            PDF_FONT_BOLD = "ConfeitariaBold"
            break
        except Exception:
            continue

    PDF_FONTS_READY = True


def desenhar_cabecalho_pdf(pdf, largura, altura, gerado_em):
    if LOGO_PATH.exists():
        logo = ImageReader(str(LOGO_PATH))
        pdf.drawImage(logo, 40, altura - 120, width=175, height=72, preserveAspectRatio=True, mask="auto")

    pdf.setFillColor(BRAND_PRIMARY)
    pdf.setFont(PDF_FONT_BOLD, 18)
    pdf.drawRightString(largura - 40, altura - 52, "Relatório Financeiro")

    pdf.setFillColor(BRAND_MUTED)
    pdf.setFont(PDF_FONT_REGULAR, 10)
    pdf.drawRightString(largura - 40, altura - 70, f"Gerado em: {gerado_em}")

    pdf.setStrokeColor(BRAND_PRIMARY)
    pdf.setLineWidth(1)
    pdf.line(40, altura - 130, largura - 40, altura - 130)
    return altura - 160


def desenhar_texto_quebrado(pdf, texto, x, y, largura_maxima, fonte=None, tamanho=10, cor=colors.black, espacamento=15):
    fonte = fonte or PDF_FONT_REGULAR
    pdf.setFont(fonte, tamanho)
    pdf.setFillColor(cor)
    linhas = simpleSplit(str(texto), fonte, tamanho, largura_maxima)

    for linha in linhas:
        pdf.drawString(x, y, linha)
        y -= espacamento

    return y


def gerar_relatorio_financeiro_pdf(data_operacao=None):
    data_operacao = normalizar_data_operacao(data_operacao)
    lancamentos = obter_fluxo_caixa(data_operacao)
    totais = obter_totais_financeiro(data_operacao)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    registrar_fontes_pdf()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4
    y = desenhar_cabecalho_pdf(pdf, largura, altura, agora)

    pdf.setFillColor(BRAND_TEXT)
    pdf.setFont(PDF_FONT_BOLD, 11)
    pdf.drawString(40, y, f"Caixa do dia: {formatar_data_operacao(data_operacao)}")
    y -= 20
    pdf.drawString(40, y, f"Total de entradas: {moeda_pdf(totais['entradas'])}")
    y -= 20
    pdf.drawString(40, y, f"Total de saídas: {moeda_pdf(totais['saidas'])}")
    y -= 20
    pdf.drawString(40, y, f"Saldo atual: {moeda_pdf(totais['saldo'])}")
    y -= 32

    pdf.setFillColor(BRAND_PRIMARY)
    pdf.setFont(PDF_FONT_BOLD, 12)
    pdf.drawString(40, y, "Extrato de caixa")
    y -= 16

    pdf.setStrokeColor(BRAND_PRIMARY)
    pdf.line(40, y, largura - 40, y)
    y -= 20

    if not lancamentos:
        pdf.setFillColor(BRAND_TEXT)
        pdf.setFont(PDF_FONT_REGULAR, 10)
        pdf.drawString(40, y, "Nenhum lançamento encontrado.")
    else:
        for item in lancamentos:
            if y < 110:
                pdf.showPage()
                y = desenhar_cabecalho_pdf(pdf, largura, altura, agora)

            valor = (
                f"+ {moeda_pdf(item['valor'])}"
                if item["tipo"] == "ENTRADA"
                else f"- {moeda_pdf(item['valor'])}"
            )

            y = desenhar_texto_quebrado(pdf, f"{formatar_datahora(item['created_at'])} | {item['tipo']} | {valor}", 40, y, 500, fonte=PDF_FONT_BOLD, tamanho=10, cor=BRAND_TEXT)
            y = desenhar_texto_quebrado(pdf, f"Descrição: {item['descricao']}", 40, y, 500, fonte=PDF_FONT_REGULAR, tamanho=10, cor=colors.black)
            y = desenhar_texto_quebrado(pdf, f"Pagamento: {item['forma_pagamento'] or '-'}", 40, y, 500, fonte=PDF_FONT_REGULAR, tamanho=10, cor=colors.black)
            pdf.setStrokeColor(BRAND_SECONDARY)
            pdf.line(40, y + 3, largura - 40, y + 3)
            y -= 16

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


@app.route("/")
def index():
    return redirect(url_for("pdv"))


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/produtos", methods=["GET", "POST"])
def produtos():
    if request.method == "POST":
        try:
            cadastrar_produto(
                nome=request.form.get("nome"),
                preco_custo=request.form.get("preco_custo"),
                preco_venda=request.form.get("preco_venda"),
                estoque=request.form.get("estoque"),
            )
            flash("Produto cadastrado com sucesso.", "success")
        except ValueError as e:
            flash(str(e), "danger")
        return redirect(url_for("produtos"))

    produto_edicao = None
    produto_edicao_id = request.args.get("editar", type=int)
    if produto_edicao_id:
        produto_edicao = obter_produto_por_id(produto_edicao_id)
        if not produto_edicao:
            flash("Produto para edição não encontrado.", "danger")
            return redirect(url_for("produtos"))

    return render_template(
        "produtos.html",
        produtos=obter_produtos(),
        produto_edicao=produto_edicao,
    )


@app.route("/produtos/<int:produto_id>/editar", methods=["POST"])
def editar_produto_route(produto_id):
    try:
        atualizar_produto(
            produto_id=produto_id,
            nome=request.form.get("nome"),
            preco_custo=request.form.get("preco_custo"),
            preco_venda=request.form.get("preco_venda"),
            estoque=request.form.get("estoque"),
        )
        flash("Produto atualizado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("produtos", editar=produto_id))

    return redirect(url_for("produtos"))


@app.route("/produtos/<int:produto_id>/excluir", methods=["POST"])
def excluir_produto_route(produto_id):
    try:
        excluir_produto(produto_id)
        flash("Produto excluído com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("produtos"))


@app.route("/pdv")
def pdv():
    return render_template(
        "pdv.html",
        produtos=obter_produtos(),
        formas_pagamento=FORMAS_PAGAMENTO,
    )


@app.route("/vendas", methods=["POST"])
def vendas():
    try:
        itens = json.loads(request.form.get("itens_json", "[]"))
        forma_pagamento = request.form.get("forma_pagamento")
        venda_id = registrar_venda(itens, forma_pagamento)
        flash(f"Venda #{venda_id} registrada com sucesso.", "success")
    except (ValueError, json.JSONDecodeError) as e:
        flash(str(e), "danger")

    return redirect(url_for("pdv"))


@app.route("/financeiro")
def financeiro():
    data_caixa_atual = obter_data_caixa_atual()
    data_consulta = normalizar_data_operacao(request.args.get("data") or data_caixa_atual)
    lancamento_edicao = None
    lancamento_edicao_id = request.args.get("editar", type=int)

    if lancamento_edicao_id:
        lancamento_edicao = obter_lancamento_por_id(lancamento_edicao_id)
        if not lancamento_edicao:
            flash("Lançamento para edição não encontrado.", "danger")
            return redirect(url_for("financeiro", data=data_consulta))
        data_consulta = lancamento_edicao["data_operacao"]

    visualizando_historico = data_consulta != data_caixa_atual
    proxima_data = (datetime.strptime(data_caixa_atual, "%Y-%m-%d").date() + timedelta(days=1)).isoformat()

    return render_template(
        "financeiro.html",
        lancamentos=obter_fluxo_caixa(data_consulta),
        totais=obter_totais_financeiro(data_consulta),
        formas_pagamento=FORMAS_PAGAMENTO,
        lancamento_edicao=lancamento_edicao,
        data_caixa_atual=data_caixa_atual,
        data_consulta=data_consulta,
        data_caixa_atual_formatada=formatar_data_operacao(data_caixa_atual),
        data_consulta_formatada=formatar_data_operacao(data_consulta),
        proxima_data_formatada=formatar_data_operacao(proxima_data),
        visualizando_historico=visualizando_historico,
    )


@app.route("/financeiro/proximo-dia", methods=["POST"])
def financeiro_proximo_dia():
    try:
        nova_data = avancar_data_caixa(request.form.get("senha_admin"))
        flash(f"Caixa reiniciado para o dia {formatar_data_operacao(nova_data)}.", "success")
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("financeiro"))

    return redirect(url_for("financeiro"))


@app.route("/financeiro/reset", methods=["POST"])
def financeiro_reset():
    try:
        resetar_programa(request.form.get("senha_admin_reset"))
        flash("Sistema resetado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("financeiro"))


@app.route("/financeiro/saida", methods=["POST"])
def financeiro_saida():
    try:
        adicionar_saida(descricao=request.form.get("descricao"), valor=request.form.get("valor"))
        flash("Saída lançada com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("financeiro"))


@app.route("/financeiro/<int:lancamento_id>/editar", methods=["POST"])
def financeiro_editar(lancamento_id):
    lancamento = obter_lancamento_por_id(lancamento_id)
    data_retorno = lancamento["data_operacao"] if lancamento else obter_data_caixa_atual()
    try:
        atualizar_lancamento_financeiro(
            lancamento_id=lancamento_id,
            descricao=request.form.get("descricao"),
            valor=request.form.get("valor"),
            forma_pagamento=request.form.get("forma_pagamento"),
            senha_admin=request.form.get("senha_admin"),
        )
        flash("Lançamento atualizado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("financeiro", data=data_retorno, editar=lancamento_id))
    return redirect(url_for("financeiro", data=data_retorno))


@app.route("/financeiro/<int:lancamento_id>/excluir", methods=["POST"])
def financeiro_excluir(lancamento_id):
    lancamento = obter_lancamento_por_id(lancamento_id)
    data_retorno = lancamento["data_operacao"] if lancamento else obter_data_caixa_atual()
    try:
        excluir_lancamento_financeiro(lancamento_id=lancamento_id, senha_admin=request.form.get("senha_admin"))
        flash("Lançamento excluído com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("financeiro", data=data_retorno, editar=lancamento_id))
    return redirect(url_for("financeiro", data=data_retorno))


@app.route("/financeiro/pdf")
def financeiro_pdf():
    data_consulta = normalizar_data_operacao(request.args.get("data") or obter_data_caixa_atual())
    pdf = gerar_relatorio_financeiro_pdf(data_consulta)
    nome_arquivo = f"relatorio_financeiro_{data_consulta.replace('-', '')}.pdf"
    return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'})


@app.route("/api/produtos", methods=["GET", "POST"])
def api_produtos():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        try:
            cadastrar_produto(
                nome=payload.get("nome"),
                preco_custo=payload.get("preco_custo"),
                preco_venda=payload.get("preco_venda"),
                estoque=payload.get("estoque"),
            )
            return jsonify({"mensagem": "Produto cadastrado com sucesso."}), 201
        except ValueError as e:
            return jsonify({"erro": str(e)}), 400

    produtos = [row_to_dict(row) for row in obter_produtos()]
    return jsonify(produtos)


@app.route("/api/vendas", methods=["POST"])
def api_vendas():
    payload = request.get_json(silent=True) or {}
    try:
        venda_id = registrar_venda(
            itens=payload.get("itens", []),
            forma_pagamento=payload.get("forma_pagamento"),
        )
        return jsonify({"mensagem": "Venda registrada com sucesso.", "venda_id": venda_id}), 201
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/api/fluxo-caixa", methods=["GET"])
def api_fluxo_caixa():
    lancamentos = [row_to_dict(row) for row in obter_fluxo_caixa()]
    totais = obter_totais_financeiro()
    return jsonify({"lancamentos": lancamentos, "totais": totais})


with app.app_context():
    init_db()


if __name__ == "__main__":
    url_inicial = "http://127.0.0.1:5000/pdv"
    threading.Timer(1.0, webbrowser.open, args=(url_inicial,)).start()
    app.run(host="127.0.0.1", port=5000, debug=False)



