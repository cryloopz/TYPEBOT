import tkinter as tk
from tkinter import messagebox
from pynput.keyboard import Controller, Key, GlobalHotKeys
from collections import Counter
import json
import os
import queue
import random
import re
import threading
import time
import unicodedata

# ---------- Atalhos globais (funcionam mesmo com o app minimizado) ----------
ATALHO_INICIAR = "<f8>"
ATALHO_PARAR = "<f9>"
NOME_INICIAR = ATALHO_INICIAR.strip("<>").upper()
NOME_PARAR = ATALHO_PARAR.strip("<>").upper()

# Caracteres invisíveis que costumam vir junto quando se copia texto de páginas
INVISIVEIS = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD}

# Tipos de quebra de linha (como números, para não haver caracteres especiais no código)
QUEBRAS = {10, 13, 11, 12, 133, 8232, 8233}
REGEX_QUEBRAS = re.compile(" *[" + "".join(re.escape(chr(n)) for n in QUEBRAS) + "]+ *")


def normalizar_texto(texto):
    """Deixa o texto só com caracteres "normais" e devolve (texto_limpo, relatorio).

    - remove caracteres invisíveis (largura zero, hífen suave, BOM)
    - troca qualquer tipo de espaço especial (nbsp, espaço fino etc.) e tab por espaço comum
    - troca quebras de linha por um único espaço (texto de teste de digitação é uma linha só)
    - remove espaços no começo e no fim
    Espaços duplicados que já existiam no texto NÃO são mexidos.
    """
    achados = Counter()

    for c in texto:
        if ord(c) in INVISIVEIS:
            achados[unicodedata.name(c, f"U+{ord(c):04X}")] += 1
        elif c == "\t":
            achados["TAB"] += 1
        elif ord(c) in QUEBRAS:
            achados["QUEBRA DE LINHA"] += 1
        elif unicodedata.category(c) == "Zs" and c != " ":
            achados[unicodedata.name(c, f"U+{ord(c):04X}")] += 1

    limpo = "".join(c for c in texto if ord(c) not in INVISIVEIS)
    limpo = "".join(" " if (unicodedata.category(c) == "Zs" or c == "\t") else c for c in limpo)
    limpo = REGEX_QUEBRAS.sub(" ", limpo)
    limpo = limpo.strip()

    return limpo, achados


def comparar(ref, digitado):
    """Devolve (acertos, tem_erro): quantos caracteres batem desde o início e se houve divergência."""
    i = 0
    limite = min(len(ref), len(digitado))
    while i < limite and ref[i] == digitado[i]:
        i += 1
    return i, i < len(digitado)


def descrever_caractere(c):
    """Nome legível de um caractere (para mostrar exatamente o que divergiu)."""
    if c is None:
        return "(nada, texto a mais)"
    cp = ord(c)
    hexa = f"U+{cp:04X}"
    if c == " ":
        return "espaço comum"
    if c == "\n":
        return "Enter (quebra de linha)"
    if c == "\t":
        return "Tab"
    if cp == 0xA0:
        return f"espaço não separável ({hexa})"
    if c.isspace() or cp in INVISIVEIS:
        return f"caractere invisível ({hexa})"
    return f"'{c}' ({hexa})"


def metricas(ref, acertos, erros, segundos):
    """TPM (toques/min), PPM (palavras/min) e precisão (%) de uma tentativa de treino."""
    minutos = max(segundos, 0.001) / 60
    tpm = acertos / minutos
    palavras = len(ref[:acertos].split())
    ppm = palavras / minutos
    total = acertos + erros
    precisao = 100.0 if total == 0 else 100.0 * acertos / total
    return {"tpm": tpm, "ppm": ppm, "precisao": precisao}


# ---------- Área de treino: textos por nível de dificuldade ----------
NIVEIS = ("Fácil", "Médio", "Difícil", "Extremo")

TEXTOS_TREINO = {
    "Fácil": [
        "O dia está bonito e o céu está azul. Vamos passear no parque e brincar com o cachorro.",
        "Eu gosto de ler um livro antes de dormir. A casa fica quieta e a noite passa devagar.",
        "O gato subiu no sofá e dormiu. A chuva caiu fina e o vento ficou calmo.",
        "Maria comprou pão e leite na padaria. Depois voltou para casa e fez o café.",
    ],
    "Médio": [
        "Aprender a digitar rápido exige paciência e prática diária. No começo, é normal errar bastante, mas com o tempo os dedos aprendem o caminho sozinhos. O segredo é manter a calma, olhar para a tela e não para o teclado.",
        "A cidade acorda cedo: o padeiro abre a loja, os ônibus enchem as ruas e o cheiro de café toma conta da esquina. Quem passa apressado quase nunca percebe como o dia começa devagar.",
        "Todo projeto grande começa com um passo pequeno. Primeiro, escolhemos o objetivo; depois, dividimos o trabalho em tarefas simples e vamos concluindo uma por uma, sem pressa e sem desistir.",
        "Na biblioteca do bairro, as crianças escolhem histórias de aventura, enquanto os adultos procuram receitas, mapas e livros de ciência. O silêncio ali tem um som próprio, feito de páginas viradas.",
    ],
    "Difícil": [
        "Será que dá tempo? Sim... talvez; quem sabe! Ele disse: \"Não esqueça o guarda-chuva (nem o casaco)\", mas ela respondeu: 'Pode deixar, já está na mochila'. Afinal, quem espera sempre alcança - ou quase sempre.",
        "Atenção: o café, o chá e o suco (de laranja, de uva ou de maçã) custam pouco; porém, a água - gelada ou natural - é cortesia da casa. Quer pedir agora? Fale com o garçom, por favor!",
        "Na reunião de hoje, o João perguntou: \"Quem vai revisar o relatório?\" Ninguém respondeu; então, a Marta, sem hesitar, disse: 'Eu reviso, mas preciso de dois dias (no mínimo)'. Combinado? Combinado!",
        "Há momentos em que a pressa atrapalha: erra-se a vírgula, esquece-se o ponto; no fim, o texto sai torto. Respire, releia, corrija - e só depois envie. Parece simples, não é? Mas exige hábito.",
    ],
    "Extremo": [
        "Pedido #4521: 3 camisetas (M) a R$ 49,90 cada + frete de R$ 12,00 = R$ 161,70. Pagamento em 2x de R$ 80,85 ou à vista com 5% de desconto. Dúvidas? Escreva para contato@loja.com.br até 30/11/2026.",
        "Código: M@th#2026! (não compartilhe). O servidor 192.168.0.10 respondeu em 35 ms; a taxa de erro caiu de 12,5% para 0,8% após a atualização v2.3.1 de 05/11.",
        "Receita: misture 250 g de farinha, 2 ovos, 1/2 xícara de açúcar e 200 ml de leite; asse a 180 graus por 35 min. Rende ~12 porções (cerca de R$ 0,75 cada) - ótimo para o café da tarde & para o lanche!",
        "Em 2026, o time marcou 3 gols no primeiro tempo e 2 no segundo; a torcida (cerca de 45.000 pessoas) gritou: \"É campeão!\" Resultado final: 5 x 2 - placar histórico, não é? Veja em www.exemplo.com.br/jogo?id=77&lang=pt.",
    ],
}


