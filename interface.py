import os
import json
import queue
import re
import sys
import threading
import unicodedata
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

try:
    import customtkinter as ctk
except ImportError as erro:
    raise SystemExit("CustomTkinter ausente. Instale: python -m pip install customtkinter") from erro

import CasaInteligente as modulo_casa
sys.modules.setdefault("casa_inteligente", modulo_casa)
from CasaInteligente import (
    CasaInteligente, AssistenteVirtual, LampadaInteligente,
    ArCondicionado, SensorPresenca, SensorTemperatura, ConexaoWiFi,
)

try:
    if sys.platform == "win32":
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            pass
        else:
            sys.modules["pyaudio"] = pyaudio
    import speech_recognition as sr
except ImportError:
    sr = None

ctk.set_default_color_theme("blue")
ctk.set_appearance_mode("dark")

casa = CasaInteligente()
janela = ctk.CTk()
janela.title("Casa Inteligente")
janela.geometry("1280x830")
janela.minsize(980, 680)

tema_atual = "escuro"
HISTORICO_ARQUIVO = "historico_atividades.txt"
historico_atividades = []
secoes_painel = {}
canvas_painel = None
painel_scroll = None
status_bar = None
label_caminho = None
pagina_atual = "inicio"
comodo_ativo = None
menu_botoes = {}
COMODOS_ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comodos_dispositivos.json")
COMODOS_SUGESTOES = ["Sala", "Cozinha", "Quarto", "Banheiro", "Quintal", "Escritório", "Garagem", "Lavanderia", "Varanda", "Corredor", "Sem Cômodo"]
locais_dispositivos = {}

# --------------- Sistema de voz (lógica original preservada) -----------
fila_voz = queue.Queue()
voz_em_execucao = False
voz_modo_continuo = False
voz_evento_parar = threading.Event()
voz_sessao = 0
voz_id_assistente = None
microfone_indice = None
texto_estado_voz = tk.StringVar(master=janela, value="Microfone em espera.")
texto_ultimo_comando = tk.StringVar(master=janela, value="Exemplo: Alexa, ligar Lâmpada da Sala.")

CORES = {
    "escuro": {
        "fundo": "#0C111D", "lateral": "#111827", "superficie": "#182233",
        "superficie_2": "#223047", "borda": "#2B3B51", "texto": "#F5F8FF",
        "texto_fraco": "#ADBBD0", "texto_sutil": "#7D90AA", "azul": "#73A9FF",
        "azul_escuro": "#224B96", "verde": "#44D9AB", "vermelho": "#FB7D89",
        "amarelo": "#F6C967", "ciano": "#65D8F3", "roxo": "#C09BFF",
        "laranja": "#FFA66E", "botao": "#293A54", "botao_hover": "#3B5172",
        "entrada": "#101A2B", "hero": "#234E9D", "hero_2": "#315EB5",
        "accent_azul": "#DCEAFF", "card_sombra": "#121D2D",
    },
    "claro": {
        "fundo": "#F1F5FC", "lateral": "#FFFFFF", "superficie": "#FFFFFF",
        "superficie_2": "#EDF3FB", "borda": "#D9E4F1", "texto": "#172437",
        "texto_fraco": "#5A6D86", "texto_sutil": "#8291A8", "azul": "#316EDF",
        "azul_escuro": "#DBE9FF", "verde": "#168C70", "vermelho": "#CF5268",
        "amarelo": "#BC7C12", "ciano": "#0E8EAC", "roxo": "#7859CB",
        "laranja": "#CB6E30", "botao": "#E9F0F9", "botao_hover": "#DAE7F7",
        "entrada": "#F8FBFF", "hero": "#3B73D7", "hero_2": "#6A9EF5",
        "accent_azul": "#FFFFFF", "card_sombra": "#ECF0F8",
    },
}

def cor(nome):
    return CORES[tema_atual][nome]

FONT = ("Segoe UI" if sys.platform == "win32" else "Arial")

def fonte(tamanho=12, peso="normal"):
    return ctk.CTkFont(family=FONT, size=tamanho, weight="bold" if peso == "bold" else "normal")