def caminho_recordes():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "typebot_recordes.json")


def carregar_recordes():
    try:
        with open(caminho_recordes(), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return {k: float(v) for k, v in dados.items() if k in NIVEIS}
    except Exception:
        return {}


def salvar_recordes(recordes):
    try:
        with open(caminho_recordes(), "w", encoding="utf-8") as f:
            json.dump(recordes, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------- Visual ----------
COR_FUNDO = "#0f172a"      # fundo da janela
COR_CARD = "#1e293b"       # cartões
COR_CAMPO = "#0b1220"      # área de texto
COR_BORDA = "#334155"
COR_TEXTO = "#e2e8f0"
COR_MUTED = "#94a3b8"
COR_DESTAQUE = "#6366f1"   # botão principal
COR_DESTAQUE_HOVER = "#818cf8"
COR_SEC = "#334155"        # botão secundário
COR_SEC_HOVER = "#475569"
COR_PARAR = "#dc2626"      # botão parar
COR_PARAR_HOVER = "#ef4444"
COR_DESATIVADO = "#273244"
COR_OK = "#22c55e"
COR_ERRO = "#f87171"

FONTE = "Segoe UI"


class BotaoRedondo(tk.Canvas):
    """Botão com cantos arredondados, efeito ao passar o mouse e estado desativado."""

    def __init__(self, parent, texto, comando, cor, cor_hover,
                 largura=180, altura=46, raio=16, fonte=None, fundo=COR_FUNDO):
        super().__init__(parent, width=largura, height=altura, bg=fundo,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.comando = comando
        self.cor = cor
        self.cor_hover = cor_hover
        self.largura = largura
        self.altura = altura
        self.raio = raio
        self.ativo = True

        self.forma = self._forma(cor)
        self.rotulo = self.create_text(largura // 2, altura // 2, text=texto, fill="white",
                                       font=fonte or (FONTE, 11, "bold"))

        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._sair)
        self.bind("<ButtonPress-1>", self._apertar)
        self.bind("<ButtonRelease-1>", self._soltar)

    def _forma(self, cor):
        r, w, h = self.raio, self.largura, self.altura
        pontos = [r, 0, r, 0, w - r, 0, w - r, 0, w, 0,
                  w, r, w, r, w, h - r, w, h - r, w, h,
                  w - r, h, w - r, h, r, h, r, h, 0, h,
                  0, h - r, 0, h - r, 0, r, 0, r, 0, 0]
        return self.create_polygon(pontos, smooth=True, fill=cor, outline=cor)

    def _pintar(self, cor):
        self.itemconfig(self.forma, fill=cor, outline=cor)

    def _entrar(self, _):
        if self.ativo:
            self._pintar(self.cor_hover)

    def _sair(self, _):
        self._pintar(self.cor if self.ativo else COR_DESATIVADO)

    def _apertar(self, _):
        if self.ativo:
            self._pintar(self.cor)

    def _soltar(self, e):
        if self.ativo and 0 <= e.x <= self.largura and 0 <= e.y <= self.altura:
            self._pintar(self.cor_hover)
            self.comando()

    def ativar(self, sim):
        self.ativo = sim
        self._pintar(self.cor if sim else COR_DESATIVADO)
        self.itemconfig(self.rotulo, fill="white" if sim else COR_MUTED)
        self.config(cursor="hand2" if sim else "arrow")

    def definir_cores(self, cor, cor_hover):
        self.cor = cor
        self.cor_hover = cor_hover
        self._pintar(cor if self.ativo else COR_DESATIVADO)


class JanelaTeste(tk.Toplevel):
    """Janela de teste: o robô digita aqui e ela compara com o texto, caractere por caractere."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("TYPEBOT - Área de teste")
        self.configure(bg=COR_FUNDO)
        self.minsize(560, 560)
        x = app.root.winfo_x() + 40
        y = app.root.winfo_y() + 40
        self.geometry(f"720x660+{x}+{y}")

        self.ref = ""
        self.inicio = None
        self.erros = 0
        self.em_erro = False
        self.fim = False
        self.ultimo = ""
        self.ativo = True
        self._job = None

        self._montar()
        self.protocol("WM_DELETE_WINDOW", self.fechar)
        self.preparar()
        self._job = self.after(30, self._loop)

    def _montar(self):
        tk.Label(self, text="ÁREA DE TESTE", bg=COR_FUNDO, fg=COR_TEXTO,
                 font=(FONTE, 18, "bold")).pack(anchor="w", padx=24, pady=(18, 2))
        tk.Label(self, text=f"Aperte {NOME_INICIAR}: o robô digita o texto do TYPEBOT na caixa "
                            "de baixo e aqui aparece se saiu exatamente igual.",
                 bg=COR_FUNDO, fg=COR_MUTED, font=(FONTE, 10), wraplength=660,
                 justify="left").pack(anchor="w", padx=24, pady=(0, 10))

        # Texto original
        card1 = tk.Frame(self, bg=COR_CARD, highlightthickness=1,
                         highlightbackground=COR_BORDA, padx=14, pady=10)
        card1.pack(fill="x", padx=24, pady=(0, 10))
        tk.Label(card1, text="TEXTO ORIGINAL", bg=COR_CARD, fg=COR_TEXTO,
                 font=(FONTE, 9, "bold")).pack(anchor="w", pady=(0, 6))
        self.ref_text = tk.Text(card1, wrap="word", height=6, bg=COR_CAMPO, fg=COR_MUTED,
                                relief="flat", bd=0, padx=10, pady=8, font=(FONTE, 11),
                                state="disabled", highlightthickness=0)
        self.ref_text.pack(fill="x")
        self.ref_text.tag_configure("ok", foreground=COR_OK)
        self.ref_text.tag_configure("bad", background=COR_PARAR, foreground="white")
        self.ref_text.tag_configure("cur", foreground=COR_TEXTO, underline=True)

        # Onde o robô digita
        card2 = tk.Frame(self, bg=COR_CARD, highlightthickness=1,
                         highlightbackground=COR_BORDA, padx=14, pady=10)
        card2.pack(fill="both", expand=True, padx=24, pady=(0, 10))
        tk.Label(card2, text="O QUE FOI DIGITADO (o robô escreve aqui)", bg=COR_CARD,
                 fg=COR_TEXTO, font=(FONTE, 9, "bold")).pack(anchor="w", pady=(0, 6))
        self.entrada = tk.Text(card2, wrap="word", height=6, bg=COR_CAMPO, fg=COR_TEXTO,
                               insertbackground="white", relief="flat", bd=0, padx=10, pady=8,
                               font=(FONTE, 11), highlightthickness=1,
                               highlightbackground=COR_BORDA, highlightcolor=COR_DESTAQUE)
        self.entrada.pack(fill="both", expand=True)

        # Números
        linha = tk.Frame(self, bg=COR_FUNDO)
        linha.pack(fill="x", padx=24, pady=(0, 8))
        self.v_acertos = self._stat(linha, "ACERTOS")
        self.v_erros = self._stat(linha, "ERROS")
        self.v_prog = self._stat(linha, "PROGRESSO")
        self.v_tempo = self._stat(linha, "TEMPO")

        self.resultado = tk.Label(self, text="", bg=COR_FUNDO, fg=COR_MUTED,
                                  font=(FONTE, 11, "bold"), wraplength=660, justify="left")
        self.resultado.pack(anchor="w", padx=24, pady=(0, 8))

        botoes = tk.Frame(self, bg=COR_FUNDO)
        botoes.pack(pady=(0, 16))
        BotaoRedondo(botoes, "REINICIAR", lambda: self.preparar(), COR_SEC, COR_SEC_HOVER,
                     largura=160, altura=40, fonte=(FONTE, 10, "bold")).pack(side="left", padx=6)
        BotaoRedondo(botoes, "FECHAR", self.fechar, COR_SEC, COR_SEC_HOVER,
                     largura=160, altura=40, fonte=(FONTE, 10, "bold")).pack(side="left", padx=6)

    def _stat(self, parent, titulo):
        quadro = tk.Frame(parent, bg=COR_CARD, highlightthickness=1,
                          highlightbackground=COR_BORDA, padx=10, pady=8)
        quadro.pack(side="left", expand=True, fill="x", padx=4)
        valor = tk.Label(quadro, text="0", bg=COR_CARD, fg=COR_TEXTO, font=(FONTE, 15, "bold"))
        valor.pack()
        tk.Label(quadro, text=titulo, bg=COR_CARD, fg=COR_MUTED, font=(FONTE, 8)).pack()
        return valor

    # ----- controle -----
    def preparar(self, texto=None, forcar_foco=False):
        """Zera o teste e carrega o texto do TYPEBOT (já limpo, igual ao que o robô vai digitar)."""
        if texto is None:
            texto, _ = normalizar_texto(self.app.text_entry.get("1.0", "end-1c"))
        self.ref = texto
        self.entrada.delete("1.0", "end")
        self.inicio = None
        self.erros = 0
        self.em_erro = False
        self.fim = False
        self.ultimo = ""
        self._atualizar(0, False, "")
        if forcar_foco:
            self.lift()
            self.entrada.focus_force()

    def fechar(self):
        self.ativo = False
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self.app.teste = None
        self.destroy()

    def _loop(self):
        if not self.ativo:
            return
        valor = self.entrada.get("1.0", "end-1c")
        if valor != self.ultimo:
            self.ultimo = valor
            self._atualizar(*comparar(self.ref, valor), valor)
        elif self.inicio is not None and not self.fim:
            self.v_tempo.config(text=f"{time.perf_counter() - self.inicio:.1f}s")
        self._job = self.after(30, self._loop)

    def _atualizar(self, acertos, tem_erro, valor):
        if self.inicio is None and valor:
            self.inicio = time.perf_counter()
        if tem_erro and not self.em_erro:
            self.erros += 1
        self.em_erro = tem_erro

        # Texto original colorido: verde = certo, vermelho = onde errou
        self.ref_text.config(state="normal")
        self.ref_text.delete("1.0", "end")
        self.ref_text.insert("1.0", self.ref)
        if acertos:
            self.ref_text.tag_add("ok", "1.0", f"1.0+{acertos}c")
        if tem_erro and acertos < len(self.ref):
            self.ref_text.tag_add("bad", f"1.0+{acertos}c", f"1.0+{acertos + 1}c")
        elif not tem_erro and acertos < len(self.ref):
            self.ref_text.tag_add("cur", f"1.0+{acertos}c", f"1.0+{acertos + 1}c")
        self.ref_text.config(state="disabled")

        self.v_acertos.config(text=str(acertos))
        self.v_erros.config(text=str(self.erros))
        self.v_prog.config(text=f"{acertos} / {len(self.ref)}")

        if not self.ref:
            self.resultado.config(text="Não há texto no TYPEBOT para comparar. Cole um texto lá e clique em REINICIAR.",
                                  fg=COR_ERRO)
        elif tem_erro:
            esperado = self.ref[acertos] if acertos < len(self.ref) else None
            antes = self.ref[max(0, acertos - 15):acertos]
            self.resultado.config(
                text=f"Erro na posição {acertos + 1} (de {len(self.ref)}).\n"
                     f"Esperado: {descrever_caractere(esperado)}\n"
                     f"Digitado: {descrever_caractere(valor[acertos])}\n"
                     f"Trecho antes: \"{antes}\"",
                fg=COR_ERRO)
        elif valor and len(valor) == len(self.ref):
            self.fim = True
            seg = max(time.perf_counter() - self.inicio, 0.001)
            self.v_tempo.config(text=f"{seg:.1f}s")
            tpm = len(self.ref) / seg * 60
            if self.erros == 0:
                self.resultado.config(
                    text=f"100% igual ao texto. Nenhum erro!  ({tpm:.0f} toques por minuto)",
                    fg=COR_OK)
            else:
                self.resultado.config(
                    text=f"Texto completo, mas teve {self.erros} erro(s) pelo caminho.", fg=COR_ERRO)
        elif valor:
            self.resultado.config(text="Digitando... sem erros até agora.", fg=COR_TEXTO)
        else:
            self.resultado.config(text=f"Aguardando o robô. Aperte {NOME_INICIAR}.", fg=COR_MUTED)


class JanelaTreino(tk.Toplevel):
    """Área de treino: VOCÊ digita, em textos de vários níveis, com métricas ao vivo e recorde."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("TYPEBOT - Área de treino")
        self.configure(bg=COR_FUNDO)
        self.minsize(600, 660)
        x = app.root.winfo_x() + 60
        y = app.root.winfo_y() + 30
        self.geometry(f"780x740+{x}+{y}")

        self.recordes = carregar_recordes()
        self.nivel = NIVEIS[0]
        self.ref = ""
        self.inicio = None
        self.erros = 0
        self.em_erro = False
        self.fim = False
        self.ultimo = ""
        self.ativo = True
        self._job = None

        self._montar()
        self.protocol("WM_DELETE_WINDOW", self.fechar)
        self.novo_texto()
        self._job = self.after(30, self._loop)

    def _montar(self):
        tk.Label(self, text="ÁREA DE TREINO", bg=COR_FUNDO, fg=COR_TEXTO,
                 font=(FONTE, 18, "bold")).pack(anchor="w", padx=24, pady=(18, 2))
        tk.Label(self, text="Digite você mesmo o texto de baixo. O tempo começa na primeira tecla "
                            "e o erro fica marcado em vermelho até você corrigir (Backspace).",
                 bg=COR_FUNDO, fg=COR_MUTED, font=(FONTE, 10), wraplength=720,
                 justify="left").pack(anchor="w", padx=24, pady=(0, 10))

        # Níveis
        niveis = tk.Frame(self, bg=COR_FUNDO)
        niveis.pack(fill="x", padx=24, pady=(0, 4))
        self.btn_nivel = {}
        for nome in NIVEIS:
            b = BotaoRedondo(niveis, nome.upper(), lambda n=nome: self.escolher(n),
                             COR_SEC, COR_SEC_HOVER, largura=140, altura=38,
                             fonte=(FONTE, 10, "bold"))
            b.pack(side="left", padx=(0, 8))
            self.btn_nivel[nome] = b
        self.lbl_recorde = tk.Label(self, text="", bg=COR_FUNDO, fg=COR_DESTAQUE_HOVER,
                                    font=(FONTE, 10, "bold"))
        self.lbl_recorde.pack(anchor="w", padx=24, pady=(4, 8))

        # Texto de referência
        card1 = tk.Frame(self, bg=COR_CARD, highlightthickness=1,
                         highlightbackground=COR_BORDA, padx=14, pady=10)
        card1.pack(fill="x", padx=24, pady=(0, 10))
        self.ref_text = tk.Text(card1, wrap="word", height=6, bg=COR_CAMPO, fg=COR_MUTED,
                                relief="flat", bd=0, padx=10, pady=8, font=(FONTE, 13),
                                state="disabled", highlightthickness=0, spacing2=4)
        self.ref_text.pack(fill="x")
        self.ref_text.tag_configure("ok", foreground=COR_OK)
        self.ref_text.tag_configure("bad", background=COR_PARAR, foreground="white")
        self.ref_text.tag_configure("cur", foreground=COR_TEXTO, underline=True)

        # Onde você digita
        card2 = tk.Frame(self, bg=COR_CARD, highlightthickness=1,
                         highlightbackground=COR_BORDA, padx=14, pady=10)
        card2.pack(fill="both", expand=True, padx=24, pady=(0, 10))
        tk.Label(card2, text="DIGITE AQUI", bg=COR_CARD, fg=COR_TEXTO,
                 font=(FONTE, 9, "bold")).pack(anchor="w", pady=(0, 6))
        self.entrada = tk.Text(card2, wrap="word", height=5, bg=COR_CAMPO, fg=COR_TEXTO,
                               insertbackground="white", relief="flat", bd=0, padx=10, pady=8,
                               font=(FONTE, 13), highlightthickness=1,
                               highlightbackground=COR_BORDA, highlightcolor=COR_DESTAQUE,
                               undo=False)
        self.entrada.pack(fill="both", expand=True)
        # Treino é para digitar de verdade: sem colar e sem Enter
        self.entrada.bind("<<Paste>>", lambda e: "break")
        self.entrada.bind("<Return>", lambda e: "break")

        # Números
        linha = tk.Frame(self, bg=COR_FUNDO)
        linha.pack(fill="x", padx=24, pady=(0, 8))
        self.v_tpm = self._stat(linha, "TPM (toques/min)")
        self.v_ppm = self._stat(linha, "PPM (palavras/min)")
        self.v_prec = self._stat(linha, "PRECISÃO")
        self.v_erros = self._stat(linha, "ERROS")
        self.v_tempo = self._stat(linha, "TEMPO")

        self.resultado = tk.Label(self, text="", bg=COR_FUNDO, fg=COR_MUTED,
                                  font=(FONTE, 11, "bold"), wraplength=720, justify="left")
        self.resultado.pack(anchor="w", padx=24, pady=(0, 8))

        botoes = tk.Frame(self, bg=COR_FUNDO)
        botoes.pack(pady=(0, 16))
        BotaoRedondo(botoes, "NOVO TEXTO", self.novo_texto, COR_DESTAQUE, COR_DESTAQUE_HOVER,
                     largura=170, altura=42, fonte=(FONTE, 10, "bold")).pack(side="left", padx=6)
        BotaoRedondo(botoes, "REINICIAR", self.reiniciar, COR_SEC, COR_SEC_HOVER,
                     largura=150, altura=42, fonte=(FONTE, 10, "bold")).pack(side="left", padx=6)
        BotaoRedondo(botoes, "FECHAR", self.fechar, COR_SEC, COR_SEC_HOVER,
                     largura=130, altura=42, fonte=(FONTE, 10, "bold")).pack(side="left", padx=6)

    def _stat(self, parent, titulo):
        quadro = tk.Frame(parent, bg=COR_CARD, highlightthickness=1,
                          highlightbackground=COR_BORDA, padx=8, pady=8)
        quadro.pack(side="left", expand=True, fill="x", padx=3)
        valor = tk.Label(quadro, text="0", bg=COR_CARD, fg=COR_TEXTO, font=(FONTE, 15, "bold"))
        valor.pack()
        tk.Label(quadro, text=titulo, bg=COR_CARD, fg=COR_MUTED, font=(FONTE, 8)).pack()
        return valor

    # ----- controle -----
    def escolher(self, nivel):
        self.nivel = nivel
        self.novo_texto()

    def _marcar_nivel(self):
        for nome, b in self.btn_nivel.items():
            if nome == self.nivel:
                b.definir_cores(COR_DESTAQUE, COR_DESTAQUE_HOVER)
            else:
                b.definir_cores(COR_SEC, COR_SEC_HOVER)
        rec = self.recordes.get(self.nivel)
        self.lbl_recorde.config(
            text=f"Recorde em {self.nivel}: {rec:.0f} TPM" if rec else f"Recorde em {self.nivel}: ainda sem recorde")

    def novo_texto(self):
        opcoes = TEXTOS_TREINO[self.nivel]
        if len(opcoes) > 1:
            opcoes = [t for t in opcoes if t != self.ref] or opcoes
        self._carregar(random.choice(opcoes))

    def reiniciar(self):
        self._carregar(self.ref)

    def _carregar(self, texto):
        self.ref = texto
        self.entrada.config(state="normal")
        self.entrada.delete("1.0", "end")
        self.inicio = None
        self.erros = 0
        self.em_erro = False
        self.fim = False
        self.ultimo = ""
        self._marcar_nivel()
        self._atualizar(0, False, "")
        self.entrada.focus_set()

    def fechar(self):
        self.ativo = False
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self.app.treino = None
        self.destroy()

    def _loop(self):
        if not self.ativo:
            return
        valor = self.entrada.get("1.0", "end-1c")
        if valor != self.ultimo and not self.fim:
            self.ultimo = valor
            self._atualizar(*comparar(self.ref, valor), valor)
        elif self.inicio is not None and not self.fim:
            self._numeros_ao_vivo(comparar(self.ref, valor)[0])
        self._job = self.after(30, self._loop)

    def _numeros_ao_vivo(self, acertos):
        seg = max(time.perf_counter() - self.inicio, 0.001)
        m = metricas(self.ref, acertos, self.erros, seg)
        self.v_tpm.config(text=f"{m['tpm']:.0f}")
        self.v_ppm.config(text=f"{m['ppm']:.0f}")
        self.v_prec.config(text=f"{m['precisao']:.0f}%")
        self.v_tempo.config(text=f"{seg:.1f}s")

    def _atualizar(self, acertos, tem_erro, valor):
        if self.inicio is None and valor:
            self.inicio = time.perf_counter()
        if tem_erro and not self.em_erro:
            self.erros += 1
        self.em_erro = tem_erro

        # Texto colorido: verde = certo, vermelho = onde errou
        self.ref_text.config(state="normal")
        self.ref_text.delete("1.0", "end")
        self.ref_text.insert("1.0", self.ref)
        if acertos:
            self.ref_text.tag_add("ok", "1.0", f"1.0+{acertos}c")
        if tem_erro and acertos < len(self.ref):
            self.ref_text.tag_add("bad", f"1.0+{acertos}c", f"1.0+{acertos + 1}c")
        elif not tem_erro and acertos < len(self.ref):
            self.ref_text.tag_add("cur", f"1.0+{acertos}c", f"1.0+{acertos + 1}c")
        self.ref_text.config(state="disabled")

        self.v_erros.config(text=str(self.erros))

        if not valor:
            for v, t in ((self.v_tpm, "0"), (self.v_ppm, "0"), (self.v_prec, "100%"), (self.v_tempo, "0.0s")):
                v.config(text=t)
            self.resultado.config(text="Comece a digitar quando quiser. O tempo corre a partir da primeira tecla.",
                                  fg=COR_MUTED)
            return

        self._numeros_ao_vivo(acertos)

        if tem_erro:
            esperado = self.ref[acertos] if acertos < len(self.ref) else None
            self.resultado.config(
                text=f"Erro na posição {acertos + 1}: era {descrever_caractere(esperado)}, "
                     f"você digitou {descrever_caractere(valor[acertos])}. Use Backspace para corrigir.",
                fg=COR_ERRO)
        elif len(valor) == len(self.ref):
            self._terminar()
        else:
            self.resultado.config(text="Muito bem, continue...", fg=COR_TEXTO)

    def _terminar(self):
        self.fim = True
        seg = max(time.perf_counter() - self.inicio, 0.001)
        m = metricas(self.ref, len(self.ref), self.erros, seg)
        self.v_tpm.config(text=f"{m['tpm']:.0f}")
        self.v_ppm.config(text=f"{m['ppm']:.0f}")
        self.v_prec.config(text=f"{m['precisao']:.0f}%")
        self.v_tempo.config(text=f"{seg:.1f}s")
        self.entrada.config(state="disabled")

        anterior = self.recordes.get(self.nivel, 0)
        novo_recorde = m["tpm"] > anterior and m["precisao"] >= 95
        if novo_recorde:
            self.recordes[self.nivel] = round(m["tpm"], 1)
            salvar_recordes(self.recordes)
            self._marcar_nivel()

        msg = f"Concluído!  {m['tpm']:.0f} TPM  •  {m['ppm']:.0f} PPM  •  precisão {m['precisao']:.0f}%  •  {self.erros} erro(s)"
        if novo_recorde:
            msg += "\nNOVO RECORDE neste nível!"
        elif m["precisao"] < 95:
            msg += "\nPara valer recorde, a precisão precisa ser de pelo menos 95%."
        self.resultado.config(text=msg, fg=COR_OK if m["precisao"] >= 95 else COR_ERRO)


class AutoTypeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TYPEBOT by Math")
        self.root.configure(bg=COR_FUNDO)
        self.root.minsize(640, 640)
        self._centralizar(780, 880)

        self.teclado = Controller()

        self.speed_var = tk.DoubleVar(value=0.050)
        self.start_delay_var = tk.DoubleVar(value=3)

        # Comunicação segura entre as threads (atalhos/digitação) e a janela
        self.fila = queue.Queue()
        self.parar_evento = threading.Event()
        self.digitando = False
        self.atalhos = None
        self.teste = None
        self.treino = None

        self.create_widgets()
        self._iniciar_atalhos()

        self.root.protocol("WM_DELETE_WINDOW", self._fechar)
        self.root.after(50, self._processar_fila)

    # ----- janela -----
    def _centralizar(self, largura, altura):
        altura = min(altura, self.root.winfo_screenheight() - 80)
        x = (self.root.winfo_screenwidth() - largura) // 2
        y = max(0, (self.root.winfo_screenheight() - altura) // 2 - 30)
        self.root.geometry(f"{largura}x{altura}+{x}+{y}")

    def _card(self, parent, **pack):
        card = tk.Frame(parent, bg=COR_CARD, highlightthickness=1,
                        highlightbackground=COR_BORDA, padx=18, pady=14)
        card.pack(**pack)
        return card

    def _slider(self, parent, titulo, de, ate, resolucao, variavel, formato, dica):
        topo = tk.Frame(parent, bg=COR_CARD)
        topo.pack(fill="x")
        tk.Label(topo, text=titulo, bg=COR_CARD, fg=COR_TEXTO,
                 font=(FONTE, 10, "bold")).pack(side="left")
        valor = tk.Label(topo, bg=COR_CARD, fg=COR_DESTAQUE_HOVER,
                         font=(FONTE, 10, "bold"))
        valor.pack(side="right")

        def atualizar(_=None):
            valor.config(text=formato(variavel.get()))

        escala = tk.Scale(parent, from_=de, to=ate, resolution=resolucao,
                          orient=tk.HORIZONTAL, variable=variavel, command=atualizar,
                          showvalue=False, bg=COR_CARD, fg=COR_TEXTO,
                          troughcolor=COR_CAMPO, activebackground=COR_DESTAQUE_HOVER,
                          highlightthickness=0, bd=0, sliderrelief="flat",
                          sliderlength=22, width=14, cursor="hand2")
        escala.pack(fill="x", pady=(2, 0))
        tk.Label(parent, text=dica, bg=COR_CARD, fg=COR_MUTED,
                 font=(FONTE, 9)).pack(anchor="w")
        atualizar()

    # ----- layout -----
    def create_widgets(self):
        # Rodapé e barra de status primeiro, para ficarem sempre visíveis embaixo
        rodape = tk.Label(self.root, text="by Math   •   baseado no AUTO-ESCRITOR de @VILHALVA",
                          bg=COR_FUNDO, fg=COR_MUTED, font=(FONTE, 9))
        rodape.pack(side="bottom", pady=(0, 12))

        bloco = tk.Frame(self.root, bg=COR_FUNDO)
        bloco.pack(side="bottom", fill="x", padx=28, pady=(0, 8))
        self.status = tk.Label(bloco, text="", bg=COR_FUNDO, fg=COR_MUTED, font=(FONTE, 10))
        self.status.pack()
        trilho = tk.Frame(bloco, bg=COR_CAMPO, height=6)
        trilho.pack(fill="x", pady=(6, 0))
        self.barra = tk.Frame(trilho, bg=COR_DESTAQUE)
        self.barra.place(x=0, y=0, relheight=1, relwidth=0)

        # Cabeçalho
        cab = tk.Frame(self.root, bg=COR_FUNDO)
        cab.pack(fill="x", padx=28, pady=(24, 14))
        titulo = tk.Frame(cab, bg=COR_FUNDO)
        titulo.pack(anchor="w")
        tk.Label(titulo, text="TYPEBOT", bg=COR_FUNDO, fg=COR_TEXTO,
                 font=(FONTE, 24, "bold")).pack(side="left")
        tk.Label(titulo, text="by Math", bg=COR_FUNDO, fg=COR_DESTAQUE_HOVER,
                 font=(FONTE, 11, "italic")).pack(side="left", anchor="s", padx=(8, 0), pady=(0, 6))
        tk.Label(cab, text="Automatize o processo de digitação", bg=COR_FUNDO,
                 fg=COR_MUTED, font=(FONTE, 11)).pack(anchor="w")

        # Cartão do texto
        card_texto = self._card(self.root, fill="both", expand=True, padx=28, pady=(0, 12))
        linha = tk.Frame(card_texto, bg=COR_CARD)
        linha.pack(fill="x", pady=(0, 8))
        tk.Label(linha, text="TEXTO", bg=COR_CARD, fg=COR_TEXTO,
                 font=(FONTE, 10, "bold")).pack(side="left")
        self.contador = tk.Label(linha, text="0 caracteres", bg=COR_CARD,
                                 fg=COR_MUTED, font=(FONTE, 9))
        self.contador.pack(side="right")

        self.text_entry = tk.Text(card_texto, wrap="word", height=7, bg=COR_CAMPO,
                                  fg=COR_TEXTO, insertbackground="white",
                                  selectbackground=COR_DESTAQUE, selectforeground="white",
                                  relief="flat", bd=0, padx=12, pady=10,
                                  font=(FONTE, 12), undo=True,
                                  highlightthickness=1, highlightbackground=COR_BORDA,
                                  highlightcolor=COR_DESTAQUE)
        self.text_entry.pack(fill="both", expand=True)
        self.text_entry.bind("<KeyRelease>", self._atualizar_contador)
        self.text_entry.bind("<<Paste>>", lambda e: self.root.after(20, self._atualizar_contador))
        self.text_entry.bind("<<Cut>>", lambda e: self.root.after(20, self._atualizar_contador))

        # Cartão das configurações
        card_cfg = self._card(self.root, fill="x", padx=28, pady=(0, 12))
        self._slider(card_cfg, "VELOCIDADE", 0.010, 0.100, 0.001, self.speed_var,
                     lambda v: f"{v:.3f} s por caractere",
                     "Quanto menor o valor, mais rápida a digitação.")
        tk.Frame(card_cfg, bg=COR_CARD, height=10).pack()
        self._slider(card_cfg, "INICIAR EM", 1, 10, 1, self.start_delay_var,
                     lambda v: f"{int(v)} s",
                     "Tempo para você clicar no campo (vale para o botão; o atalho começa na hora).")

        # Botões
        linha1 = tk.Frame(self.root, bg=COR_FUNDO)
        linha1.pack(pady=(0, 8))
        self.btn_iniciar = BotaoRedondo(linha1, f"▶   INICIAR  ({NOME_INICIAR})",
                                        self.iniciar, COR_DESTAQUE, COR_DESTAQUE_HOVER,
                                        largura=250, altura=52)
        self.btn_iniciar.pack(side="left", padx=6)
        self.btn_parar = BotaoRedondo(linha1, f"■   PARAR  ({NOME_PARAR})",
                                      self.parar, COR_PARAR, COR_PARAR_HOVER,
                                      largura=200, altura=52)
        self.btn_parar.pack(side="left", padx=6)
        self.btn_parar.ativar(False)

        linha2 = tk.Frame(self.root, bg=COR_FUNDO)
        linha2.pack(pady=(0, 10))
        pequena = (FONTE, 10, "bold")
        self.btn_corrigir = BotaoRedondo(linha2, "✎   CORRIGIR TEXTO", self.corrigir_texto,
                                         COR_SEC, COR_SEC_HOVER, largura=180, altura=42, fonte=pequena)
        self.btn_corrigir.pack(side="left", padx=5)
        self.btn_testar = BotaoRedondo(linha2, "✔   TESTAR", self.abrir_teste,
                                       COR_SEC, COR_SEC_HOVER, largura=130, altura=42, fonte=pequena)
        self.btn_testar.pack(side="left", padx=5)
        self.btn_treinar = BotaoRedondo(linha2, "★   TREINAR", self.abrir_treino,
                                        COR_SEC, COR_SEC_HOVER, largura=140, altura=42, fonte=pequena)
        self.btn_treinar.pack(side="left", padx=5)
        self.btn_limpar = BotaoRedondo(linha2, "LIMPAR", self.validate_and_clear,
                                       COR_SEC, COR_SEC_HOVER, largura=110, altura=42, fonte=pequena)
        self.btn_limpar.pack(side="left", padx=5)

    # ----- status / contador -----
    def _status(self, texto, cor=COR_MUTED):
        self.status.config(text=texto, fg=cor)

    def _atualizar_contador(self, _=None):
        n = len(self.text_entry.get("1.0", "end-1c"))
        self.contador.config(text=f"{n} caractere" + ("" if n == 1 else "s"))

    def _progresso(self, feitos, total):
        self.barra.place_configure(relwidth=(feitos / total) if total else 0)

    # ----- atalhos globais -----
    def _iniciar_atalhos(self):
        try:
            self.atalhos = GlobalHotKeys({
                ATALHO_INICIAR: lambda: self.fila.put(("iniciar",)),
                ATALHO_PARAR: lambda: self.fila.put(("parar",)),
            })
            self.atalhos.daemon = True
            self.atalhos.start()
            self._status(f"Pronto  •  {NOME_INICIAR} inicia  •  {NOME_PARAR} para")
        except Exception:
            self.atalhos = None
            self._status("Pronto  •  atalhos de teclado indisponíveis (use os botões)")

    def _processar_fila(self):
        try:
            while True:
                evento = self.fila.get_nowait()
                if evento[0] == "iniciar":
                    self.iniciar(via_atalho=True)
                elif evento[0] == "parar":
                    self.parar()
                elif evento[0] == "progresso":
                    self._progresso(evento[1], evento[2])
                    self._status(f"Digitando...  {evento[1]} / {evento[2]}", COR_TEXTO)
                elif evento[0] == "fim":
                    self._fim(evento[1])
        except queue.Empty:
            pass
        self.root.after(50, self._processar_fila)

    def _fechar(self):
        self.parar_evento.set()
        if self.atalhos is not None:
            try:
                self.atalhos.stop()
            except Exception:
                pass
        self.root.destroy()

    # ----- ações -----
    def _teste_aberto(self):
        return self.teste is not None and self.teste.ativo

    def abrir_teste(self):
        if self.digitando:
            return
        if self._teste_aberto():
            self.teste.lift()
            return
        self.teste = JanelaTeste(self)
        self._status(f"Janela de teste aberta  •  aperte {NOME_INICIAR} para o robô digitar nela")

    def abrir_treino(self):
        if self.digitando:
            return
        if self.treino is not None and self.treino.ativo:
            self.treino.lift()
            return
        self.treino = JanelaTreino(self)
        self._status("Área de treino aberta  •  digite você mesmo e acompanhe o TPM")

    def iniciar(self, via_atalho=False):
        if self.digitando:
            return

        teste_aberto = self._teste_aberto()
        if teste_aberto and not via_atalho:
            # O botão tira o foco da janela de teste e o robô digitaria no lugar errado
            self._status(f"Com a janela de teste aberta, use o atalho {NOME_INICIAR}.", COR_ERRO)
            return

        bruto = self.text_entry.get("1.0", "end-1c")
        text, achados = normalizar_texto(bruto)
        if not text:
            if via_atalho:
                self._status("Campo de texto vazio.", COR_ERRO)
            else:
                messagebox.showwarning("Campo vazio", "Por favor, digite algum texto antes de iniciar.")
            return

        # Proteção: não deixa o robô digitar dentro da própria caixa de texto do app
        if via_atalho and not teste_aberto:
            try:
                foco = self.root.focus_get()
            except Exception:
                foco = None
            if foco is self.text_entry:
                self._status(f"Clique no campo de destino antes de apertar {NOME_INICIAR}.", COR_ERRO)
                return

        # Limpa o texto automaticamente (sem janelas, para não tirar o foco do campo de destino)
        if text != bruto:
            self.text_entry.delete("1.0", tk.END)
            self.text_entry.insert("1.0", text)
            self._atualizar_contador()

        if teste_aberto:
            self.teste.preparar(text, forcar_foco=True)

        atraso = 0.3 if via_atalho else self.start_delay_var.get()
        if not via_atalho:
            self.root.iconify()

        self.parar_evento.clear()
        self.digitando = True
        self.btn_iniciar.ativar(False)
        self.btn_corrigir.ativar(False)
        self.btn_testar.ativar(False)
        self.btn_treinar.ativar(False)
        self.btn_limpar.ativar(False)
        self.btn_parar.ativar(True)
        self._progresso(0, 1)
        self._status("Começando...", COR_TEXTO)

        threading.Thread(target=self.type_text, args=(text, self.speed_var.get(), atraso), daemon=True).start()

    def parar(self):
        if self.digitando:
            self.parar_evento.set()

    def type_text(self, text, speed, start_delay):
        total = len(text)
        try:
            if self.parar_evento.wait(start_delay):
                self.fila.put(("fim", "parado"))
                return

            # Em vez de pyautogui.write() (que só envia teclas do layout US e
            # perde pontuação/acentos no teclado ABNT2), cada caractere é enviado
            # como Unicode pelo pynput, então sai exatamente como no texto.
            for i, char in enumerate(text, 1):
                if self.parar_evento.is_set():
                    self.fila.put(("fim", "parado"))
                    return
                if char == "\n":
                    self.teclado.press(Key.enter)
                    self.teclado.release(Key.enter)
                else:
                    self.teclado.type(char)
                if i % 3 == 0 or i == total:
                    self.fila.put(("progresso", i, total))
                if self.parar_evento.wait(speed):
                    self.fila.put(("fim", "parado"))
                    return
            self.fila.put(("fim", "concluido"))
        except Exception:
            self.fila.put(("fim", "erro"))

    def _fim(self, motivo):
        self.digitando = False
        self.btn_iniciar.ativar(True)
        self.btn_corrigir.ativar(True)
        self.btn_testar.ativar(True)
        self.btn_treinar.ativar(True)
        self.btn_limpar.ativar(True)
        self.btn_parar.ativar(False)

        estava_minimizado = self.root.state() == "iconic"
        if estava_minimizado:
            self.root.deiconify()

        if motivo == "concluido":
            self._progresso(1, 1)
            self._status("Concluído!", COR_OK)
            if estava_minimizado:
                messagebox.showinfo("Finalizado", "A digitação foi concluída com sucesso!")
        elif motivo == "parado":
            self._status("Digitação interrompida.", COR_ERRO)
        else:
            self._status("Ocorreu um erro durante a digitação.", COR_ERRO)

    def corrigir_texto(self):
        if self.digitando:
            return
        bruto = self.text_entry.get("1.0", "end-1c")
        if not bruto.strip():
            messagebox.showinfo("Nada para corrigir", "O campo de texto está vazio.")
            return

        text, achados = normalizar_texto(bruto)
        if text == bruto:
            self._status("O texto já está certo, nada para corrigir.", COR_OK)
            messagebox.showinfo("Texto já está certo",
                                "Não foi encontrado nenhum espaço estranho nem caractere escondido.")
            return

        self.text_entry.delete("1.0", tk.END)
        self.text_entry.insert("1.0", text)
        self._atualizar_contador()

        if achados:
            lista = "\n".join(f"- {nome}: {qtd}x" for nome, qtd in achados.items())
            self._status("Texto corrigido!", COR_OK)
            messagebox.showinfo("Texto corrigido",
                                "Estes caracteres foram trocados/removidos:\n\n" + lista)
        else:
            self._status("Espaços no começo/fim do texto foram removidos.", COR_OK)

    def validate_and_clear(self):
        text = self.text_entry.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Nada para limpar", "O campo já está vazio.")
            return
        self.text_entry.delete("1.0", tk.END)
        self._atualizar_contador()
        self._progresso(0, 1)


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoTypeApp(root)
    root.mainloop()