def misturar_cor(inicio, fim, t):
    a = [int(inicio[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(fim[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))

class BotaoAnimado(ctk.CTkButton):
    """Botão CTk com transições suaves de hover usando after, sem bloquear eventos."""
    def __init__(self, mestre, *, texto, comando, estilo="normal", compacto=False,
                 fundo=None, frente=None, borda=None, largura=None, altura=None,
                 alinhamento="center", **kwargs):
        estilos = {
            "normal": (cor("botao"), cor("texto")),
            "primario": ("#407CF2", "#FFFFFF"),
            "positivo": ("#147E69" if tema_atual == "escuro" else "#168D70", "#FFFFFF"),
            "perigo": ("#B94A5E" if tema_atual == "escuro" else "#D25364", "#FFFFFF"),
            "suave": (cor("superficie_2"), cor("texto_fraco")),
        }
        bg, fg = estilos.get(estilo, estilos["normal"])
        self._normal = fundo or bg
        self._hover = misturar_cor(self._normal, "#FFFFFF" if tema_atual == "escuro" else "#192F5A", .14 if tema_atual == "escuro" else .08)
        self._color = self._normal
        self._job = None
        self._alvo = self._normal
        self._acao_real = comando
        super().__init__(mestre, text=texto, fg_color=self._normal, hover=False,
                         text_color=frente or fg, corner_radius=12,
                         height=altura or (34 if compacto else 42),
                         width=largura or (95 if compacto else 132),
                         font=fonte(11 if compacto else 12, "bold"),
                         border_width=1 if borda else 0,
                         border_color=borda or self._normal,
                         anchor=alinhamento, command=self._clicar, **kwargs)
        self.bind("<Enter>", lambda _e: self._animar(self._hover), add="+")
        self.bind("<Leave>", lambda _e: self._animar(self._normal), add="+")

    def _animar(self, destino):
        self._alvo = destino
        if self._job is not None:
            try: self.after_cancel(self._job)
            except Exception: pass
        origem = self._color
        def passo(n=1):
            if not self.winfo_exists():
                return
            self._color = misturar_cor(origem, destino, n / 7)
            self.configure(fg_color=self._color)
            if n < 7:
                self._job = self.after(18, lambda: passo(n + 1))
            else:
                self._job = None
        passo()

    def _clicar(self):
        if self._acao_real:
            self._acao_real()


def criar_botao(pai, texto, comando, estilo="normal", compacto=False, **kwargs):
    return BotaoAnimado(pai, texto=texto, comando=comando, estilo=estilo, compacto=compacto, **kwargs)

def criar_rotulo(pai, texto, tamanho=11, peso="normal", cor_texto=None, fundo=None,
                 fonte=None, **kwargs):
    kwargs.pop("bg", None)
    kwargs.pop("fg", None)
    return ctk.CTkLabel(pai, text=texto, font=fonte or globals()["fonte"](tamanho, peso),
                        text_color=cor_texto or cor("texto"), fg_color="transparent",
                        **kwargs)

def caixa(pai, fundo=None, arredondado=0, borda=False, **kwargs):
    return ctk.CTkFrame(pai, fg_color=fundo or "transparent", corner_radius=arredondado,
                        border_width=1 if borda else 0, border_color=cor("borda"), **kwargs)

def criar_cartao(pai, padding=18):
    # O padding será aplicado pelos conteúdos internos, não nos construtores CTk.
    return ctk.CTkFrame(pai, fg_color=cor("superficie"), corner_radius=21,
                        border_width=1, border_color=cor("borda"))

def rotulo_pill(pai, texto, cor_chave, preenchimento=None):
    pill = ctk.CTkFrame(pai, fg_color=preenchimento or fundo_icone(cor_chave), corner_radius=12)
    criar_rotulo(pill, texto, 10, "bold", cor(cor_chave)).pack(padx=11, pady=5)
    return pill

def cabecalho_secao(pai, titulo, descricao="", botao=None):
    linha = caixa(pai)
    linha.pack(fill="x", pady=(23, 12))
    criar_rotulo(linha, titulo, 17, "bold").pack(side="left", anchor="w")
    if botao is not None:
        botao(linha).pack(side="right")
    if descricao:
        criar_rotulo(pai, descricao, 11, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(0, 8))
    return linha



def normalizar_texto(texto):
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(letra for letra in texto if unicodedata.category(letra) != "Mn")

def carregar_comodos():
    try:
        with open(COMODOS_ARQUIVO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if isinstance(dados, dict):
            return {str(chave): str(valor) for chave, valor in dados.items() if str(chave).isdigit() and isinstance(valor, str)}
    except (OSError, ValueError, TypeError):
        pass
    return {}

def salvar_comodos():
    temporario = COMODOS_ARQUIVO + ".tmp"
    try:
        with open(temporario, "w", encoding="utf-8") as arquivo:
            json.dump(locais_dispositivos, arquivo, ensure_ascii=False, indent=2)
        os.replace(temporario, COMODOS_ARQUIVO)
    except OSError as erro:
        try:
            os.remove(temporario)
        except OSError:
            pass
        messagebox.showerror("Cômodos", f"Não foi possível salvar o cômodo.\n{erro}", parent=janela)

def formatar_comodo(nome):
    nome = " ".join(str(nome).strip().split()).title()
    return nome if nome else "Sem Cômodo"

def sugerir_comodo_nome(nome):
    texto = normalizar_texto(nome)
    for local in sorted(COMODOS_SUGESTOES, key=len, reverse=True):
        if local == "Sem Cômodo":
            continue
        if re.search(r"(?<!\w)" + re.escape(normalizar_texto(local)) + r"(?!\w)", texto):
            return local
    return "Sem Cômodo"

def obter_comodo(id_disp, dispositivo=None):
    if str(id_disp) in locais_dispositivos:
        return formatar_comodo(locais_dispositivos[str(id_disp)])
    if dispositivo is None:
        dispositivo = casa.get_dispositivo(id_disp)
    return sugerir_comodo_nome(dispositivo.get_nome())

def lista_comodos():
    nomes = {obter_comodo(i, d) for i, d in casa.listar_dispositivos()}
    prioridade = [c for c in COMODOS_SUGESTOES if c in nomes and c != "Sem Cômodo"]
    return prioridade + sorted(nomes - set(prioridade) - {"Sem Cômodo"}) + (["Sem Cômodo"] if "Sem Cômodo" in nomes else [])

def editar_comodo(id_disp):
    dispositivo = casa.get_dispositivo(id_disp)
    local = selecionar_comodo_dialogo("Alterar cômodo", obter_comodo(id_disp, dispositivo))
    if local is None:
        return
    locais_dispositivos[str(id_disp)] = local
    salvar_comodos()
    registrar_atividade(f"Cômodo de {dispositivo.get_nome().title()} alterado para {local}.")
    atualizar_lista()
    atualizar_status(f"{dispositivo.get_nome().title()} está em {local}.")

def categoria_dispositivo(dispositivo):
    if isinstance(dispositivo, LampadaInteligente):
        return "lampadas"
    if isinstance(dispositivo, ArCondicionado):
        return "ar"
    if isinstance(dispositivo, (SensorPresenca, SensorTemperatura)):
        return "sensores"
    if isinstance(dispositivo, AssistenteVirtual):
        return "assistentes"
    return "inicio"

def dispositivos_categoria(chave):
    tipos = {"lampadas": LampadaInteligente, "ar": ArCondicionado,
             "sensores": (SensorPresenca, SensorTemperatura), "assistentes": AssistenteVirtual}
    return [(i, d) for i, d in casa.listar_dispositivos() if isinstance(d, tipos[chave])]

def dispositivos_comodo(local):
    return [(i, d) for i, d in casa.listar_dispositivos() if normalizar_texto(obter_comodo(i, d)) == normalizar_texto(local)]

def registrar_atividade(mensagem):
    """Registra a mensagem da operacao e mantem o historico entre execucoes."""
    linha = f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | {mensagem.strip()}"
    historico_atividades.insert(0, linha)
    try:
        with open(HISTORICO_ARQUIVO, "a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")
    except OSError:
        pass

def carregar_historico():
    if not os.path.exists(HISTORICO_ARQUIVO):
        return []
    try:
        with open(HISTORICO_ARQUIVO, "r", encoding="utf-8") as arquivo:
            return [linha.rstrip("\n") for linha in arquivo.readlines()][-100:][::-1]
    except OSError:
        return []

def reparar_wifi_antigo():
    """Inicializa dados Wi-Fi ausentes em aparelhos salvos por versoes anteriores."""
    houve_alteracao = False

    for _, dispositivo in casa.listar_dispositivos():
        if isinstance(dispositivo, ConexaoWiFi):
            try:
                dispositivo.get_ssid()
                dispositivo.is_conectado_wifi()
            except AttributeError:
                ConexaoWiFi.__init__(dispositivo, "Casa", "12345678")
                houve_alteracao = True

    if houve_alteracao:
        casa.salvar_estado()

def nome_tipo(dispositivo):
    if isinstance(dispositivo, LampadaInteligente):
        return "Lâmpada Inteligente"
    if isinstance(dispositivo, ArCondicionado):
        return "Ar Condicionado"
    if isinstance(dispositivo, SensorPresenca):
        return "Sensor de Presença"
    if isinstance(dispositivo, SensorTemperatura):
        return "Sensor de Temperatura"
    if isinstance(dispositivo, AssistenteVirtual):
        return "Assistente Virtual"
    return "Dispositivo"

def obter_icone(dispositivo):
    if isinstance(dispositivo, LampadaInteligente):
        return "☼", "amarelo"
    if isinstance(dispositivo, ArCondicionado):
        return "❄", "ciano"
    if isinstance(dispositivo, SensorPresenca):
        return "◉", "roxo"
    if isinstance(dispositivo, SensorTemperatura):
        return "♨", "laranja"
    if isinstance(dispositivo, AssistenteVirtual):
        return "◖))", "azul"
    return "⌂", "azul"

def obter_status_wifi(dispositivo):
    if not isinstance(dispositivo, ConexaoWiFi):
        return "Sem Wi-Fi"
    try:
        return "Conectado" if dispositivo.is_conectado_wifi() else "Desconectado"
    except AttributeError:
        return "Nao inicializado"

def obter_selecionado(id_disp=None):
    """Mantem a mesma validacao da interface anterior, agora por cartao/ID."""
    if id_disp is None:
        messagebox.showwarning(
            "Seleção necessária",
            "Selecione um dispositivo na lista primeiro.",
            parent=janela,
        )
        return None, None
    try:
        return id_disp, casa.get_dispositivo(id_disp)
    except Exception as erro:
        messagebox.showerror("Erro", str(erro), parent=janela)
        atualizar_lista()
        return None, None

def atualizar_status(texto):
    if status_bar is not None and status_bar.winfo_exists():
        status_bar.configure(text=texto)

def remover_dispositivo(id_disp=None):
    id_disp, dispositivo = obter_selecionado(id_disp)
    if dispositivo is None:
        return
    confirmar = messagebox.askyesno(
        "Confirmar remoção",
        f"Deseja remover '{dispositivo.get_nome()}' (ID {id_disp})?",
        parent=janela,
    )
    if not confirmar:
        return
    try:
        dispositivo_removido = casa.remover_dispositivo(id_disp)
        locais_dispositivos.pop(str(id_disp), None)
        salvar_comodos()
        if id_disp == voz_id_assistente:
            parar_escuta_voz()
        mensagem = f"Dispositivo '{dispositivo_removido.get_nome()}' removido com sucesso."
        registrar_atividade(mensagem)
        atualizar_lista()
        atualizar_status(mensagem)
    except Exception as erro:
        messagebox.showerror("Erro ao remover", str(erro), parent=janela)

def ligar_dispositivo(id_disp=None):
    id_disp, dispositivo = obter_selecionado(id_disp)
    if dispositivo is None:
        return
    try:
        casa.ligar_dispositivo(id_disp)
        mensagem = f"{casa.get_dispositivo(id_disp).get_nome()} ligado com sucesso!"
        registrar_atividade(mensagem)
        atualizar_lista()
        atualizar_status(mensagem)
    except Exception as erro:
        messagebox.showerror("Não foi possível ligar", str(erro), parent=janela)

def desligar_dispositivo(id_disp=None):
    id_disp, dispositivo = obter_selecionado(id_disp)
    if dispositivo is None:
        return
    try:
        casa.desligar_dispositivo(id_disp)
        if id_disp == voz_id_assistente:
            parar_escuta_voz()
        mensagem = f"{casa.get_dispositivo(id_disp).get_nome()} desligado com sucesso!"
        registrar_atividade(mensagem)
        atualizar_lista()
        atualizar_status(mensagem)
    except Exception as erro:
        messagebox.showerror("Não foi possível desligar", str(erro), parent=janela)

def alternar_dispositivo(id_disp):
    dispositivo = casa.get_dispositivo(id_disp)
    if dispositivo.is_ligado():
        desligar_dispositivo(id_disp)
    else:
        ligar_dispositivo(id_disp)

def conectar_wifi(id_disp=None):
    id_disp, dispositivo = obter_selecionado(id_disp)
    if dispositivo is None:
        return
    if not isinstance(dispositivo, ConexaoWiFi):
        messagebox.showwarning(
            "Wi-Fi indisponível",
            "O dispositivo selecionado não possui conexão Wi-Fi.",
            parent=janela,
        )
        return
    try:
        senha = simpledialog.askstring(
            "Conectar ao Wi-Fi",
            f"Digite a senha da rede '{dispositivo.get_ssid()}':",
            parent=janela,
            show="*",
        )
        if senha is None:
            return
        resultado = dispositivo.conectar(senha)
        casa.salvar_estado()
        registrar_atividade(resultado)
        atualizar_lista()
        atualizar_status(resultado)
    except Exception as erro:
        messagebox.showerror("Falha na conexão", str(erro), parent=janela)

def desconectar_wifi(id_disp=None):
    id_disp, dispositivo = obter_selecionado(id_disp)
    if dispositivo is None:
        return
    if not isinstance(dispositivo, ConexaoWiFi):
        messagebox.showwarning(
            "Wi-Fi indisponível",
            "O dispositivo selecionado não possui conexão Wi-Fi.",
            parent=janela,
        )
        return
    try:
        resultado = dispositivo.desconectar()
        casa.salvar_estado()
        registrar_atividade(resultado)
        atualizar_lista()
        atualizar_status(resultado)
    except Exception as erro:
        messagebox.showerror("Falha ao desconectar", str(erro), parent=janela)

def mudar_cor_lampada(id_disp, nova_cor):
    try:
        dispositivo = casa.get_dispositivo(id_disp)
        if not isinstance(dispositivo, LampadaInteligente):
            return
        dispositivo.mudar_cor(nova_cor)
        casa.salvar_estado()
        mensagem = "Cor alterada."
        registrar_atividade(f"{mensagem} {dispositivo.get_nome()}: {nova_cor}.")
        atualizar_lista()
        atualizar_status(mensagem)
    except Exception as erro:
        messagebox.showerror("Nao foi possivel mudar a cor", str(erro), parent=janela)

def ajustar_temperatura_ar(id_disp, variacao=None):
    dispositivo = casa.get_dispositivo(id_disp)
    if not isinstance(dispositivo, ArCondicionado):
        return
    if variacao is None:
        temp_atual = extrair_temperatura_ar(dispositivo)
        nova_temp = simpledialog.askinteger(
            "Ajustar temperatura (Ar Condicionado)",
            "Nova temperatura (16-30°C):",
            parent=janela,
            initialvalue=temp_atual,
            minvalue=16,
            maxvalue=30,
        )
        if nova_temp is None:
            return
    else:
        nova_temp = extrair_temperatura_ar(dispositivo) + variacao
    try:
        dispositivo.ajustar_temperatura(nova_temp)
        casa.salvar_estado()
        mensagem = "Temperatura ajustada."
        registrar_atividade(f"{mensagem} {dispositivo.get_nome()}: {nova_temp}°C.")
        atualizar_lista()
        atualizar_status(mensagem)
    except Exception as erro:
        messagebox.showerror("Erro", str(erro), parent=janela)

def extrair_temperatura_ar(dispositivo):
    correspondencia = re.search(r"Temperatura:\s*(-?\d+)", str(dispositivo))
    return int(correspondencia.group(1)) if correspondencia else 24

def definir_temporizador(id_disp):
    dispositivo = casa.get_dispositivo(id_disp)
    if not isinstance(dispositivo, ArCondicionado):
        return
    minutos = simpledialog.askinteger(
        "Temporizador",
        "Tempo do temporizador em minutos:",
        parent=janela,
        minvalue=1,
    )
    if minutos is None:
        return
    try:
        mensagem = dispositivo.definir_temporizador(minutos)
        casa.salvar_estado()
        registrar_atividade(mensagem)
        atualizar_lista()
        atualizar_status(mensagem)
    except Exception as erro:
        messagebox.showerror("Erro", str(erro), parent=janela)

def cancelar_temporizador(id_disp):
    dispositivo = casa.get_dispositivo(id_disp)
    if not isinstance(dispositivo, ArCondicionado):
        return
    try:
        mensagem = dispositivo.cancelar_temporizador()
        casa.salvar_estado()
        registrar_atividade(mensagem)
        atualizar_lista()
        atualizar_status(mensagem)
    except Exception as erro:
        messagebox.showerror("Erro", str(erro), parent=janela)

def simular_presenca(id_disp, presenca):
    try:
        mensagem = casa.simular_presenca(id_disp, presenca)
        registrar_atividade(mensagem)
        atualizar_lista()
        atualizar_status(mensagem)
    except Exception as erro:
        messagebox.showerror("Erro", str(erro), parent=janela)

def atualizar_sensor_temperatura(id_disp):
    temperatura = simpledialog.askfloat(
        "Atualizar temperatura (Sensor de Temperatura)",
        "Nova temperatura:",
        parent=janela,
    )
    if temperatura is None:
        return
    try:
        casa.atualizar_sensor_temperatura(id_disp, temperatura)
        mensagem = "Temperatura atualizada."
        registrar_atividade(f"{mensagem} Sensor ID {id_disp}: {temperatura:.1f}°C.")
        atualizar_lista()
        atualizar_status(mensagem)
    except Exception as erro:
        messagebox.showerror("Erro", str(erro), parent=janela)

def mostrar_detalhes(id_disp=None):
    id_disp, dispositivo = obter_selecionado(id_disp)
    if dispositivo is None:
        return
    detalhes = (
        f"ID: {id_disp}\n"
        f"Nome: {dispositivo.get_nome()}\n"
        f"Cômodo: {obter_comodo(id_disp, dispositivo)}\n"
        f"Tipo: {nome_tipo(dispositivo)}\n"
        f"Estado: {'Ligado' if dispositivo.is_ligado() else 'Desligado'}\n\n"
        f"{dispositivo.testar_status()}"
    )
    if isinstance(dispositivo, ConexaoWiFi):
        detalhes += (
            f"\n\nRede Wi-Fi: {dispositivo.get_ssid()}"
            f"\nConexao: {obter_status_wifi(dispositivo)}"
        )
    messagebox.showinfo("Detalhes do dispositivo", detalhes, parent=janela)

def encontrar_dispositivo_comando(texto, id_asst, acao):
    itens = [(id_disp, disp) for id_disp, disp in casa.listar_dispositivos() if id_disp != id_asst]
    match_id = re.search(r"\b(?:id|dispositivo|numero)\s*(?:n[º°o.]?\s*)?(\d+)\b", texto)
    if match_id:
        candidato_id = int(match_id.group(1))
        for id_disp, _ in itens:
            if id_disp == candidato_id:
                return id_disp
        raise ValueError("Erro: Dispositivo não encontrado no sistema!")

    nomes = []
    for id_disp, disp in itens:
        nome = normalizar_texto(disp.get_nome()).strip()
        if nome and re.search(r"(?<!\w)" + re.escape(nome) + r"(?!\w)", texto):
            nomes.append((len(nome), id_disp))
    if nomes:
        maior = max(tamanho for tamanho, _ in nomes)
        correspondentes = [id_disp for tamanho, id_disp in nomes if tamanho == maior]
        if len(correspondentes) == 1:
            return correspondentes[0]
        return None

    # Se nao citar o nome, uma categoria unica pode ser escolhida sem adivinhacao.
    tipos = [
        (r"\b(?:lampada|luz|iluminacao)\b", LampadaInteligente),
        (r"\b(?:ar condicionado|climatizacao|ar)\b", ArCondicionado),
        (r"\b(?:sensor de presenca|sensor presenca)\b", SensorPresenca),
        (r"\b(?:sensor de temperatura|sensor temperatura)\b", SensorTemperatura),
    ]
    if acao == "cor":
        tipos.insert(0, (r"\bcor\b", LampadaInteligente))
    if acao == "temperatura" and re.search(r"\bsensor(?: de)? temperatura\b", texto):
        tipos.insert(0, (r"\bsensor(?: de)? temperatura\b", SensorTemperatura))
    elif acao in ("temperatura", "temporizador", "cancelar_temporizador"):
        tipos.insert(0, (r"\b(?:temperatura|graus|temporizador)\b", ArCondicionado))

    for padrao, classe in tipos:
        if re.search(padrao, texto):
            opcoes = [id_disp for id_disp, disp in itens if isinstance(disp, classe)]
            if len(opcoes) == 1:
                return opcoes[0]
            if len(opcoes) > 1:
                return None
    if len(itens) == 1:
        return itens[0][0]
    return None

def interpretar_acao_comando(texto):
    texto = normalizar_texto(texto)
    # Testar desligar antes de ligar evita a colisao presente em AssistenteVirtual.executar_comando().
    if re.search(r"\b(?:desligar|desliga|desligue|apagar|apaga|apague|desativar|desative)\b", texto):
        return "desligar", None
    if re.search(r"\b(?:ligar|liga|ligue|acender|acenda|ativar|ative)\b", texto):
        return "ligar", None
    if "temporizador" in texto:
        if re.search(r"\b(?:cancelar|cancele|remover|pare)\b", texto):
            return "cancelar_temporizador", None
        minutos = re.search(r"\b(\d+)\s*minutos?\b", texto)
        if minutos:
            return "temporizador", int(minutos.group(1))
    if re.search(r"\b(?:sem presenca|nenhuma presenca|nao detectou presenca)\b", texto):
        return "presenca", False
    if re.search(r"\b(?:presenca detectada|detectou presenca|simular presenca)\b", texto):
        return "presenca", True
    # Cores so sao trocadas quando a fala menciona cor ou uma acao de alteracao.
    cores = {
        "branca": "Branca", "branco": "Branca", "azul": "Azul",
        "amarelo": "Amarela", "amarela": "Amarela",
        "vermelho": "Vermelha", "vermelha": "Vermelha", "verde": "Verde",
    }
    if re.search(r"\b(?:cor|mudar|mude|trocar|troque|alterar|altere|deixe)\b", texto):
        for chave, cor_nova in cores.items():
            if re.search(r"\b" + chave + r"\b", texto):
                return "cor", cor_nova
    temperatura = re.search(r"\b(\d{1,2})(?:[.,](\d))?\s*(?:°\s*c|graus?|celsius)\b", texto)
    if temperatura:
        valor = float(temperatura.group(1) + ("." + temperatura.group(2) if temperatura.group(2) else ""))
        return "temperatura", valor
    return "nao_entendido", None

def acao_expressa(texto, acao):
    palavras = normalizar_texto(texto)
    verbos = {"ligar": r"(?:ligar|liga|ligue|acender|acenda|ativar|ative)",
              "desligar": r"(?:desligar|desliga|desligue|apagar|apaga|apague|desativar|desative)"}
    if acao in verbos:
        palavras = re.sub(r"\b" + verbos[acao] + r"\b", " ", palavras)
    palavras = re.sub(r"\b(?:alexa|por favor|os|as|o|a|da|do|de|na|no|em|para|por|dispositivos?|aparelhos?)\b", " ", palavras)
    return " ".join(palavras.split())

def identificar_comodo_texto(texto):
    texto = normalizar_texto(texto)
    locais = [local for local in lista_comodos() if local != "Sem Cômodo"]
    for local in sorted(locais, key=len, reverse=True):
        if re.search(r"(?<!\w)" + re.escape(normalizar_texto(local)) + r"(?!\w)", texto):
            return local
    return None

def tipo_mencionado(texto):
    texto = normalizar_texto(texto)
    if re.search(r"\b(?:lampada(?:s)?|luz(?:es)?|iluminacao)\b", texto):
        return LampadaInteligente
    if re.search(r"\b(?:ar condicionado|ares condicionados|climatizacao|ar)\b", texto):
        return ArCondicionado
    if re.search(r"\b(?:sensor(?:es)? de presenca|sensor(?:es)? presenca)\b", texto):
        return SensorPresenca
    if re.search(r"\b(?:sensor(?:es)? de temperatura|sensor(?:es)? temperatura)\b", texto):
        return SensorTemperatura
    if re.search(r"\bassistente\b", texto):
        return AssistenteVirtual
    return None

def resolver_alvos_comando(comando, id_asst, acao):
    texto = normalizar_texto(comando)
    itens = [(i, d) for i, d in casa.listar_dispositivos() if i != id_asst]
    if acao not in ("ligar", "desligar"):
        id_alvo = encontrar_dispositivo_comando(texto, id_asst, acao)
        return ([id_alvo] if id_alvo is not None else []), False

    correspondencia = re.search(r"\b(?:id|dispositivo|numero)\s*(?:n[º°o.]?\s*)?(\d+)\b", texto)
    if correspondencia:
        id_alvo = int(correspondencia.group(1))
        if id_alvo not in [i for i, _ in itens]:
            raise ValueError("Erro: Dispositivo não encontrado no sistema!")
        return [id_alvo], False

    local = identificar_comodo_texto(texto)
    tipo = tipo_mencionado(texto)
    geral = bool(re.search(r"\b(?:todos?|todas?|tudo|casa inteira|casa toda)\b", texto))
    restante = acao_expressa(comando, acao)
    local_puro = local is not None and (restante == normalizar_texto(local) or restante in ("todos " + normalizar_texto(local), "todas " + normalizar_texto(local)))

    # Nomes completos são prioridade: 'Lâmpada Sala' e 'Ar Sala' não se confundem.
    if not geral and not local_puro:
        nomes = []
        for id_disp, dispositivo in itens:
            nome = normalizar_texto(dispositivo.get_nome()).strip()
            if nome and re.search(r"(?<!\w)" + re.escape(nome) + r"(?!\w)", texto):
                nomes.append((len(nome), id_disp, dispositivo))
        if nomes:
            maior = max(t for t, _, _ in nomes)
            candidatos = [(i, d) for t, i, d in nomes if t == maior]
            if tipo is not None:
                candidatos_filtrados = [(i, d) for i, d in candidatos if isinstance(d, tipo)]
                if candidatos_filtrados:
                    candidatos = candidatos_filtrados
            if len(candidatos) == 1:
                return [candidatos[0][0]], False
            return [], False

    candidatos = itens
    if local:
        candidatos = [(i, d) for i, d in candidatos if normalizar_texto(obter_comodo(i, d)) == normalizar_texto(local)]
    if tipo is not None and not (re.search(r"\balexa\b", texto) and tipo is AssistenteVirtual and (geral or local)):
        candidatos = [(i, d) for i, d in candidatos if isinstance(d, tipo)]
    if geral or (local and tipo is None) or (local and re.search(r"\b(?:todos?|todas?)\b", texto)):
        # Se for sala inteira, o assistente também entra quando está nesse cômodo.
        if tipo is None:
            if not local or normalizar_texto(obter_comodo(id_asst)) == normalizar_texto(local):
                candidatos = candidatos + [(id_asst, casa.get_dispositivo(id_asst))]
        return [i for i, _ in candidatos], True
    if len(candidatos) == 1:
        return [candidatos[0][0]], False
    if tipo is None and local is None and len(itens) == 1:
        return [itens[0][0]], False
    return [], False

def executar_comando_assistente(id_asst, comando, origem="texto", mostrar_confirmacao=True):
    try:
        assistente = casa.get_dispositivo(id_asst)
        if not isinstance(assistente, AssistenteVirtual):
            return
        if not assistente.is_ligado():
            raise Exception(f"O assistente {assistente.get_nome()} está desligado e não pode ouvir comandos.")
        acao, valor = interpretar_acao_comando(comando)
        if acao == "nao_entendido":
            resultado = f"{assistente.get_nome()}: Desculpe, não entendi o comando."
        else:
            alvos, multiplo = resolver_alvos_comando(comando, id_asst, acao)
            if not alvos and multiplo:
                resultado = f"{assistente.get_nome()}: Nenhum dispositivo compatível encontrado."
            elif not alvos:
                if origem == "voz" and voz_modo_continuo:
                    resultado = "Informe o nome completo, o cômodo ou ID do dispositivo para executar o comando."
                else:
                    id_escolhido = escolher_dispositivo_alvo(excluir_id=id_asst)
                    if id_escolhido is None:
                        return
                    alvos = [id_escolhido]
            if alvos and multiplo and acao in ("ligar", "desligar"):
                # Processa o assistente por último, permitindo que ele desligue a si mesmo.
                alvos.sort(key=lambda i: i == id_asst)
                executados, inalterados, erros = [], [], []
                for id_alvo in alvos:
                    dispositivo = casa.get_dispositivo(id_alvo)
                    try:
                        ja_estado = dispositivo.is_ligado()
                        if (acao == "ligar" and ja_estado) or (acao == "desligar" and not ja_estado):
                            inalterados.append(dispositivo.get_nome().title())
                            continue
                        if acao == "ligar":
                            casa.ligar_dispositivo(id_alvo)
                        else:
                            casa.desligar_dispositivo(id_alvo)
                        executados.append(dispositivo.get_nome().title())
                        registrar_atividade(f"{dispositivo.get_nome()} {'ligado' if acao == 'ligar' else 'desligado'} com sucesso!")
                        if id_alvo == voz_id_assistente and acao == "desligar":
                            parar_escuta_voz()
                    except Exception as erro:
                        erros.append(f"{dispositivo.get_nome().title()}: {erro}")
                verbo = "ligados" if acao == "ligar" else "desligados"
                resultado = (f"{assistente.get_nome()}: {len(executados)} dispositivo(s) {verbo}; "
                             f"{len(inalterados)} já estavam no estado solicitado.")
                if erros:
                    resultado += " Erros: " + "; ".join(erros)
            elif alvos:
                id_alvo = alvos[0]
                dispositivo = casa.get_dispositivo(id_alvo)
                try:
                    if acao == "ligar":
                        resultado = assistente.executar_comando("ligar", id_alvo, casa)
                    elif acao == "desligar":
                        casa.desligar_dispositivo(id_alvo)
                        resultado = f"{assistente.get_nome()}: Ok, desliguei o dispositivo {id_alvo}."
                        if id_alvo == voz_id_assistente:
                            parar_escuta_voz()
                    elif acao == "cor" and isinstance(dispositivo, LampadaInteligente):
                        dispositivo.mudar_cor(valor)
                        casa.salvar_estado()
                        resultado = "Cor alterada."
                    elif acao == "temperatura" and isinstance(dispositivo, ArCondicionado):
                        if int(valor) != valor:
                            raise ValueError("Erro: Temperatura inválida! Escolha entre 16°C e 30°C.")
                        dispositivo.ajustar_temperatura(int(valor))
                        casa.salvar_estado()
                        resultado = "Temperatura ajustada."
                    elif acao == "temperatura" and isinstance(dispositivo, SensorTemperatura):
                        casa.atualizar_sensor_temperatura(id_alvo, valor)
                        resultado = "Temperatura atualizada."
                    elif acao == "presenca" and isinstance(dispositivo, SensorPresenca):
                        resultado = casa.simular_presenca(id_alvo, valor)
                    elif acao == "temporizador" and isinstance(dispositivo, ArCondicionado):
                        resultado = dispositivo.definir_temporizador(valor)
                        casa.salvar_estado()
                    elif acao == "cancelar_temporizador" and isinstance(dispositivo, ArCondicionado):
                        resultado = dispositivo.cancelar_temporizador()
                        casa.salvar_estado()
                    else:
                        raise TypeError(f"O dispositivo {dispositivo.get_nome().title()} não aceita esse comando.")
                except Exception as erro:
                    resultado = f"{assistente.get_nome()}: Não consegui executar. {str(erro)}"
        registrar_atividade(resultado)
        atualizar_lista()
        atualizar_status(resultado)
        if origem == "voz":
            texto_ultimo_comando.set(f"Você disse: {comando}   |   {resultado}")
        if mostrar_confirmacao:
            messagebox.showinfo("Assistente Virtual", resultado, parent=janela)
        return resultado
    except Exception as erro:
        texto_ultimo_comando.set(str(erro))
        atualizar_status(str(erro))
        if mostrar_confirmacao:
            messagebox.showerror("Assistente Virtual", str(erro), parent=janela)
        return str(erro)

def comando_manual_assistente(id_asst):
    assistente = casa.get_dispositivo(id_asst)
    if not assistente.is_ligado():
        messagebox.showerror(
            "Assistente Virtual",
            f"O assistente {assistente.get_nome()} está desligado e não pode ouvir comandos.",
            parent=janela,
        )
        return
    comando = simpledialog.askstring(
        "Usar Assistente Virtual (Comando de Voz)",
        "Digite o comando (ex: 'ligar', 'desligar') e, se quiser, o nome do dispositivo:",
        parent=janela,
    )
    if comando:
        executar_comando_assistente(id_asst, comando)

def iniciar_comando_voz(id_asst, continuo=False):
    global voz_em_execucao, voz_modo_continuo, voz_sessao, voz_evento_parar, voz_id_assistente
    if voz_em_execucao:
        atualizar_status("O microfone já está em uso. Encerre a escuta antes de iniciar outra.")
        return
    if sr is None:
        messagebox.showwarning(
            "Reconhecimento de voz",
            'Instale as dependências no VS Code:\n\npython -m pip install SpeechRecognition PyAudioWPatch\n\nReinicie a interface após a instalação.',
            parent=janela,
        )
        return
    try:
        assistente = casa.get_dispositivo(id_asst)
        if not isinstance(assistente, AssistenteVirtual):
            return
        if not assistente.is_ligado():
            raise Exception(f"O assistente {assistente.get_nome()} está desligado e não pode ouvir comandos.")
    except Exception as erro:
        messagebox.showerror("Assistente Virtual", str(erro), parent=janela)
        return

    voz_sessao += 1
    sessao = voz_sessao
    voz_evento_parar = threading.Event()
    voz_em_execucao = True
    voz_modo_continuo = continuo
    voz_id_assistente = id_asst
    texto_estado_voz.set("Iniciando microfone...")
    atualizar_status("Preparando o microfone...")
    atualizar_lista()

    def ouvir_microfone():
        reconhecedor = sr.Recognizer()
        reconhecedor.dynamic_energy_threshold = True
        reconhecedor.pause_threshold = 0.9
        reconhecedor.operation_timeout = 8
        try:
            with sr.Microphone(device_index=microfone_indice) as microfone:
                fila_voz.put(("estado", sessao, "Calibrando microfone, aguarde..."))
                reconhecedor.adjust_for_ambient_noise(microfone, duration=0.7)
                while not voz_evento_parar.is_set():
                    fila_voz.put(("estado", sessao, "Ouvindo... fale claramente próximo ao microfone."))
                    try:
                        audio = reconhecedor.listen(microfone, timeout=3 if continuo else 7, phrase_time_limit=7)
                    except sr.WaitTimeoutError:
                        if not continuo:
                            fila_voz.put(("falha", sessao, "Nenhum comando foi detectado. Tente novamente."))
                        continue
                    if voz_evento_parar.is_set():
                        break
                    fila_voz.put(("estado", sessao, "Reconhecendo a fala..."))
                    try:
                        comando = reconhecedor.recognize_google(audio, language="pt-BR")
                    except sr.UnknownValueError:
                        fila_voz.put(("falha", sessao, "Não foi possível entender o comando. Tente novamente."))
                    except sr.RequestError as erro:
                        fila_voz.put(("erro", sessao, f"Falha no serviço de reconhecimento. Confira sua conexão com a internet.\n\n{erro}"))
                        break
                    else:
                        if not voz_evento_parar.is_set():
                            fila_voz.put(("comando", sessao, comando))
                    if not continuo:
                        break
        except Exception as erro:
            fila_voz.put(("erro", sessao, f"Não foi possível acessar o microfone. Confira o dispositivo selecionado, o PyAudio e as permissões de microfone do Windows.\n\n{erro}"))
        finally:
            fila_voz.put(("fim", sessao, None))

    threading.Thread(target=ouvir_microfone, daemon=True, name="Casa-Assistente-Voz").start()

def parar_escuta_voz():
    if voz_em_execucao:
        voz_evento_parar.set()
        texto_estado_voz.set("Encerrando escuta...")
        atualizar_status("Encerrando escuta...")

def processar_eventos_voz():
    global voz_em_execucao, voz_modo_continuo, voz_id_assistente
    try:
        while True:
            tipo, sessao, dado = fila_voz.get_nowait()
            if sessao != voz_sessao:
                continue
            if tipo == "estado" and not voz_evento_parar.is_set():
                texto_estado_voz.set(dado)
            elif tipo == "comando" and not voz_evento_parar.is_set():
                id_asst = voz_id_assistente
                if id_asst is None:
                    continue
                texto_normalizado = normalizar_texto(dado)
                nome_assistente = normalizar_texto(casa.get_dispositivo(id_asst).get_nome())
                # Em escuta continua, a palavra de ativacao impede executar conversas aleatorias.
                if voz_modo_continuo and not any(
                    re.search(r"(?<!\w)" + re.escape(chamada) + r"(?!\w)", texto_normalizado)
                    for chamada in (nome_assistente, "alexa") if chamada
                ):
                    texto_ultimo_comando.set(f"Ignorado (sem chamar Alexa): {dado}")
                else:
                    texto_estado_voz.set("Comando reconhecido.")
                    texto_ultimo_comando.set(f"Você disse: {dado}")
                    executar_comando_assistente(id_asst, dado, origem="voz", mostrar_confirmacao=False)
            elif tipo == "falha" and not voz_evento_parar.is_set():
                texto_ultimo_comando.set(dado)
                atualizar_status(dado)
            elif tipo == "erro" and not voz_evento_parar.is_set():
                texto_ultimo_comando.set(dado)
                atualizar_status("Falha no reconhecimento de voz.")
                messagebox.showerror("Reconhecimento de voz", dado, parent=janela)
            elif tipo == "fim":
                voz_em_execucao = False
                voz_modo_continuo = False
                voz_id_assistente = None
                texto_estado_voz.set("Microfone em espera. Clique em Ouvir para começar.")
                atualizar_lista()
    except queue.Empty:
        pass
    if janela.winfo_exists():
        janela.after(120, processar_eventos_voz)

def fechar_interface():
    voz_evento_parar.set()
    janela.destroy()

def limpar_historico():
    confirmar = messagebox.askyesno("Limpar historico", "Deseja apagar o historico de atividades?", parent=janela)
    if not confirmar:
        return
    historico_atividades.clear()
    try:
        with open(HISTORICO_ARQUIVO, "w", encoding="utf-8"):
            pass
    except OSError:
        pass
    atualizar_lista()
    atualizar_status("Historico de atividades limpo.")

# --------------- Janelas de entrada e formulários CustomTkinter -----------
def janela_modal(titulo, tamanho="490x300", minimo=None):
    dialogo = ctk.CTkToplevel(janela)
    dialogo.title(titulo)
    dialogo.geometry(tamanho)
    dialogo.configure(fg_color=cor("fundo"))
    if minimo:
        dialogo.minsize(*minimo)
    else:
        dialogo.resizable(False, False)
    dialogo.transient(janela)
    dialogo.after(100, lambda: dialogo.grab_set() if dialogo.winfo_exists() else None)
    dialogo.after(120, lambda: dialogo.focus_force() if dialogo.winfo_exists() else None)
    return dialogo


def _pedir_valor(titulo, pergunta, parent=None, show=None, initialvalue=None,
                 minvalue=None, maxvalue=None, tipo="texto"):
    resposta = {"valor": None}
    dialogo = janela_modal(titulo, "475x265")
    box = caixa(dialogo)
    box.pack(fill="both", expand=True, padx=23, pady=20)
    criar_rotulo(box, titulo, 18, "bold").pack(anchor="w", pady=(0, 8))
    criar_rotulo(box, pergunta, 11, cor_texto=cor("texto_fraco"),
                 wraplength=400, justify="left").pack(anchor="w", pady=(0, 15))
    var = tk.StringVar(master=dialogo, value="" if initialvalue is None else str(initialvalue))
    entrada = ctk.CTkEntry(box, textvariable=var, show=show or "", fg_color=cor("entrada"),
                           border_color=cor("borda"), text_color=cor("texto"),
                           height=43, corner_radius=11, font=fonte(12))
    entrada.pack(fill="x")
    entrada.focus_set()

    def confirmar(_e=None):
        texto = var.get()
        if tipo != "texto":
            try:
                convertido = int(texto) if tipo == "inteiro" else float(texto)
            except (ValueError, OverflowError):
                messagebox.showerror("Valor inválido", "Digite um número válido.", parent=dialogo)
                return
            if minvalue is not None and convertido < minvalue or maxvalue is not None and convertido > maxvalue:
                messagebox.showerror("Valor inválido", f"Digite um valor entre {minvalue if minvalue is not None else '-∞'} e {maxvalue if maxvalue is not None else '+∞'}.", parent=dialogo)
                return
            resposta["valor"] = convertido
        else:
            resposta["valor"] = texto
        dialogo.destroy()
    rodape = caixa(box)
    rodape.pack(fill="x", pady=(18, 0))
    criar_botao(rodape, "Cancelar", dialogo.destroy, "suave", True).pack(side="right")
    criar_botao(rodape, "Confirmar", confirmar, "primario", True).pack(side="right", padx=(0, 8))
    dialogo.bind("<Return>", confirmar)
    dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
    dialogo.wait_window()
    return resposta["valor"]

class Dialogos:
    @staticmethod
    def askstring(titulo, pergunta, parent=None, show=None, initialvalue=None, **_kwargs):
        return _pedir_valor(titulo, pergunta, parent, show=show, initialvalue=initialvalue)

    @staticmethod
    def askinteger(titulo, pergunta, parent=None, initialvalue=None, minvalue=None, maxvalue=None, **_kwargs):
        return _pedir_valor(titulo, pergunta, parent, initialvalue=initialvalue, minvalue=minvalue,
                            maxvalue=maxvalue, tipo="inteiro")

    @staticmethod
    def askfloat(titulo, pergunta, parent=None, initialvalue=None, minvalue=None, maxvalue=None, **_kwargs):
        return _pedir_valor(titulo, pergunta, parent, initialvalue=initialvalue, minvalue=minvalue,
                            maxvalue=maxvalue, tipo="real")

simpledialog = Dialogos


def selecionar_comodo_dialogo(titulo, atual="Sem Cômodo"):
    resultado = {"valor": None}
    dialogo = janela_modal(titulo, "480x275")
    corpo = caixa(dialogo)
    corpo.pack(fill="both", expand=True, padx=26, pady=23)
    criar_rotulo(corpo, "Onde está o dispositivo?", 19, "bold").pack(anchor="w")
    criar_rotulo(corpo, "Escolha um cômodo ou digite outro nome.", 11, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(7, 18))
    escolha = tk.StringVar(master=dialogo, value=atual)
    entrada = ctk.CTkComboBox(corpo, variable=escolha, values=COMODOS_SUGESTOES,
                             fg_color=cor("entrada"), border_color=cor("borda"),
                             button_color=cor("azul_escuro"), button_hover_color=cor("azul"),
                             text_color=cor("texto"), font=fonte(12), height=42, corner_radius=11)
    entrada.pack(fill="x")
    entrada.focus_set()

    def salvar(_evento=None):
        resultado["valor"] = formatar_comodo(escolha.get())
        dialogo.destroy()

    criar_botao(corpo, "Confirmar cômodo", salvar, "primario").pack(fill="x", pady=(19, 0))
    dialogo.bind("<Return>", salvar)
    dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
    dialogo.wait_window()
    return resultado["valor"]


def adicionar_dispositivo():
    # --------------- Cadastro CTk; mantém mesmas classes, defaults e mensagens -----------
    dialogo = janela_modal("Adicionar dispositivo", "590x730", (510, 590))
    cab = caixa(dialogo)
    cab.pack(fill="x", padx=28, pady=(20, 12))
    criar_rotulo(cab, "Novo dispositivo", 25, "bold").pack(anchor="w")
    criar_rotulo(cab, "Escolha a categoria, personalize e organize por cômodo.", 11,
                 cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(6, 0))
    scroll = ctk.CTkScrollableFrame(dialogo, fg_color=cor("superficie"),
                                    corner_radius=18, border_width=1,
                                    border_color=cor("borda"))
    scroll.pack(fill="both", expand=True, padx=25, pady=(0, 12))
    valores = {
        "tipo": tk.StringVar(master=dialogo, value="lampada"),
        "nome": tk.StringVar(master=dialogo, value=""),
        "comodo": tk.StringVar(master=dialogo, value="Sala"),
        "cor": tk.StringVar(master=dialogo, value="Branca"),
        "temperatura": tk.StringVar(master=dialogo, value="24"),
        "ssid": tk.StringVar(master=dialogo, value="Casa"),
        "senha": tk.StringVar(master=dialogo, value="12345678"),
    }
    form = caixa(scroll)
    form.pack(fill="x", padx=16, pady=18)

    def campo(label, var, valores_combo=None, secreto=False, editavel=True, pai=form):
        criar_rotulo(pai, label, 11, "bold", cor("texto_fraco")).pack(anchor="w", pady=(0, 6))
        if valores_combo is not None:
            widget = ctk.CTkComboBox(pai, variable=var, values=valores_combo,
                                    state="normal" if editavel else "readonly",
                                    fg_color=cor("entrada"), text_color=cor("texto"),
                                    border_color=cor("borda"), button_color=cor("azul_escuro"),
                                    height=42, corner_radius=11, font=fonte(12))
        else:
            widget = ctk.CTkEntry(pai, textvariable=var, show="*" if secreto else "",
                                 height=42, corner_radius=11, font=fonte(12),
                                 fg_color=cor("entrada"), border_color=cor("borda"),
                                 text_color=cor("texto"))
        widget.pack(fill="x", pady=(0, 16))
        return widget

    campo("Tipo de dispositivo", valores["tipo"],
          ["lampada", "ar", "presenca", "temperatura", "assistente"], editavel=False)
    nome_entrada = campo("Nome do dispositivo", valores["nome"])
    campo("Cômodo", valores["comodo"], COMODOS_SUGESTOES)
    extras = caixa(form)
    extras.pack(fill="x")

    def adicionar_campo_extra(titulo, nome, esconder=""):
        campo(titulo, valores[nome], secreto=bool(esconder), pai=extras)

    def atualizar_campos(*_):
        for filho in extras.winfo_children():
            filho.destroy()
        tipo = valores["tipo"].get()
        if tipo == "assistente" and not valores["nome"].get().strip():
            valores["nome"].set("Alexa")
        if tipo == "lampada":
            adicionar_campo_extra("Cor inicial", "cor")
        if tipo in ("ar", "temperatura"):
            adicionar_campo_extra("Temperatura inicial", "temperatura")
        if tipo in ("lampada", "ar", "presenca"):
            adicionar_campo_extra("Rede Wi-Fi", "ssid")
            adicionar_campo_extra("Senha Wi-Fi", "senha", esconder="*")

    valores["tipo"].trace_add("write", atualizar_campos)
    atualizar_campos()
    if pagina_atual in ("lampadas", "ar", "sensores", "assistentes"):
        valores["tipo"].set({"lampadas": "lampada", "ar": "ar", "sensores": "presenca", "assistentes": "assistente"}[pagina_atual])
    if pagina_atual == "comodo" and comodo_ativo:
        valores["comodo"].set(comodo_ativo)

    def confirmar():
        tipo = valores["tipo"].get()
        nome = " ".join(valores["nome"].get().split()).title()
        if not nome:
            messagebox.showwarning("Campo obrigatório", "O nome não pode ficar vazio.", parent=dialogo)
            return
        try:
            if tipo == "lampada":
                disp = LampadaInteligente(nome, valores["cor"].get().strip().title() or "Branca")
            elif tipo == "ar":
                disp = ArCondicionado(nome, int(valores["temperatura"].get()))
            elif tipo == "presenca":
                disp = SensorPresenca(nome)
            elif tipo == "temperatura":
                disp = SensorTemperatura(nome, float(valores["temperatura"].get().replace(",", ".")))
            elif tipo == "assistente":
                disp = AssistenteVirtual(nome)
            else:
                raise ValueError("Tipo inválido!")
            if isinstance(disp, ConexaoWiFi):
                ssid = valores["ssid"].get().strip()
                if not ssid:
                    raise ValueError("O nome da rede não pode ficar vazio.")
                ConexaoWiFi.__init__(disp, ssid, valores["senha"].get())
            id_disp = max(casa.listar_ids_dispositivos(), default=0) + 1
            casa.adicionar_dispositivo(id_disp, disp)
            locais_dispositivos[str(id_disp)] = formatar_comodo(valores["comodo"].get())
            salvar_comodos()
            mensagem = f"Dispositivo '{nome}' adicionado com sucesso! (ID interno: {id_disp})"
            registrar_atividade(mensagem)
            dialogo.destroy()
            navegar_para(categoria_dispositivo(disp))
            atualizar_status(mensagem)
        except Exception as erro:
            messagebox.showerror("Erro ao cadastrar", str(erro), parent=dialogo)

    acoes = caixa(dialogo)
    acoes.pack(fill="x", padx=25, pady=(0, 19))
    criar_botao(acoes, "+  Adicionar dispositivo", confirmar, "primario", altura=46).pack(fill="x")
    dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
    dialogo.protocol("WM_DELETE_WINDOW", dialogo.destroy)
    nome_entrada.focus_set()


def escolher_dispositivo_alvo(excluir_id=None, tipo=None):
    dispositivos = [(i, d) for i, d in casa.listar_dispositivos()
                    if i != excluir_id and (tipo is None or isinstance(d, tipo))]
    if not dispositivos:
        messagebox.showwarning("Assistente Virtual", "Nenhum dispositivo compatível encontrado.", parent=janela)
        return None
    dialogo = janela_modal("Qual dispositivo deseja controlar?", "540x280")
    corpo = caixa(dialogo)
    corpo.pack(fill="both", expand=True, padx=22, pady=19)
    criar_rotulo(corpo, "Qual dispositivo deseja controlar?", 17, "bold").pack(anchor="w", pady=(0, 15))
    opcoes = [f"{i} - {d.get_nome().title()} ({nome_tipo(d)})" for i, d in dispositivos]
    selecionado = tk.StringVar(master=dialogo, value=opcoes[0])
    menu = ctk.CTkComboBox(corpo, variable=selecionado, values=opcoes,
                           state="readonly", fg_color=cor("entrada"),
                           text_color=cor("texto"), border_color=cor("borda"),
                           height=42, font=fonte(12))
    menu.pack(fill="x")
    resultado = {"id": None}
    def confirmar():
        try: resultado["id"] = int(selecionado.get().split(" - ", 1)[0])
        except (ValueError, IndexError): resultado["id"] = None
        dialogo.destroy()
    criar_botao(corpo, "Selecionar", confirmar, "primario").pack(fill="x", pady=(20, 0))
    dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
    dialogo.wait_window()
    return resultado["id"]


def configurar_microfone():
    global microfone_indice
    if sr is None:
        messagebox.showwarning("Reconhecimento de voz",
            "Instale o microfone com:\n\npython -m pip install SpeechRecognition PyAudioWPatch", parent=janela)
        return
    try:
        nomes = sr.Microphone.list_microphone_names()
    except Exception as erro:
        messagebox.showerror("Microfone", f"Não foi possível listar os microfones. Verifique o PyAudio e as permissões do Windows.\n\n{erro}", parent=janela)
        return
    if not nomes:
        messagebox.showwarning("Microfone", "Nenhum microfone encontrado no sistema.", parent=janela)
        return
    dialogo = janela_modal("Selecionar microfone", "610x295")
    corpo = caixa(dialogo)
    corpo.pack(fill="both", expand=True, padx=24, pady=20)
    criar_rotulo(corpo, "Selecione a entrada de áudio", 18, "bold").pack(anchor="w", pady=(0, 15))
    opcoes = ["Padrão do sistema"] + [f"{i} - {nome or 'Microfone sem nome'}" for i, nome in enumerate(nomes)]
    selecionado = tk.StringVar(master=dialogo,
        value=f"{microfone_indice} - {nomes[microfone_indice]}" if microfone_indice is not None and microfone_indice < len(nomes) else opcoes[0])
    menu = ctk.CTkComboBox(corpo, variable=selecionado, values=opcoes, state="readonly",
                           fg_color=cor("entrada"), text_color=cor("texto"),
                           border_color=cor("borda"), font=fonte(12), height=43)
    menu.pack(fill="x")

    def confirmar():
        global microfone_indice
        microfone_indice = None if selecionado.get() == opcoes[0] else int(selecionado.get().split(" - ", 1)[0])
        texto_estado_voz.set("Microfone configurado. Pronto para ouvir.")
        atualizar_status("Microfone configurado.")
        dialogo.destroy()

    criar_botao(corpo, "Usar microfone", confirmar, "primario").pack(fill="x", pady=(18, 0))
    dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
    dialogo.protocol("WM_DELETE_WINDOW", dialogo.destroy)



# --------------- Design CustomTkinter: páginas, cartões e cores -----------
CATEGORIAS = {
    "lampadas": ("Iluminação", "☀", "amarelo", "Controle as lâmpadas e personalize as cores."),
    "ar": ("Climatização", "❄", "ciano", "Ajuste a temperatura e os temporizadores."),
    "sensores": ("Sensores", "◉", "roxo", "Monitore presença e temperatura."),
    "assistentes": ("Assistente Virtual", "◌", "azul", "Comandos digitados ou com o microfone."),
}

def fundo_icone(chave):
    escuros = {"amarelo": "#463822", "ciano": "#153A4D", "roxo": "#352D53",
                "azul": "#243F70", "verde": "#173C34", "laranja": "#513626", "vermelho": "#4A2B38"}
    claros = {"amarelo": "#FFF2D6", "ciano": "#D9F5FF", "roxo": "#EEE8FF",
              "azul": "#E3EEFF", "verde": "#DDF6EC", "laranja": "#FFEBDB", "vermelho": "#FFE7EB"}
    return (escuros if tema_atual == "escuro" else claros).get(chave, cor("superficie_2"))


def criar_icone(pai, simbolo, destaque, tamanho=48, fonte_icone=24):
    bloco = ctk.CTkFrame(pai, width=tamanho, height=tamanho, fg_color=fundo_icone(destaque), corner_radius=16)
    bloco.pack_propagate(False)
    criar_rotulo(bloco, simbolo, fonte_icone, "bold", cor(destaque)).pack(expand=True)
    return bloco


def criar_indicador(pai, estado, texto):
    linha = caixa(pai)
    cor_ponto = cor("verde") if estado == "Conectado" else cor("vermelho") if estado == "Desconectado" else cor("texto_sutil")
    ponto = ctk.CTkFrame(linha, width=9, height=9, fg_color=cor_ponto, corner_radius=5)
    ponto.pack(side="left", padx=(0, 8))
    criar_rotulo(linha, texto, 10, cor_texto=cor("texto_fraco")).pack(side="left")
    return linha


def animar_faixa(pai, destaque):
    faixa = ctk.CTkFrame(pai, width=14, height=4, fg_color=cor(destaque), corner_radius=3)
    faixa.pack(anchor="w", pady=(12, 0))
    def passo(largura=14):
        if not faixa.winfo_exists(): return
        faixa.configure(width=largura)
        if largura < 88:
            faixa.after(16, lambda: passo(min(88, largura + 7)))
    faixa.after(30, passo)


def navegar_para(chave, local=None):
    global pagina_atual, comodo_ativo
    pagina_atual = chave
    comodo_ativo = local if chave == "comodo" else None
    renderizar_painel()
    try:
        painel_scroll._parent_canvas.yview_moveto(0)
    except (AttributeError, tk.TclError):
        pass
    if label_caminho is not None and label_caminho.winfo_exists():
        titulo = (CATEGORIAS[chave][0] if chave in CATEGORIAS else
                  "Visão geral" if chave == "inicio" else
                  "Atividades" if chave == "atividade" else comodo_ativo or "Cômodos")
        label_caminho.configure(text="Meu lar  /  " + titulo)
    for nome, botao in list(menu_botoes.items()):
        if not botao.winfo_exists(): continue
        ativo = nome == chave
        destaque = CATEGORIAS[nome][2] if nome in CATEGORIAS else "azul"
        fundo = cor("superficie_2") if ativo else cor("lateral")
        botao._normal = fundo
        botao._hover = misturar_cor(fundo, "#FFFFFF" if tema_atual == "escuro" else "#192F5A", .14 if tema_atual == "escuro" else .08)
        botao.configure(fg_color=fundo, text_color=cor(destaque) if ativo else cor("texto_fraco"))


def criar_hero(pai, dispositivos, ligados, conectados):
    # --------------- Banner com composição CTk, sem Canvas pesado -----------
    hero = ctk.CTkFrame(pai, fg_color=cor("hero"), corner_radius=26, height=200)
    hero.pack(fill="x", pady=(2, 8))
    hero.pack_propagate(False)
    esquerda = caixa(hero)
    esquerda.pack(side="left", fill="both", expand=True, padx=(29, 8), pady=26)
    ctk.CTkLabel(esquerda, text="●  CASA INTELIGENTE  /  PAINEL PRINCIPAL",
                 text_color="#D9E8FF", font=fonte(10, "bold")).pack(anchor="w", pady=(0, 11))
    ctk.CTkLabel(esquerda, text="Sua casa, do seu jeito.", text_color="#FFFFFF",
                 font=fonte(28, "bold")).pack(anchor="w")
    ctk.CTkLabel(esquerda, text="Veja o que está acontecendo e acesse seus ambientes.",
                 text_color="#E5EFFF", font=fonte(12), wraplength=435, justify="left").pack(anchor="w", pady=(10, 15))
    ctk.CTkLabel(esquerda, text=f"{len(dispositivos)} dispositivos     •     {ligados} ligados     •     {conectados} no Wi-Fi",
                 text_color="#FFFFFF", font=fonte(12, "bold")).pack(anchor="w")
    direita = ctk.CTkFrame(hero, fg_color=cor("hero_2"), corner_radius=22,
                           width=164, height=152)
    direita.pack(side="right", padx=(0, 25), pady=24)
    direita.pack_propagate(False)
    criar_rotulo(direita, "⌂", 49, "bold", "#FFFFFF").pack(pady=(11, 0))
    criar_rotulo(direita, "MEU LAR", 11, "bold", "#E7F0FF").pack(pady=(3, 0))
    criar_rotulo(direita, "Tudo em um só lugar", 10, cor_texto="#E7F0FF").pack(pady=(3, 0))
    return hero


def criar_card_resumo(pai, titulo, numero, detalhe, cor_chave, simbolo, coluna):
    card = criar_cartao(pai)
    card.grid(row=0, column=coluna, sticky="nsew", padx=(0, 11) if coluna < 3 else 0, pady=4)
    miolo = caixa(card)
    miolo.pack(fill="both", expand=True, padx=17, pady=15)
    criar_icone(miolo, simbolo, cor_chave, 41, 22).pack(anchor="w")
    criar_rotulo(miolo, str(numero), 29, "bold").pack(anchor="w", pady=(9, 0))
    criar_rotulo(miolo, titulo, 12, "bold").pack(anchor="w")
    criar_rotulo(miolo, detalhe, 10, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(5, 0))


def criar_atalho_categoria(pai, chave, indice):
    titulo, simbolo, destaque, descricao = CATEGORIAS[chave]
    itens = dispositivos_categoria(chave)
    card = criar_cartao(pai)
    card.grid(row=indice // 2, column=indice % 2, sticky="nsew",
              padx=(0, 8) if indice % 2 == 0 else (8, 0), pady=8)
    area = caixa(card)
    area.pack(fill="both", expand=True, padx=18, pady=18)
    topo = caixa(area)
    topo.pack(fill="x")
    criar_icone(topo, simbolo, destaque, 55, 26).pack(side="left")
    infos = caixa(topo)
    infos.pack(side="left", padx=15, expand=True, fill="x")
    criar_rotulo(infos, titulo, 16, "bold").pack(anchor="w")
    criar_rotulo(infos, f"{len(itens)} dispositivo(s)", 10, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(4, 0))
    criar_rotulo(area, descricao, 11, cor_texto=cor("texto_fraco"),
                 wraplength=380, justify="left").pack(anchor="w", pady=(15, 10))
    criar_botao(area, "Explorar categoria  →", lambda chave=chave: navegar_para(chave), "suave", True,
                largura=170).pack(anchor="w")


def criar_atalho_comodo(pai, local, indice):
    itens = dispositivos_comodo(local)
    ligados = sum(d.is_ligado() for _, d in itens)
    card = criar_cartao(pai)
    card.grid(row=indice // 3, column=indice % 3, sticky="nsew",
              padx=(0, 9) if indice % 3 < 2 else 0, pady=7)
    conteudo = caixa(card)
    conteudo.pack(fill="x", padx=16, pady=16)
    criar_icone(conteudo, "⌂", "azul", 45, 23).pack(anchor="w")
    criar_rotulo(conteudo, local, 14, "bold").pack(anchor="w", pady=(8, 0))
    criar_rotulo(conteudo, f"{len(itens)} dispositivos  •  {ligados} ligados", 10,
                 cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(6, 12))
    criar_botao(conteudo, "Ver ambiente  →", lambda l=local: navegar_para("comodo", l),
                "suave", True, largura=140).pack(anchor="w")


def criar_grade_dispositivos(pai, itens):
    if not itens:
        aviso = criar_cartao(pai)
        aviso.pack(fill="x", pady=5)
        area = caixa(aviso)
        area.pack(fill="x", padx=23, pady=24)
        criar_rotulo(area, "Nenhum dispositivo cadastrado nesta categoria.", 14, "bold").pack(anchor="w")
        criar_rotulo(area, "Use Adicionar dispositivo para começar.", 11, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(7, 0))
        return
    grade = caixa(pai)
    grade.pack(fill="x")
    for n, (ident, disp) in enumerate(itens):
        cartao = criar_cartao_dispositivo(grade, ident, disp)
        cartao.grid(row=n // 2, column=n % 2, padx=(0, 8) if n % 2 == 0 else (8, 0), pady=8, sticky="nsew")
    grade.grid_columnconfigure(0, weight=1, uniform="dispositivos")
    grade.grid_columnconfigure(1, weight=1, uniform="dispositivos")


def criar_cartao_dispositivo(pai, id_disp, dispositivo):
    # --------------- Dispositivos: controles originais com cartões novos -----------
    card = criar_cartao(pai)
    miolo = caixa(card)
    miolo.pack(fill="both", expand=True, padx=17, pady=17)
    simbolo, destaque = obter_icone(dispositivo)
    # Usa símbolos simples e compatíveis com fontes de várias plataformas.
    simbolos = {"Lâmpada Inteligente": "☀", "Ar Condicionado": "❄",
                "Sensor de Presença": "◉", "Sensor de Temperatura": "♨", "Assistente Virtual": "◌"}
    simbolo = simbolos.get(nome_tipo(dispositivo), simbolo)
    cab = caixa(miolo)
    cab.pack(fill="x")
    criar_icone(cab, simbolo, destaque, 50, 24).pack(side="left")
    nomes = caixa(cab)
    nomes.pack(side="left", fill="x", expand=True, padx=(12, 0))
    criar_rotulo(nomes, dispositivo.get_nome().title(), 14, "bold", wraplength=215,
                 anchor="w", justify="left").pack(anchor="w")
    criar_rotulo(nomes, f"{nome_tipo(dispositivo)}  •  ID {id_disp}", 10,
                 cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(4, 0))
    criar_rotulo(miolo, "", 1).pack(pady=(1, 0))
    status = caixa(miolo)
    status.pack(fill="x", pady=(5, 4))
    ligado = dispositivo.is_ligado()
    rotulo_pill(status, "●  " + ("Ligado" if ligado else "Desligado"),
                "verde" if ligado else "vermelho").pack(side="left")
    criar_botao(status, "⌖  " + obter_comodo(id_disp, dispositivo),
                lambda i=id_disp: editar_comodo(i), "suave", True,
                largura=115).pack(side="right")
    wifi = obter_status_wifi(dispositivo)
    criar_indicador(miolo, wifi, "Wi-Fi: " + wifi).pack(anchor="w", pady=(7, 8))
    titulo = dispositivo.get_nome().title()
    descricao = dispositivo.testar_status() if ligado else f"{titulo} está desligado."
    criar_rotulo(miolo, descricao, 10, cor_texto=cor("texto_fraco"),
                 justify="left", anchor="w", wraplength=335).pack(anchor="w", pady=(4, 10))
    ctk.CTkFrame(miolo, height=1, fg_color=cor("borda")).pack(fill="x", pady=(5, 13))
    acoes = caixa(miolo)
    acoes.pack(fill="x")
    if ligado:
        criar_botao(acoes, "●  Desligar", lambda i=id_disp: desligar_dispositivo(i), "perigo", True,
                    largura=91).pack(side="left", padx=(0, 5))
    else:
        criar_botao(acoes, "●  Ligar", lambda i=id_disp: ligar_dispositivo(i), "positivo", True,
                    largura=91).pack(side="left", padx=(0, 5))
    criar_botao(acoes, "Detalhes", lambda i=id_disp: mostrar_detalhes(i), "suave", True,
                largura=84).pack(side="left", padx=(0, 4))
    criar_botao(acoes, "Remover", lambda i=id_disp: remover_dispositivo(i), "suave", True,
                largura=84).pack(side="right")

    if isinstance(dispositivo, ConexaoWiFi):
        espaco_wifi = caixa(miolo)
        espaco_wifi.pack(fill="x", pady=(11, 0))
        if wifi == "Conectado":
            criar_botao(espaco_wifi, "◉  Desconectar Wi-Fi", lambda i=id_disp: desconectar_wifi(i),
                        "suave", True, largura=182).pack(anchor="w")
        else:
            criar_botao(espaco_wifi, "◉  Conectar Wi-Fi", lambda i=id_disp: conectar_wifi(i),
                        "suave", True, largura=173).pack(anchor="w")

    if isinstance(dispositivo, LampadaInteligente):
        # --------------- Lâmpada: paleta de cores original -----------
        criar_rotulo(miolo, "Cor da luz", 11, "bold", cor("texto_fraco")).pack(anchor="w", pady=(17, 7))
        cores = caixa(miolo)
        cores.pack(anchor="w")
        for nome, hex_cor in [("Branca", "#F1F1EB"), ("Amarela", "#F8CE6D"),
                              ("Azul", "#6CB9FF"), ("Vermelha", "#FA7784"), ("Verde", "#53DAAA")]:
            amostra = ctk.CTkButton(cores, text="", width=33, height=33,
                                   corner_radius=16, fg_color=hex_cor,
                                   hover_color=misturar_cor(hex_cor, "#121C2F", .20),
                                   command=lambda i=id_disp, c=nome: mudar_cor_lampada(i, c))
            amostra.pack(side="left", padx=(0, 11))
    elif isinstance(dispositivo, ArCondicionado):
        # --------------- Ar: temperatura e temporizador originais -----------
        ajuste = caixa(miolo)
        ajuste.pack(fill="x", pady=(14, 0))
        criar_rotulo(ajuste, f"{extrair_temperatura_ar(dispositivo)}°C", 28, "bold", cor("ciano")).pack(side="left", padx=(0, 13))
        for txt, cmd, wid in [("−", lambda i=id_disp: ajustar_temperatura_ar(i, -1), 38),
                              ("+", lambda i=id_disp: ajustar_temperatura_ar(i, 1), 38),
                              ("Definir", lambda i=id_disp: ajustar_temperatura_ar(i), 74)]:
            criar_botao(ajuste, txt, cmd, "suave", True, largura=wid).pack(side="left", padx=(0, 5))
        tempo = caixa(miolo)
        tempo.pack(fill="x", pady=(12, 0))
        criar_botao(tempo, "Temporizador", lambda i=id_disp: definir_temporizador(i), "suave", True,
                    largura=126).pack(side="left", padx=(0, 6))
        criar_botao(tempo, "Cancelar", lambda i=id_disp: cancelar_temporizador(i), "suave", True,
                    largura=85).pack(side="left")
    elif isinstance(dispositivo, SensorPresenca):
        # --------------- Presença: simulação original -----------
        opcoes = caixa(miolo)
        opcoes.pack(fill="x", pady=(14, 0))
        criar_botao(opcoes, "Presença detectada", lambda i=id_disp: simular_presenca(i, True),
                    "suave", True, largura=158).pack(side="left", padx=(0, 7))
        criar_botao(opcoes, "Sem presença", lambda i=id_disp: simular_presenca(i, False),
                    "suave", True, largura=119).pack(side="left")
    elif isinstance(dispositivo, SensorTemperatura):
        criar_botao(miolo, "Atualizar temperatura", lambda i=id_disp: atualizar_sensor_temperatura(i),
                    "suave", True, largura=190).pack(anchor="w", pady=(14, 0))
    elif isinstance(dispositivo, AssistenteVirtual):
        # --------------- Alexa: voz única, contínua, manual e microfone -----------
        voz = caixa(miolo)
        voz.pack(fill="x", pady=(13, 0))
        if voz_em_execucao and voz_id_assistente == id_disp:
            criar_botao(voz, "■ Parar escuta", parar_escuta_voz, "perigo", True,
                        largura=155).pack(side="left")
        else:
            criar_botao(voz, "◉ Ouvir uma vez", lambda i=id_disp: iniciar_comando_voz(i),
                        "primario", True, largura=148).pack(side="left", padx=(0, 6))
            criar_botao(voz, "▶ Escuta contínua", lambda i=id_disp: iniciar_comando_voz(i, True),
                        "suave", True, largura=145).pack(side="left")
        botoes = caixa(miolo)
        botoes.pack(fill="x", pady=(9, 0))
        criar_botao(botoes, "Digitar comando", lambda i=id_disp: comando_manual_assistente(i),
                    "suave", True, largura=153).pack(side="left", padx=(0, 7))
        criar_botao(botoes, "Microfone", configurar_microfone,
                    "suave", True, largura=109).pack(side="left")
        criar_rotulo(miolo, "", 11, "bold", cor("ciano"), textvariable=texto_estado_voz,
                     wraplength=330, justify="left").pack(anchor="w", pady=(11, 1))
        criar_rotulo(miolo, "", 10, cor_texto=cor("texto_fraco"), textvariable=texto_ultimo_comando,
                     wraplength=330, justify="left").pack(anchor="w", pady=(2, 0))
    return card


def criar_area_sensores(pai, dispositivos):
    card = criar_cartao(pai)
    miolo = caixa(card)
    miolo.pack(fill="both", expand=True, padx=19, pady=17)
    criar_rotulo(miolo, "Sensores", 15, "bold").pack(anchor="w")
    criar_rotulo(miolo, "Leituras e estados informados pelos sensores cadastrados.",
                 10, cor_texto=cor("texto_fraco"), wraplength=410,
                 justify="left").pack(anchor="w", pady=(4, 12))
    if not dispositivos:
        criar_rotulo(miolo, "Nenhum sensor cadastrado.", 11, cor_texto=cor("texto_sutil")).pack(anchor="w")
    for ident, disp in dispositivos:
        linha = caixa(miolo)
        linha.pack(fill="x", pady=7)
        simb, destaque = obter_icone(disp)
        criar_icone(linha, simb, destaque, 38, 17).pack(side="left")
        textos = caixa(linha)
        textos.pack(side="left", fill="x", padx=(9, 0), expand=True)
        criar_rotulo(textos, disp.get_nome().title(), 11, "bold").pack(anchor="w")
        criar_rotulo(textos, disp.testar_status(), 10, cor_texto=cor("texto_fraco"),
                     justify="left", wraplength=385).pack(anchor="w")
    return card


def criar_area_historico(pai):
    card = criar_cartao(pai)
    miolo = caixa(card)
    miolo.pack(fill="both", expand=True, padx=19, pady=17)
    topo = caixa(miolo)
    topo.pack(fill="x")
    criar_rotulo(topo, "Histórico de atividades", 15, "bold").pack(side="left")
    criar_botao(topo, "Limpar", limpar_historico, "suave", True,
                largura=74).pack(side="right")
    criar_rotulo(miolo, "Operações realizadas nesta interface.", 10,
                 cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(5, 10))
    linhas = historico_atividades or carregar_historico()
    if not linhas:
        criar_rotulo(miolo, "Nenhuma atividade registrada ainda.", 11,
                     cor_texto=cor("texto_sutil")).pack(anchor="w")
    else:
        for item in linhas[:8]:
            criar_rotulo(miolo, "• " + item, 10, cor_texto=cor("texto_fraco"),
                         justify="left", wraplength=460, anchor="w").pack(anchor="w", pady=3)
    return card


def atualizar_lista():
    renderizar_painel()


def renderizar_painel():
    # --------------- Navegação independente, preservando o conteúdo original -----------
    if painel_scroll is None or not painel_scroll.winfo_exists(): return
    for filho in painel_scroll.winfo_children(): filho.destroy()
    secoes_painel.clear()
    itens = casa.listar_dispositivos()
    ligados = sum(d.is_ligado() for _, d in itens)
    desligados = len(itens) - ligados
    conectados = sum(isinstance(d, ConexaoWiFi) and obter_status_wifi(d) == "Conectado" for _, d in itens)
    sensores = [(i, d) for i, d in itens if isinstance(d, (SensorPresenca, SensorTemperatura))]
    area = painel_scroll

    if pagina_atual == "inicio":
        criar_hero(area, itens, ligados, conectados)
        cabecalho_secao(area, "Visão geral", "Tudo o que você precisa saber sobre sua casa.",
                        lambda p: criar_botao(p, "+ Adicionar dispositivo", adicionar_dispositivo,
                                             "primario", True, largura=185))
        grade = caixa(area)
        grade.pack(fill="x")
        for i, vals in enumerate([
            ("Dispositivos", len(itens), "Cadastrados", "azul", "⌂"),
            ("Ligados", ligados, "Em funcionamento", "verde", "●"),
            ("Desligados", desligados, "Fora de funcionamento", "vermelho", "○"),
            ("Wi-Fi", conectados, "Conectados", "ciano", "◉"),
        ]):
            criar_card_resumo(grade, *vals, i)
            grade.grid_columnconfigure(i, weight=1, uniform="resumo")

        cabecalho_secao(area, "Categorias", "Cada categoria possui sua própria página e seus controles.")
        atalhos = caixa(area)
        atalhos.pack(fill="x")
        for i, chave in enumerate(CATEGORIAS):
            criar_atalho_categoria(atalhos, chave, i)
        atalhos.grid_columnconfigure(0, weight=1, uniform="atalhos")
        atalhos.grid_columnconfigure(1, weight=1, uniform="atalhos")

        cabecalho_secao(area, "Cômodos", "Os dispositivos são agrupados pelo ambiente cadastrado.")
        locais = lista_comodos()
        if locais:
            grade_comodos = caixa(area)
            grade_comodos.pack(fill="x")
            for i, local in enumerate(locais):
                criar_atalho_comodo(grade_comodos, local, i)
            for col in range(3):
                grade_comodos.grid_columnconfigure(col, weight=1, uniform="comodos")
        else:
            criar_rotulo(area, "Nenhum cômodo cadastrado ainda.", 11,
                         cor_texto=cor("texto_fraco")).pack(anchor="w")

        cabecalho_secao(area, "Atividade e sensores")
        cols = caixa(area)
        cols.pack(fill="x", pady=(2, 10))
        criar_area_historico(cols).grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        criar_area_sensores(cols, sensores).grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        cols.grid_columnconfigure(0, weight=1, uniform="rodape")
        cols.grid_columnconfigure(1, weight=1, uniform="rodape")

    elif pagina_atual in CATEGORIAS:
        nome, simbolo, destaque, descricao = CATEGORIAS[pagina_atual]
        titulo = caixa(area)
        titulo.pack(fill="x", pady=(12, 14))
        criar_icone(titulo, simbolo, destaque, 62, 31).pack(side="left")
        textos = caixa(titulo)
        textos.pack(side="left", padx=16)
        criar_rotulo(textos, nome, 28, "bold").pack(anchor="w")
        criar_rotulo(textos, descricao, 12, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(5, 0))
        animar_faixa(area, destaque)
        pagina_itens = dispositivos_categoria(pagina_atual)
        criar_rotulo(area, f"{len(pagina_itens)} dispositivo(s) nesta categoria", 11,
                     cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(18, 12))
        criar_grade_dispositivos(area, pagina_itens)
        if pagina_atual == "assistentes":
            dica = criar_cartao(area)
            dica.pack(fill="x", pady=(15, 0))
            corpo = caixa(dica)
            corpo.pack(fill="x", padx=18, pady=16)
            criar_rotulo(corpo, "Exemplos de comandos", 13, "bold").pack(anchor="w")
            criar_rotulo(corpo,
                '"Alexa, ligar todos os dispositivos"   •   "Alexa, desligar Sala"   •   "Alexa, ligar Lâmpada Sala"',
                11, cor_texto=cor("texto_fraco"), wraplength=760, justify="left").pack(anchor="w", pady=(8, 0))

    elif pagina_atual == "comodo":
        local = comodo_ativo or "Sem Cômodo"
        criar_rotulo(area, "⌂  " + local, 28, "bold").pack(anchor="w", pady=(10, 5))
        criar_rotulo(area, "Dispositivos deste ambiente.", 12,
                     cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(0, 16))
        animar_faixa(area, "azul")
        pagina_itens = dispositivos_comodo(local)
        criar_rotulo(area,
                     f"{len(pagina_itens)} dispositivo(s)  •  {sum(d.is_ligado() for _, d in pagina_itens)} ligado(s)",
                     11, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(17, 12))
        criar_grade_dispositivos(area, pagina_itens)

    elif pagina_atual == "atividade":
        criar_rotulo(area, "◷  Histórico de atividades", 28, "bold").pack(anchor="w", pady=(10, 5))
        criar_rotulo(area, "Operações realizadas nesta interface.", 12,
                     cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(0, 16))
        animar_faixa(area, "verde")
        historico = criar_cartao(area)
        historico.pack(fill="x", pady=(17, 0))
        conteudo = caixa(historico)
        conteudo.pack(fill="x", padx=19, pady=17)
        criar_botao(conteudo, "Limpar histórico", limpar_historico, "suave", True,
                    largura=140).pack(anchor="e", pady=(0, 10))
        for msg in (historico_atividades or ["Nenhuma atividade registrada ainda."])[:100]:
            linha = caixa(conteudo)
            linha.pack(fill="x", pady=4)
            criar_rotulo(linha, "●", 11, "bold", cor("azul")).pack(side="left", padx=(0, 11))
            criar_rotulo(linha, msg, 11, cor_texto=cor("texto_fraco"),
                         justify="left", anchor="w", wraplength=765).pack(side="left", fill="x", expand=True)
        cabecalho_secao(area, "Sensores", "Leituras e estados dos sensores cadastrados.")
        criar_area_sensores(area, sensores).pack(fill="x")

    criar_rotulo(area,
        "Os indicadores verde e vermelho representam o estado lógico do Wi-Fi dos dispositivos compatíveis. Cinza significa que não possuem Wi-Fi no modelo atual.",
        10, cor_texto=cor("texto_sutil"), justify="left", wraplength=810).pack(anchor="w", pady=(26, 22))


def alternar_tema():
    global tema_atual
    tema_atual = "claro" if tema_atual == "escuro" else "escuro"
    ctk.set_appearance_mode("light" if tema_atual == "claro" else "dark")
    montar_interface()


def montar_interface():
    # --------------- Estrutura CTk: navegação, temas e scroll independente -----------
    global canvas_painel, painel_scroll, status_bar, label_caminho
    for filho in janela.winfo_children(): filho.destroy()
    menu_botoes.clear()
    janela.configure(fg_color=cor("fundo"))
    estrutura = caixa(janela, fundo=cor("fundo"))
    estrutura.pack(fill="both", expand=True)
    lateral = ctk.CTkFrame(estrutura, fg_color=cor("lateral"), corner_radius=0, width=240)
    lateral.pack(side="left", fill="y")
    lateral.pack_propagate(False)
    marca = caixa(lateral)
    marca.pack(fill="x", padx=18, pady=(24, 37))
    criar_icone(marca, "⌂", "azul", 49, 26).pack(side="left")
    textos_marca = caixa(marca)
    textos_marca.pack(side="left", padx=(11, 0))
    criar_rotulo(textos_marca, "CASA", 18, "bold").pack(anchor="w")
    criar_rotulo(textos_marca, "INTELIGENTE", 10, "bold", cor("texto_fraco")).pack(anchor="w")
    criar_rotulo(lateral, "NAVEGAÇÃO", 10, "bold", cor("texto_sutil")).pack(anchor="w", padx=24, pady=(0, 11))

    def menu(titulo, simbolo, chave, destaque):
        ativo = pagina_atual == chave
        botao = criar_botao(lateral, f"{simbolo}    {titulo}", lambda c=chave: navegar_para(c),
                             "suave", fundo=cor("superficie_2") if ativo else cor("lateral"),
                             frente=cor(destaque) if ativo else cor("texto_fraco"),
                             altura=45, alinhamento="w")
        botao.pack(fill="x", padx=13, pady=4)
        menu_botoes[chave] = botao

    menu("Visão geral", "⌂", "inicio", "azul")
    menu("Iluminação", "☀", "lampadas", "amarelo")
    menu("Climatização", "❄", "ar", "ciano")
    menu("Sensores", "◉", "sensores", "roxo")
    menu("Assistente Virtual", "◌", "assistentes", "azul")
    menu("Atividades", "◷", "atividade", "verde")
    lateral_rodape = caixa(lateral)
    lateral_rodape.pack(side="bottom", fill="x", padx=18, pady=26)
    ctk.CTkFrame(lateral_rodape, height=1, fg_color=cor("borda")).pack(fill="x", pady=(0, 17))
    criar_rotulo(lateral_rodape, "●  Sistema local", 11, "bold", cor("verde")).pack(anchor="w")
    criar_rotulo(lateral_rodape, "Dados salvos em dispositivos_casa.pkl", 10,
                 cor_texto=cor("texto_sutil"), wraplength=195,
                 justify="left").pack(anchor="w", pady=(7, 0))

    principal = caixa(estrutura, fundo=cor("fundo"))
    principal.pack(side="left", fill="both", expand=True)
    barra = caixa(principal, fundo=cor("fundo"))
    barra.pack(fill="x", padx=27, pady=(19, 13))
    titulo = (CATEGORIAS[pagina_atual][0] if pagina_atual in CATEGORIAS else
              "Visão geral" if pagina_atual == "inicio" else
              "Atividades" if pagina_atual == "atividade" else comodo_ativo or "Cômodos")
    label_caminho = criar_rotulo(barra, "Meu lar  /  " + titulo, 11, "bold", cor("texto_fraco"))
    label_caminho.pack(side="left")
    criar_botao(barra, "☀ Modo claro" if tema_atual == "escuro" else "☾ Modo escuro",
                alternar_tema, "suave", True, largura=126).pack(side="right", padx=(9, 0))
    criar_botao(barra, "+ Adicionar", adicionar_dispositivo, "primario", True,
                largura=120).pack(side="right")

    painel_scroll = ctk.CTkScrollableFrame(principal, fg_color=cor("fundo"),
                                          corner_radius=0, scrollbar_fg_color=cor("fundo"),
                                          scrollbar_button_color=cor("borda"),
                                          scrollbar_button_hover_color=cor("azul"))
    painel_scroll.pack(fill="both", expand=True, padx=(24, 13), pady=(0, 8))
    canvas_painel = getattr(painel_scroll, "_parent_canvas", None)
    status_bar = ctk.CTkLabel(principal, text="Sistema pronto.", fg_color=cor("lateral"),
                              text_color=cor("texto_fraco"), font=fonte(10),
                              anchor="w", height=32)
    status_bar.pack(fill="x", side="bottom")
    renderizar_painel()



# --------------- Inicialização: mesmos arquivos e classes -----------
if __name__ == "__main__":
    reparar_wifi_antigo()
    locais_dispositivos = carregar_comodos()
    historico_atividades = carregar_historico()
    montar_interface()
    janela.after(120, processar_eventos_voz)
    janela.protocol("WM_DELETE_WINDOW", fechar_interface)
    janela.mainloop()
