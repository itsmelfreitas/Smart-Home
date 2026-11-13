Here is the complete, fully cleaned-up version of `interface.py` with all the Mac compatibility fixes and non-breaking spaces removed so it won't throw any indentation errors:

```python
import os
import json
import queue
import re
import sys
import threading
import traceback
import unicodedata
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from datetime import datetime

import CasaInteligente as modulo_casa

sys.modules.setdefault("casa_inteligente", modulo_casa)

from CasaInteligente import (
    CasaInteligente,
    AssistenteVirtual,
    LampadaInteligente,
    ArCondicionado,
    SensorPresenca,
    SensorTemperatura,
    ConexaoWiFi,
)

try:
    import speech_recognition as sr
except ImportError:
    sr = None


# --------------- Compatibilidade visual com Tkinter no macOS -----------
MODO_MAC = sys.platform == "darwin"
FONTE_INTERFACE = "Helvetica" if MODO_MAC else "Segoe UI"
FONTE_SIMBOLOS = "Helvetica" if MODO_MAC else "Segoe UI Symbol"

casa = CasaInteligente()
janela = tk.Tk()
janela.title("Casa Inteligente")
if MODO_MAC:
    largura_tela = janela.winfo_screenwidth()
    altura_tela = janela.winfo_screenheight()
    largura_janela = min(1260, max(760, largura_tela - 75))
    altura_janela = min(820, max(560, altura_tela - 130))
    janela.geometry(f"{largura_janela}x{altura_janela}")
    janela.minsize(min(800, largura_janela), min(540, altura_janela))
else:
    janela.geometry("1260x820")
    janela.minsize(1010, 690)

# --------------- Diagnóstico de exceções em callbacks no macOS -----------
def registrar_erro_interface(tipo, erro, rastreio):
    detalhes = "".join(traceback.format_exception(tipo, erro, rastreio))
    print(detalhes, file=sys.stderr)
    if MODO_MAC:
        try:
            caminho_erro = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erro_interface_mac.txt")
            with open(caminho_erro, "a", encoding="utf-8") as arquivo:
                arquivo.write(f"\n{datetime.now().isoformat(timespec='seconds')}\n{detalhes}\n")
        except OSError:
            pass
        try:
            messagebox.showerror("Erro na interface", f"Ocorreu um erro ao abrir ou atualizar a tela:\n{erro}\n\nVeja erro_interface_mac.txt.", parent=janela)
        except tk.TclError:
            pass

janela.report_callback_exception = registrar_erro_interface

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

# ---------------comentario-----------
# Captura de audio fora da thread do Tkinter, com eventos processados somente na janela principal.
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
        "fundo": "#101923",
        "lateral": "#131D2B",
        "superficie": "#1B2636",
        "superficie_2": "#253244",
        "borda": "#344256",
        "texto": "#F3F6FA",
        "texto_fraco": "#A5B1C2",
        "texto_sutil": "#748399",
        "azul": "#69A7FF",
        "azul_escuro": "#264D80",
        "verde": "#37C987",
        "vermelho": "#F16B75",
        "amarelo": "#F0C15A",
        "ciano": "#58C8E8",
        "roxo": "#B29AFF",
        "laranja": "#F09A59",
        "botao": "#26384F",
        "botao_hover": "#394B63",
        "entrada": "#131B27",
    },
    "claro": {
        "fundo": "#F3F5FA",
        "lateral": "#FFFFFF",
        "superficie": "#FFFFFF",
        "superficie_2": "#EEF3FA",
        "borda": "#DCE4EE",
        "texto": "#172334",
        "texto_fraco": "#536277",
        "texto_sutil": "#78879A",
        "azul": "#3278D5",
        "azul_escuro": "#DCEBFF",
        "verde": "#169B66",
        "vermelho": "#D94D5C",
        "amarelo": "#B98116",
        "ciano": "#1686A7",
        "roxo": "#7958C8",
        "laranja": "#C66B28",
        "botao": "#E8EEF6",
        "botao_hover": "#D9E4F2",
        "entrada": "#F8FAFD",
    },
}


def cor(nome):
    return CORES[tema_atual][nome]


def normalizar_texto(texto):
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(letra for letra in texto if unicodedata.category(letra) != "Mn")


# --------------- Cômodos e identificação dos dispositivos -----------
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


def selecionar_comodo_dialogo(titulo, atual="Sem Cômodo"):
    resultado = {"valor": None}
    dialogo = tk.Toplevel(janela)
    dialogo.title(titulo)
    dialogo.configure(bg=cor("superficie"))
    dialogo.geometry("420x225")
    dialogo.resizable(False, False)
    dialogo.transient(janela)
    dialogo.grab_set()
    tk.Label(dialogo, text="Onde está o dispositivo?", font=(FONTE_INTERFACE, 15, "bold"), bg=cor("superficie"), fg=cor("texto")).pack(anchor="w", padx=25, pady=(23, 7))
    tk.Label(dialogo, text="Escolha um cômodo ou digite outro nome.", font=(FONTE_INTERFACE, 10), bg=cor("superficie"), fg=cor("texto_fraco")).pack(anchor="w", padx=25)
    escolha = tk.StringVar(value=atual)
    entrada = ttk.Combobox(dialogo, textvariable=escolha, values=COMODOS_SUGESTOES, width=35)
    entrada.pack(fill="x", padx=25, pady=(14, 12), ipady=5)
    entrada.focus_set()

    def salvar(evento=None):
        resultado["valor"] = formatar_comodo(escolha.get())
        dialogo.destroy()

    criar_botao(dialogo, "Confirmar cômodo", salvar, "primario").pack(fill="x", padx=25)
    dialogo.bind("<Return>", salvar)
    dialogo.bind("<Escape>", lambda evento: dialogo.destroy())
    dialogo.wait_window()
    return resultado["valor"]


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


def criar_botao(pai, texto, comando, estilo="normal", compacto=False):
    estilos = {
        "normal": (cor("botao"), cor("texto")),
        "primario": (cor("azul"), "#FFFFFF"),
        "positivo": (cor("verde"), "#FFFFFF"),
        "perigo": (cor("vermelho"), "#FFFFFF"),
        "suave": (cor("superficie_2"), cor("texto_fraco")),
    }
    fundo, frente = estilos.get(estilo, estilos["normal"])
    parametros = dict(
        bg=fundo,
        fg=frente,
        relief="flat",
        bd=0,
        cursor="hand2",
        font=(FONTE_INTERFACE, 9 if compacto else 10, "bold"),
        padx=10 if compacto else 14,
        pady=6 if compacto else 9,
        highlightthickness=0,
    )
    if MODO_MAC:
        # No Aqua, Button pode ignorar as cores do tema. Label preserva cores e clique.
        botao = tk.Label(pai, text=texto, takefocus=1, **parametros)
        botao.bind("<Button-1>", lambda evento: comando())
        botao.bind("<Return>", lambda evento: comando())
        botao.bind("<space>", lambda evento: comando())
    else:
        botao = tk.Button(
            pai, text=texto, command=comando,
            activebackground=cor("botao_hover"), activeforeground=frente,
            **parametros,
        )
    botao.bind("<Enter>", lambda evento: botao.configure(bg=cor("botao_hover")) if estilo in ("normal", "suave") else None)
    botao.bind("<Leave>", lambda evento: botao.configure(bg=fundo))
    return botao


def criar_rotulo(pai, texto, tamanho=10, peso="normal", cor_texto=None, fundo=None, fonte=None, **kwargs):
    return tk.Label(
        pai,
        text=texto,
        bg=fundo or cor("superficie"),
        fg=cor_texto or cor("texto"),
        font=fonte or (FONTE_INTERFACE, tamanho, peso),
        **kwargs,
    )


def criar_cartao(pai, padding=18):
    return tk.Frame(pai, bg=cor("superficie"), highlightbackground=cor("borda"),
                    highlightthickness=1, padx=padding, pady=padding)


def atualizar_status(texto):
    if status_bar is not None and status_bar.winfo_exists():
        status_bar.configure(text=texto)


def rolar_para(secao):
    if canvas_painel is None or secao not in secoes_painel:
        return
    painel_scroll.update_idletasks()
    altura = max(painel_scroll.winfo_height(), 1)
    canvas_painel.yview_moveto(max(0, secoes_painel[secao].winfo_y()) / altura)


def adicionar_dispositivo():
    # --------------- Cadastro visual, usando as classes de CasaInteligente -----------
    dialogo = tk.Toplevel(janela)
    dialogo.title("Adicionar dispositivo")
    dialogo.geometry("530x640")
    dialogo.minsize(475, 580)
    dialogo.configure(bg=cor("fundo"))
    dialogo.transient(janela)
    dialogo.grab_set()
    tk.Label(dialogo, text="Novo dispositivo", font=(FONTE_INTERFACE, 21, "bold"),
             fg=cor("texto"), bg=cor("fundo")).pack(anchor="w", padx=30, pady=(25, 4))
    tk.Label(dialogo, text="Personalize o dispositivo e escolha onde ele está na casa.",
             font=(FONTE_INTERFACE, 10), fg=cor("texto_fraco"), bg=cor("fundo")).pack(anchor="w", padx=30, pady=(0, 18))
    formulario = criar_cartao(dialogo, 20)
    formulario.pack(fill="both", expand=True, padx=26, pady=(0, 10))

    valores = {"tipo": tk.StringVar(value="lampada"),
               "nome": tk.StringVar(value=""),
               "comodo": tk.StringVar(value="Sala"),
               "cor": tk.StringVar(value="Branca"),
               "temperatura": tk.StringVar(value="24"),
               "ssid": tk.StringVar(value="Casa"),
               "senha": tk.StringVar(value="12345678")}

    def campo(texto, variavel, combo=None, esconder=None):
        bloco = tk.Frame(formulario, bg=cor("superficie"))
        criar_rotulo(bloco, texto, 9, "bold", cor("texto_fraco")).pack(anchor="w", pady=(0, 5))
        if combo is None:
            entrada = tk.Entry(bloco, textvariable=variavel, show=esconder or "", relief="flat",
                               bg=cor("entrada"), fg=cor("texto"), insertbackground=cor("texto"),
                               font=(FONTE_INTERFACE, 11), bd=0)
        else:
            entrada = ttk.Combobox(bloco, textvariable=variavel, values=combo, state="readonly" if texto.startswith("Tipo") else "normal")
        entrada.pack(fill="x", ipady=6)
        bloco.pack(fill="x", pady=(0, 12))
        return bloco

    campo("Tipo de dispositivo", valores["tipo"], ["lampada", "ar", "presenca", "temperatura", "assistente"])
    campo("Nome do dispositivo", valores["nome"])
    campo("Cômodo", valores["comodo"], COMODOS_SUGESTOES)
    extras = tk.Frame(formulario, bg=cor("superficie"))
    extras.pack(fill="x")

    def atualizar_campos(*_):
        for item in extras.winfo_children():
            item.destroy()
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

    def adicionar_campo_extra(titulo, nome, esconder=""):
        bloco = tk.Frame(extras, bg=cor("superficie"))
        criar_rotulo(bloco, titulo, 9, "bold", cor("texto_fraco")).pack(anchor="w", pady=(0, 5))
        tk.Entry(bloco, textvariable=valores[nome], show=esconder, relief="flat", bd=0,
                 font=(FONTE_INTERFACE, 11), bg=cor("entrada"), fg=cor("texto"),
                 insertbackground=cor("texto")).pack(fill="x", ipady=5)
        bloco.pack(fill="x", pady=(0, 12))

    valores["tipo"].trace_add("write", atualizar_campos)
    atualizar_campos()
    if pagina_atual in ("lampadas", "ar", "sensores", "assistentes"):
        tipo_inicial = {"lampadas": "lampada", "ar": "ar", "sensores": "presenca", "assistentes": "assistente"}[pagina_atual]
        valores["tipo"].set(tipo_inicial)
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

    criar_botao(dialogo, "+  Adicionar dispositivo", confirmar, "primario").pack(fill="x", padx=26, pady=(0, 25))
    dialogo.bind("<Escape>", lambda evento: dialogo.destroy())
    dialogo.protocol("WM_DELETE_WINDOW", dialogo.destroy)


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


def escolher_dispositivo_alvo(excluir_id=None, tipo=None):
    dispositivos = [
        (id_disp, disp) for id_disp, disp in casa.listar_dispositivos()
        if id_disp != excluir_id and (tipo is None or isinstance(disp, tipo))
    ]
    if not dispositivos:
        messagebox.showwarning("Assistente Virtual", "Nenhum dispositivo compatível encontrado.", parent=janela)
        return None

    dialogo = tk.Toplevel(janela)
    dialogo.title("Qual dispositivo deseja controlar?")
    dialogo.configure(bg=cor("fundo"))
    dialogo.transient(janela)
    dialogo.grab_set()
    dialogo.resizable(False, False)
    tk.Label(
        dialogo, text="Qual dispositivo deseja controlar?", bg=cor("fundo"),
        fg=cor("texto"), font=(FONTE_INTERFACE, 12, "bold"), padx=18, pady=14,
    ).pack(anchor="w")
    opcoes = [f"{id_disp} - {disp.get_nome().title()} ({nome_tipo(disp)})" for id_disp, disp in dispositivos]
    selecionado = tk.StringVar(value=opcoes[0])
    ttk.Combobox(dialogo, textvariable=selecionado, values=opcoes, state="readonly", width=46).pack(padx=18, pady=5)
    resultado = {"id": None}

    def confirmar():
        try:
            resultado["id"] = int(selecionado.get().split(" - ", 1)[0])
        except (ValueError, IndexError):
            resultado["id"] = None
        dialogo.destroy()

    criar_botao(dialogo, "Selecionar", confirmar, "primario").pack(fill="x", padx=18, pady=16)
    dialogo.bind("<Escape>", lambda evento: dialogo.destroy())
    dialogo.protocol("WM_DELETE_WINDOW", dialogo.destroy)
    dialogo.wait_window()
    return resultado["id"]


# ---------------comentario-----------
# Os nomes e IDs sao os mesmos usados por CasaInteligente e main; nunca se inventa um novo dispositivo.
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


# --------------- Comando de voz: alvo único, cômodo e comando global -----------
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


# ---------------comentario-----------
# Pode-se escolher o dispositivo de gravacao do Windows; a selecao e mantida nesta sessao da interface.
def configurar_microfone():
    global microfone_indice
    if sr is None:
        messagebox.showwarning(
            "Reconhecimento de voz",
            'Instale o microfone com:\n\npython -m pip install "SpeechRecognition[audio]"',
            parent=janela,
        )
        return
    try:
        nomes = sr.Microphone.list_microphone_names()
    except Exception as erro:
        messagebox.showerror(
            "Microfone",
            f"Não foi possível listar os microfones. Verifique o PyAudio e as permissões do Windows.\n\n{erro}",
            parent=janela,
        )
        return
    if not nomes:
        messagebox.showwarning("Microfone", "Nenhum microfone encontrado no sistema.", parent=janela)
        return

    dialogo = tk.Toplevel(janela)
    dialogo.title("Selecionar microfone")
    dialogo.configure(bg=cor("fundo"))
    dialogo.transient(janela)
    dialogo.grab_set()
    dialogo.resizable(False, False)
    criar_rotulo(dialogo, "Selecione a entrada de áudio", 12, "bold", fundo=cor("fundo")).pack(padx=16, pady=(16, 10))
    opcoes = ["Padrão do sistema"] + [f"{indice} - {nome or 'Microfone sem nome'}" for indice, nome in enumerate(nomes)]
    selecionado = tk.StringVar(value=(f"{microfone_indice} - {nomes[microfone_indice]}" if microfone_indice is not None and microfone_indice < len(nomes) else opcoes[0]))
    ttk.Combobox(dialogo, textvariable=selecionado, values=opcoes, state="readonly", width=56).pack(padx=16, pady=5)

    def confirmar():
        global microfone_indice
        escolha = selecionado.get()
        microfone_indice = None if escolha == opcoes[0] else int(escolha.split(" - ", 1)[0])
        texto_estado_voz.set("Microfone configurado. Pronto para ouvir.")
        atualizar_status("Microfone configurado.")
        dialogo.destroy()

    criar_botao(dialogo, "Usar microfone", confirmar, "primario").pack(fill="x", padx=16, pady=(8, 16))
    dialogo.bind("<Escape>", lambda evento: dialogo.destroy())
    dialogo.protocol("WM_DELETE_WINDOW", dialogo.destroy)


def iniciar_comando_voz(id_asst, continuo=False):
    global voz_em_execucao, voz_modo_continuo, voz_sessao, voz_evento_parar, voz_id_assistente
    if voz_em_execucao:
        atualizar_status("O microfone já está em uso. Encerre a escuta antes de iniciar outra.")
        return
    if sr is None:
        messagebox.showwarning(
            "Reconhecimento de voz",
            'Instale as dependências no VS Code:\n\npython -m pip install "SpeechRecognition[audio]"\n\nReinicie a interface após a instalação.',
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


# --------------- Páginas, cores e cartões do painel -----------
CATEGORIAS = {
    "lampadas": ("Iluminação", "✦", "amarelo", "Controle as lâmpadas e personalize as cores."),
    "ar": ("Climatização", "❄", "ciano", "Ajuste a temperatura e os temporizadores."),
    "sensores": ("Sensores", "◉", "roxo", "Monitore presença e temperatura."),
    "assistentes": ("Assistente Virtual", "◖))", "azul", "Comandos digitados ou com o microfone."),
}


def fundo_icone(chave):
    fundos = {
        "escuro": {"amarelo": "#493B2B", "ciano": "#153E4E", "roxo": "#382C55",
                   "azul": "#203D65", "verde": "#194235", "laranja": "#49362A"},
        "claro": {"amarelo": "#FFF1D5", "ciano": "#D9F4FC", "roxo": "#EEE6FF",
                  "azul": "#DFECFF", "verde": "#DDF8EC", "laranja": "#FFEADA"},
    }
    return fundos[tema_atual].get(chave, cor("superficie_2"))


def titulo_secao(pai, titulo, subtitulo=""):
    linha = tk.Frame(pai, bg=cor("fundo"))
    linha.pack(fill="x", pady=(22, 12))
    criar_rotulo(linha, titulo, 15, "bold", cor("texto"), cor("fundo")).pack(anchor="w")
    if subtitulo:
        criar_rotulo(linha, subtitulo, 9, cor_texto=cor("texto_fraco"), fundo=cor("fundo")).pack(anchor="w", pady=(4, 0))
    return linha


def criar_etiqueta(pai, texto, cor_texto="azul"):
    faixa = tk.Frame(pai, bg=fundo_icone(cor_texto), padx=8, pady=4)
    criar_rotulo(faixa, texto, 8, "bold", cor(cor_texto), fundo_icone(cor_texto)).pack()
    return faixa


def navegar_para(chave, local=None):
    global pagina_atual, comodo_ativo
    pagina_atual = chave
    comodo_ativo = local if chave == "comodo" else None
    renderizar_painel()
    if canvas_painel is not None and canvas_painel.winfo_exists():
        canvas_painel.yview_moveto(0)
    if label_caminho is not None and label_caminho.winfo_exists():
        titulo = (CATEGORIAS[chave][0] if chave in CATEGORIAS else
                  "Visão geral" if chave == "inicio" else
                  "Atividades" if chave == "atividade" else comodo_ativo or "Cômodos")
        label_caminho.configure(text="Meu lar  /  " + titulo)
    for nome, botao in list(menu_botoes.items()):
        if botao.winfo_exists():
            ativo = nome == chave
            destaque = CATEGORIAS[nome][2] if nome in CATEGORIAS else "azul"
            botao.configure(bg=cor("superficie_2") if ativo else cor("lateral"),
                            fg=cor(destaque) if ativo else cor("texto_fraco"))


def criar_hero(pai, dispositivos, ligados, conectados):
    # --------------- Painel principal com visual adaptado ao Mac -----------
    if MODO_MAC:
        # Fundo sólido evita falhas com stipple/camadas do Canvas no Aqua antigo.
        painel = tk.Frame(pai, height=218, bg="#155A9D", padx=29, pady=22)
        painel.pack(fill="x", pady=(4, 5))
        painel.pack_propagate(False)
        tk.Label(painel, text="CASA INTELIGENTE  /  PAINEL PRINCIPAL", bg="#155A9D", fg="#D8EDFF",
                 font=(FONTE_INTERFACE, 9, "bold")).pack(anchor="w")
        tk.Label(painel, text="Sua casa, do seu jeito.", bg="#155A9D", fg="#FFFFFF",
                 font=(FONTE_INTERFACE, 24, "bold")).pack(anchor="w", pady=(13, 2))
        tk.Label(painel, text="Veja o que está acontecendo e acesse seus ambientes.",
                 bg="#155A9D", fg="#EDF7FF", font=(FONTE_INTERFACE, 10)).pack(anchor="w")
        tk.Label(painel, text=f"{len(dispositivos)} dispositivos    •    {ligados} ligados    •    {conectados} no Wi-Fi",
                 bg="#155A9D", fg="#FFFFFF", font=(FONTE_INTERFACE, 11, "bold")).pack(anchor="w", pady=(20, 0))
        return painel
    # --------------- Gradiente inspirado no painel de casa inteligente -----------
    painel = tk.Canvas(pai, height=218, bg="#0C559A", bd=0, highlightthickness=0)
    painel.pack(fill="x", pady=(4, 5))

    def desenhar(evento=None):
        painel.delete("all")
        largura = max(painel.winfo_width(), 580)
        altura = 218
        # Gradiente do azul ao pôr do sol, usando apenas Tkinter.
        inicio, centro, fim = (13, 68, 128), (34, 119, 189), (238, 151, 91)
        for indice in range(0, 220, 2):
            progresso = indice / 220
            if progresso < 0.60:
                fracao = progresso / 0.60
                cor_a, cor_b = inicio, centro
            else:
                fracao = (progresso - 0.60) / 0.40
                cor_a, cor_b = centro, fim
            rgb = [round(a + (b - a) * fracao) for a, b in zip(cor_a, cor_b)]
            faixa = "#%02x%02x%02x" % tuple(rgb)
            painel.create_rectangle(0, indice, largura, indice + 3, fill=faixa, outline=faixa)
        painel.create_oval(largura-245, -105, largura+175, 310, fill="#F8B26F", outline="", stipple="gray25")
        painel.create_oval(largura-160, -65, largura+88, 180, fill="#9FD5F9", outline="", stipple="gray25")
        painel.create_oval(largura-20, 65, largura+175, 255, fill="#FFC184", outline="", stipple="gray25")
        painel.create_text(30, 27, text="CASA INTELIGENTE  /  PAINEL PRINCIPAL", anchor="nw",
                           fill="#D8EDFF", font=(FONTE_INTERFACE, 9, "bold"))
        painel.create_text(29, 64, text="Sua casa, do seu jeito.", anchor="nw",
                           fill="white", font=(FONTE_INTERFACE, 25, "bold"))
        painel.create_text(31, 112, text="Veja o que está acontecendo e acesse seus ambientes.", anchor="nw",
                           fill="#EDF7FF", font=(FONTE_INTERFACE, 10))
        painel.create_text(32, 170, text=f"{len(dispositivos)} dispositivos      •      {ligados} ligados      •      {conectados} no Wi-Fi",
                           anchor="nw", fill="white", font=(FONTE_INTERFACE, 11, "bold"))
    painel.bind("<Configure>", desenhar)
    return painel


def criar_card_resumo(pai, titulo, numero, detalhe, cor_chave, simbolo, coluna):
    cartao = criar_cartao(pai, 17)
    cartao.grid(row=0, column=coluna, sticky="nsew", padx=(0, 12) if coluna < 3 else 0)
    icone = tk.Frame(cartao, bg=fundo_icone(cor_chave), width=38, height=38)
    icone.pack(anchor="w")
    icone.pack_propagate(False)
    criar_rotulo(icone, simbolo, 17, "bold", cor(cor_chave), fundo_icone(cor_chave)).pack(expand=True)
    criar_rotulo(cartao, str(numero), 24, "bold").pack(anchor="w", pady=(8, 1))
    criar_rotulo(cartao, titulo, 10, "bold").pack(anchor="w")
    criar_rotulo(cartao, detalhe, 8, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(5, 0))


def criar_atalho_categoria(pai, chave, indice):
    titulo, simbolo, destaque, descricao = CATEGORIAS[chave]
    itens = dispositivos_categoria(chave)
    card = criar_cartao(pai, 18)
    card.grid(row=indice // 2, column=indice % 2, padx=(0, 8) if indice % 2 == 0 else (8, 0), pady=8, sticky="nsew")
    topo = tk.Frame(card, bg=cor("superficie"))
    topo.pack(fill="x")
    bolha = tk.Frame(topo, bg=fundo_icone(destaque), width=50, height=50)
    bolha.pack(side="left")
    bolha.pack_propagate(False)
    criar_rotulo(bolha, simbolo, 22, "bold", cor(destaque), fundo_icone(destaque),
                 fonte=(FONTE_SIMBOLOS, 22, "bold")).pack(expand=True)
    infos = tk.Frame(topo, bg=cor("superficie"))
    infos.pack(side="left", padx=13, fill="x", expand=True)
    criar_rotulo(infos, titulo, 13, "bold").pack(anchor="w")
    criar_rotulo(infos, f"{len(itens)} dispositivo(s)", 9, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(3, 0))
    criar_rotulo(card, descricao, 9, cor_texto=cor("texto_fraco"), justify="left",
                 anchor="w", wraplength=380).pack(anchor="w", pady=(16, 12))
    criar_botao(card, "Abrir categoria  →", lambda chave=chave: navegar_para(chave), "suave", True).pack(anchor="w")


def criar_atalho_comodo(pai, local, indice):
    itens = dispositivos_comodo(local)
    ligados = sum(d.is_ligado() for _, d in itens)
    cartao = criar_cartao(pai, 16)
    cartao.grid(row=indice // 3, column=indice % 3, padx=(0, 10) if indice % 3 < 2 else 0, pady=7, sticky="nsew")
    criar_rotulo(cartao, "⌂", 22, "bold", cor("azul"), fonte=(FONTE_SIMBOLOS, 22, "bold")).pack(anchor="w")
    criar_rotulo(cartao, local, 12, "bold").pack(anchor="w", pady=(6, 0))
    criar_rotulo(cartao, f"{len(itens)} dispositivos  •  {ligados} ligados", 9,
                 cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(4, 12))
    criar_botao(cartao, "Ver ambiente  →", lambda local=local: navegar_para("comodo", local), "suave", True).pack(anchor="w")


def criar_grade_dispositivos(pai, itens):
    if not itens:
        vazio = criar_cartao(pai, 26)
        criar_rotulo(vazio, "Nenhum dispositivo cadastrado nesta categoria.", 11, "bold").pack(anchor="w")
        criar_rotulo(vazio, "Use Adicionar dispositivo para começar.", 9,
                     cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(7, 0))
        vazio.pack(fill="x")
        return
    grade = tk.Frame(pai, bg=cor("fundo"))
    grade.pack(fill="x")
    for n, (id_disp, dispositivo) in enumerate(itens):
        cartao = criar_cartao_dispositivo(grade, id_disp, dispositivo)
        cartao.grid(row=n // 2, column=n % 2, padx=(0, 8) if n % 2 == 0 else (8, 0), pady=8, sticky="nsew")
    grade.grid_columnconfigure(0, weight=1, uniform="dispositivos")
    grade.grid_columnconfigure(1, weight=1, uniform="dispositivos")


def criar_indicador(pai, estado, texto):
    linha = tk.Frame(pai, bg=cor("superficie"))
    cor_ponto = cor("verde") if estado == "Conectado" else cor("vermelho") if estado == "Desconectado" else cor("texto_sutil")
    ponto = tk.Canvas(linha, width=11, height=11, bg=cor("superficie"), highlightthickness=0)
    ponto.create_oval(2, 2, 9, 9, fill=cor_ponto, outline=cor_ponto)
    ponto.pack(side="left", padx=(0, 5))
    criar_rotulo(linha, texto, 8, cor_texto=cor("texto_fraco")).pack(side="left")
    return linha


def criar_cartao_dispositivo(pai, id_disp, dispositivo):
    # --------------- Cartão do dispositivo: estado, Wi-Fi e controles -----------
    cartao = criar_cartao(pai, 16)
    simbolo, destaque = obter_icone(dispositivo)
    titulo = dispositivo.get_nome().title()
    comodo = obter_comodo(id_disp, dispositivo)
    linha = tk.Frame(cartao, bg=cor("superficie"))
    linha.pack(fill="x")
    bloco_icone = tk.Frame(linha, bg=fundo_icone(destaque), width=52, height=52)
    bloco_icone.pack(side="left")
    bloco_icone.pack_propagate(False)
    criar_rotulo(bloco_icone, simbolo, 22, "bold", cor(destaque), fundo_icone(destaque),
                 fonte=(FONTE_SIMBOLOS, 22, "bold")).pack(expand=True)
    bloco_nome = tk.Frame(linha, bg=cor("superficie"))
    bloco_nome.pack(side="left", padx=(11, 0), fill="both", expand=True)
    criar_rotulo(bloco_nome, titulo, 12, "bold", anchor="w", wraplength=210, justify="left").pack(anchor="w")
    criar_rotulo(bloco_nome, f"{nome_tipo(dispositivo)}  •  ID {id_disp}", 8,
                 cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(3, 0))
    estado = "Ligado" if dispositivo.is_ligado() else "Desligado"
    destaque_estado = "verde" if dispositivo.is_ligado() else "vermelho"
    linha_estado = tk.Frame(cartao, bg=cor("superficie"))
    linha_estado.pack(fill="x", pady=(13, 5))
    criar_etiqueta(linha_estado, "●  " + estado, destaque_estado).pack(side="left")
    criar_botao(linha_estado, "⌖  " + comodo, lambda id_disp=id_disp: editar_comodo(id_disp),
                "suave", True).pack(side="right")
    wifi = obter_status_wifi(dispositivo)
    criar_indicador(cartao, wifi, "Wi-Fi: " + wifi).pack(anchor="w", pady=(4, 5))
    descricao = dispositivo.testar_status() if dispositivo.is_ligado() else f"{titulo} está desligado."
    criar_rotulo(cartao, descricao, 9, cor_texto=cor("texto_fraco"),
                 justify="left", anchor="w", wraplength=340).pack(anchor="w", pady=(5, 10))
    tk.Frame(cartao, bg=cor("borda"), height=1).pack(fill="x", pady=(0, 12))
    acoes = tk.Frame(cartao, bg=cor("superficie"))
    acoes.pack(fill="x")
    if dispositivo.is_ligado():
        criar_botao(acoes, "●  Desligar", lambda i=id_disp: desligar_dispositivo(i), "perigo", True).pack(side="left", padx=(0, 5))
    else:
        criar_botao(acoes, "●  Ligar", lambda i=id_disp: ligar_dispositivo(i), "positivo", True).pack(side="left", padx=(0, 5))
    criar_botao(acoes, "Detalhes", lambda i=id_disp: mostrar_detalhes(i), "suave", True).pack(side="left", padx=4)
    criar_botao(acoes, "Remover", lambda i=id_disp: remover_dispositivo(i), "suave", True).pack(side="right")
    if isinstance(dispositivo, ConexaoWiFi):
        wifi_linha = tk.Frame(cartao, bg=cor("superficie"))
        wifi_linha.pack(fill="x", pady=(8, 0))
        if wifi == "Conectado":
            criar_botao(wifi_linha, "◉  Desconectar Wi-Fi", lambda i=id_disp: desconectar_wifi(i), "suave", True).pack(anchor="w")
        else:
            criar_botao(wifi_linha, "◉  Conectar Wi-Fi", lambda i=id_disp: conectar_wifi(i), "suave", True).pack(anchor="w")

    # --------------- Lâmpada: seletor visual de cor -----------
    if isinstance(dispositivo, LampadaInteligente):
        criar_rotulo(cartao, "Cor da luz", 9, "bold", cor("texto_fraco")).pack(anchor="w", pady=(15, 6))
        linha_cores = tk.Frame(cartao, bg=cor("superficie"))
        linha_cores.pack(anchor="w")
        for cor_nome, cor_visual in [("Branca", "#EFEFE6"), ("Amarela", "#F3C963"),
                                     ("Azul", "#67B7FF"), ("Vermelha", "#F4707C"), ("Verde", "#4CD2A0")]:
            tk.Button(linha_cores, text="●", bg=cor("superficie"), fg=cor_visual,
                      activebackground=cor("superficie"), bd=0, cursor="hand2",
                      font=(FONTE_INTERFACE, 20, "bold"), relief="flat", highlightthickness=0,
                      command=lambda i=id_disp, c=cor_nome: mudar_cor_lampada(i, c)).pack(side="left", padx=(0, 7))

    # --------------- Ar-condicionado: ajuste de temperatura e temporizador -----------
    elif isinstance(dispositivo, ArCondicionado):
        linha_ar = tk.Frame(cartao, bg=cor("superficie"))
        linha_ar.pack(fill="x", pady=(13, 0))
        criar_rotulo(linha_ar, f"{extrair_temperatura_ar(dispositivo)}°C", 24, "bold", cor("ciano")).pack(side="left", padx=(0, 12))
        criar_botao(linha_ar, "−", lambda i=id_disp: ajustar_temperatura_ar(i, -1), "suave", True).pack(side="left", padx=3)
        criar_botao(linha_ar, "+", lambda i=id_disp: ajustar_temperatura_ar(i, 1), "suave", True).pack(side="left", padx=3)
        criar_botao(linha_ar, "Definir", lambda i=id_disp: ajustar_temperatura_ar(i), "suave", True).pack(side="left", padx=3)
        temporizador = tk.Frame(cartao, bg=cor("superficie"))
        temporizador.pack(fill="x", pady=(10, 0))
        criar_botao(temporizador, "Temporizador", lambda i=id_disp: definir_temporizador(i), "suave", True).pack(side="left", padx=(0, 6))
        criar_botao(temporizador, "Cancelar", lambda i=id_disp: cancelar_temporizador(i), "suave", True).pack(side="left")

    # --------------- Sensores: ações de simulação mantidas -----------
    elif isinstance(dispositivo, SensorPresenca):
        linha_sensor = tk.Frame(cartao, bg=cor("superficie"))
        linha_sensor.pack(fill="x", pady=(13, 0))
        criar_botao(linha_sensor, "Presença detectada", lambda i=id_disp: simular_presenca(i, True), "suave", True).pack(side="left", padx=(0, 4))
        criar_botao(linha_sensor, "Sem presença", lambda i=id_disp: simular_presenca(i, False), "suave", True).pack(side="left")
    elif isinstance(dispositivo, SensorTemperatura):
        criar_botao(cartao, "Atualizar temperatura", lambda i=id_disp: atualizar_sensor_temperatura(i), "suave", True).pack(anchor="w", pady=(13, 0))

    # --------------- Alexa: comandos manuais, microfone e escuta contínua -----------
    elif isinstance(dispositivo, AssistenteVirtual):
        faixa = tk.Frame(cartao, bg=cor("superficie"))
        faixa.pack(fill="x", pady=(13, 0))
        if voz_em_execucao and voz_id_assistente == id_disp:
            criar_botao(faixa, "■ Parar escuta", parar_escuta_voz, "perigo", True).pack(side="left")
        else:
            criar_botao(faixa, "◉ Ouvir uma vez", lambda i=id_disp: iniciar_comando_voz(i), "primario", True).pack(side="left", padx=(0, 6))
            criar_botao(faixa, "▶ Escuta contínua", lambda i=id_disp: iniciar_comando_voz(i, True), "suave", True).pack(side="left")
        outros = tk.Frame(cartao, bg=cor("superficie"))
        outros.pack(fill="x", pady=(7, 0))
        criar_botao(outros, "Digitar comando", lambda i=id_disp: comando_manual_assistente(i), "suave", True).pack(side="left", padx=(0, 6))
        criar_botao(outros, "Microfone", configurar_microfone, "suave", True).pack(side="left")
        criar_rotulo(cartao, "", 9, "bold", cor("ciano"), wraplength=340,
                     justify="left", textvariable=texto_estado_voz).pack(anchor="w", pady=(11, 2))
        criar_rotulo(cartao, "", 8, cor_texto=cor("texto_fraco"), wraplength=340,
                     justify="left", textvariable=texto_ultimo_comando).pack(anchor="w", pady=(2, 0))
    return cartao


def criar_secao_dispositivos(pai, titulo, icone, cor_icone, dispositivos, chave):
    secao = tk.Frame(pai, bg=cor("fundo"))
    secao.pack(fill="x", pady=(17, 0))
    secoes_painel[chave] = secao
    topo = tk.Frame(secao, bg=cor("fundo"))
    topo.pack(fill="x", pady=(0, 9))
    criar_rotulo(topo, f"{icone}  {titulo}", 13, "bold", cor(cor_icone), cor("fundo")).pack(side="left")
    criar_rotulo(topo, f"{len(dispositivos)} dispositivo(s)", 9, cor_texto=cor("texto_sutil"), fundo=cor("fundo")).pack(side="right")

    if not dispositivos:
        vazio = criar_cartao(secao, 14)
        criar_rotulo(vazio, "Nenhum dispositivo cadastrado nesta categoria.", 9, cor_texto=cor("texto_fraco")).pack(anchor="w")
        vazio.pack(fill="x")
        return

    grade = tk.Frame(secao, bg=cor("fundo"))
    grade.pack(fill="x")
    for indice, (id_disp, dispositivo) in enumerate(dispositivos):
        cartao = criar_cartao_dispositivo(grade, id_disp, dispositivo)
        cartao.grid(row=indice // 2, column=indice % 2, sticky="nsew", padx=(0, 9) if indice % 2 == 0 else (9, 0), pady=7)
    grade.grid_columnconfigure(0, weight=1, uniform="cartoes")
    grade.grid_columnconfigure(1, weight=1, uniform="cartoes")


def criar_cartao_resumo(pai, titulo, valor, descricao, cor_destaque, icone):
    cartao = criar_cartao(pai, 14)
    cartao.grid_columnconfigure(0, weight=1)
    criar_rotulo(cartao, icone, 16, "bold", cor(cor_destaque)).grid(row=0, column=0, sticky="w")
    criar_rotulo(cartao, str(valor), 23, "bold").grid(row=1, column=0, sticky="w", pady=(5, 0))
    criar_rotulo(cartao, titulo, 10, "bold").grid(row=2, column=0, sticky="w", pady=(1, 0))
    criar_rotulo(cartao, descricao, 8, cor_texto=cor("texto_fraco")).grid(row=3, column=0, sticky="w", pady=(4, 0))
    return cartao


def criar_area_sensores(pai, dispositivos):
    cartao = criar_cartao(pai, 15)
    criar_rotulo(cartao, "Sensores", 12, "bold").pack(anchor="w")
    criar_rotulo(cartao, "Leituras e estados informados pelos sensores cadastrados.", 8, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(3, 10))
    if not dispositivos:
        criar_rotulo(cartao, "Nenhum sensor cadastrado.", 9, cor_texto=cor("texto_sutil")).pack(anchor="w")
    else:
        for id_disp, dispositivo in dispositivos:
            linha = tk.Frame(cartao, bg=cor("superficie"))
            linha.pack(fill="x", pady=5)
            icone, cor_icone = obter_icone(dispositivo)
            criar_rotulo(linha, icone, 15, "bold", cor(cor_icone), fonte=(FONTE_SIMBOLOS, 15, "bold")).pack(side="left", padx=(0, 8))
            bloco = tk.Frame(linha, bg=cor("superficie"))
            bloco.pack(side="left", fill="x", expand=True)
            criar_rotulo(bloco, dispositivo.get_nome().title(), 9, "bold").pack(anchor="w")
            criar_rotulo(bloco, dispositivo.testar_status(), 8, cor_texto=cor("texto_fraco"), wraplength=360, justify="left").pack(anchor="w", pady=(2, 0))
    return cartao


def criar_area_historico(pai):
    cartao = criar_cartao(pai, 15)
    topo = tk.Frame(cartao, bg=cor("superficie"))
    topo.pack(fill="x")
    criar_rotulo(topo, "Histórico de atividades", 12, "bold").pack(side="left")
    criar_botao(topo, "Limpar", limpar_historico, "suave", True).pack(side="right")
    criar_rotulo(cartao, "Operações realizadas nesta interface.", 8, cor_texto=cor("texto_fraco")).pack(anchor="w", pady=(3, 10))
    linhas = historico_atividades or carregar_historico()
    if not linhas:
        criar_rotulo(cartao, "Nenhuma atividade registrada ainda.", 9, cor_texto=cor("texto_sutil")).pack(anchor="w")
    else:
        for linha in linhas[:8]:
            criar_rotulo(cartao, linha, 8, cor_texto=cor("texto_fraco"), justify="left", anchor="w", wraplength=460).pack(anchor="w", pady=3)
    return cartao


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


def atualizar_lista():
    """Atualiza os resumos, os cartoes, os sensores e o historico."""
    renderizar_painel()


def renderizar_painel():
    # --------------- Navegação por páginas: sem misturar todas as categorias -----------
    if painel_scroll is None or not painel_scroll.winfo_exists():
        return
    for item in painel_scroll.winfo_children():
        item.destroy()
    secoes_painel.clear()
    dispositivos = casa.listar_dispositivos()
    ligados = sum(d.is_ligado() for _, d in dispositivos)
    desligados = len(dispositivos) - ligados
    conectados = sum(isinstance(d, ConexaoWiFi) and obter_status_wifi(d) == "Conectado" for _, d in dispositivos)
    sensores = [(i, d) for i, d in dispositivos if isinstance(d, (SensorPresenca, SensorTemperatura))]

    if pagina_atual == "inicio":
        criar_hero(painel_scroll, dispositivos, ligados, conectados)
        topo = titulo_secao(painel_scroll, "Visão geral", "Tudo o que você precisa saber sobre sua casa.")
        criar_botao(topo, "+ Adicionar dispositivo", adicionar_dispositivo, "primario", True).pack(side="right")
        resumo = tk.Frame(painel_scroll, bg=cor("fundo"))
        resumo.pack(fill="x")
        for n, valores in enumerate([
            ("Dispositivos", len(dispositivos), "Cadastrados", "azul", "⌂"),
            ("Ligados", ligados, "Em funcionamento", "verde", "●"),
            ("Desligados", desligados, "Fora de funcionamento", "vermelho", "○"),
            ("Wi-Fi", conectados, "Conectados", "ciano", "◉"),
        ]):
            criar_card_resumo(resumo, *valores, n)
            resumo.grid_columnconfigure(n, weight=1, uniform="resumo")
        titulo_secao(painel_scroll, "Categorias", "Selecione uma categoria para abrir sua própria página.")
        atalhos = tk.Frame(painel_scroll, bg=cor("fundo"))
        atalhos.pack(fill="x")
        for indice, chave in enumerate(CATEGORIAS):
            criar_atalho_categoria(atalhos, chave, indice)
        atalhos.grid_columnconfigure(0, weight=1, uniform="categorias")
        atalhos.grid_columnconfigure(1, weight=1, uniform="categorias")
        titulo_secao(painel_scroll, "Cômodos", "Os dispositivos são agrupados pelo ambiente cadastrado.")
        locais = lista_comodos()
        if locais:
            grade = tk.Frame(painel_scroll, bg=cor("fundo"))
            grade.pack(fill="x")
            for indice, local in enumerate(locais):
                criar_atalho_comodo(grade, local, indice)
            for coluna in range(3):
                grade.grid_columnconfigure(coluna, weight=1, uniform="ambientes")
        else:
            criar_rotulo(painel_scroll, "Nenhum cômodo cadastrado ainda.", 9,
                         cor_texto=cor("texto_fraco"), fundo=cor("fundo")).pack(anchor="w")
        titulo_secao(painel_scroll, "Atividade e sensores")
        linha = tk.Frame(painel_scroll, bg=cor("fundo"))
        linha.pack(fill="x", pady=(0, 10))
        criar_area_historico(linha).grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        criar_area_sensores(linha, sensores).grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        linha.grid_columnconfigure(0, weight=1, uniform="rodape")
        linha.grid_columnconfigure(1, weight=1, uniform="rodape")

    elif pagina_atual in CATEGORIAS:
        nome, simbolo, destaque, descricao = CATEGORIAS[pagina_atual]
        topo = tk.Frame(painel_scroll, bg=cor("fundo"))
        topo.pack(fill="x", pady=(10, 20))
        criar_rotulo(topo, f"{simbolo}  {nome}", 23, "bold", cor(destaque), cor("fundo")).pack(anchor="w")
        criar_rotulo(topo, descricao, 10, cor_texto=cor("texto_fraco"), fundo=cor("fundo")).pack(anchor="w", pady=(5, 0))
        itens = dispositivos_categoria(pagina_atual)
        criar_rotulo(painel_scroll, f"{len(itens)} dispositivo(s) nesta categoria", 10,
                     "bold", cor("texto_fraco"), cor("fundo")).pack(anchor="w", pady=(0, 12))
        criar_grade_dispositivos(painel_scroll, itens)
        if pagina_atual == "assistentes":
            dica = criar_cartao(painel_scroll, 18)
            dica.pack(fill="x", pady=(13, 0))
            criar_rotulo(dica, "Exemplos de comandos", 11, "bold").pack(anchor="w")
            criar_rotulo(dica,
                         '"Alexa, ligar todos os dispositivos"   •   "Alexa, desligar Sala"   •   "Alexa, ligar Lâmpada Sala"',
                         9, cor_texto=cor("texto_fraco"), justify="left", wraplength=740).pack(anchor="w", pady=(8, 0))

    elif pagina_atual == "comodo":
        local = comodo_ativo or "Sem Cômodo"
        criar_rotulo(painel_scroll, "⌂  " + local, 23, "bold", cor("texto"), cor("fundo")).pack(anchor="w", pady=(10, 5))
        criar_rotulo(painel_scroll, "Dispositivos deste ambiente.", 10,
                     cor_texto=cor("texto_fraco"), fundo=cor("fundo")).pack(anchor="w", pady=(0, 20))
        itens = dispositivos_comodo(local)
        criar_rotulo(painel_scroll, f"{len(itens)} dispositivo(s)  •  {sum(d.is_ligado() for _, d in itens)} ligado(s)",
                     10, "bold", cor("texto_fraco"), cor("fundo")).pack(anchor="w", pady=(0, 12))
        criar_grade_dispositivos(painel_scroll, itens)

    elif pagina_atual == "atividade":
        criar_rotulo(painel_scroll, "◷  Histórico de atividades", 23, "bold", cor("texto"), cor("fundo")).pack(anchor="w", pady=(10, 5))
        criar_rotulo(painel_scroll, "Operações realizadas nesta interface.", 10,
                     cor_texto=cor("texto_fraco"), fundo=cor("fundo")).pack(anchor="w", pady=(0, 18))
        cartao = criar_cartao(painel_scroll, 20)
        cartao.pack(fill="x")
        criar_botao(cartao, "Limpar histórico", limpar_historico, "suave", True).pack(anchor="e", pady=(0, 12))
        for linha_historico in (historico_atividades or ["Nenhuma atividade registrada ainda."])[:100]:
            item = tk.Frame(cartao, bg=cor("superficie"))
            item.pack(fill="x", pady=3)
            criar_rotulo(item, "●", 9, "bold", cor("azul")).pack(side="left", padx=(0, 10))
            criar_rotulo(item, linha_historico, 9, cor_texto=cor("texto_fraco"),
                         justify="left", wraplength=780).pack(side="left", fill="x", expand=True, anchor="w")
        titulo_secao(painel_scroll, "Sensores", "Leituras e estados dos sensores cadastrados.")
        criar_area_sensores(painel_scroll, sensores).pack(fill="x")

    criar_rotulo(painel_scroll,
        "Os indicadores verde e vermelho representam o estado lógico do Wi-Fi dos dispositivos compatíveis. Cinza significa que não possuem Wi-Fi no modelo atual.",
        8, cor_texto=cor("texto_sutil"), fundo=cor("fundo"), justify="left", wraplength=830).pack(anchor="w", pady=(23, 22))


def alternar_tema():
    global tema_atual
    tema_atual = "claro" if tema_atual == "escuro" else "escuro"
    montar_interface()


def montar_interface():
    # --------------- Estrutura principal: menu lateral e páginas independentes -----------
    global canvas_painel, painel_scroll, status_bar, label_caminho
    janela.unbind_all("<MouseWheel>")
    for item in janela.winfo_children():
        item.destroy()
    menu_botoes.clear()
    janela.configure(bg=cor("fundo"))

    estrutura = tk.Frame(janela, bg=cor("fundo"))
    estrutura.pack(fill="both", expand=True)
    lateral = tk.Frame(estrutura, bg=cor("lateral"), width=227, padx=16, pady=22)
    lateral.pack(side="left", fill="y")
    lateral.pack_propagate(False)
    bloco_marca = tk.Frame(lateral, bg=cor("lateral"))
    bloco_marca.pack(fill="x", pady=(3, 35))
    marca_icone = tk.Frame(bloco_marca, bg=fundo_icone("azul"), width=48, height=48)
    marca_icone.pack(side="left")
    marca_icone.pack_propagate(False)
    criar_rotulo(marca_icone, "⌂", 26, "bold", cor("azul"), fundo_icone("azul"),
                 fonte=(FONTE_SIMBOLOS, 26, "bold")).pack(expand=True)
    nome = tk.Frame(bloco_marca, bg=cor("lateral"))
    nome.pack(side="left", padx=10)
    criar_rotulo(nome, "CASA", 13, "bold", cor("texto"), cor("lateral")).pack(anchor="w")
    criar_rotulo(nome, "INTELIGENTE", 8, "bold", cor("texto_fraco"), cor("lateral")).pack(anchor="w")
    criar_rotulo(lateral, "PAINEL", 8, "bold", cor("texto_sutil"), cor("lateral")).pack(anchor="w", pady=(0, 10))

    def botao_menu(titulo, simbolo, chave, destaque):
        ativo = pagina_atual == chave
        parametros = dict(text=f"{simbolo}    {titulo}", anchor="w",
                          font=(FONTE_INTERFACE, 10, "bold" if ativo else "normal"),
                          bg=cor("superficie_2") if ativo else cor("lateral"),
                          fg=cor(destaque) if ativo else cor("texto_fraco"),
                          relief="flat", bd=0, highlightthickness=0,
                          padx=13, pady=11, cursor="hand2")
        if MODO_MAC:
            botao = tk.Label(lateral, takefocus=1, **parametros)
            botao.bind("<Button-1>", lambda evento, chave=chave: navegar_para(chave))
            botao.bind("<Return>", lambda evento, chave=chave: navegar_para(chave))
        else:
            botao = tk.Button(lateral, command=lambda chave=chave: navegar_para(chave),
                              activebackground=cor("superficie_2"), activeforeground=cor("texto"),
                              **parametros)
        botao.pack(fill="x", pady=3)
        menu_botoes[chave] = botao

    botao_menu("Visão geral", "⌂", "inicio", "azul")
    botao_menu("Iluminação", "✦", "lampadas", "amarelo")
    botao_menu("Climatização", "❄", "ar", "ciano")
    botao_menu("Sensores", "◉", "sensores", "roxo")
    botao_menu("Assistente Virtual", "◖))", "assistentes", "azul")
    botao_menu("Atividades", "◷", "atividade", "verde")
    area_lateral = tk.Frame(lateral, bg=cor("lateral"))
    area_lateral.pack(side="bottom", fill="x")
    tk.Frame(area_lateral, bg=cor("borda"), height=1).pack(fill="x", pady=(0, 17))
    criar_rotulo(area_lateral, "●  Sistema local", 9, "bold", cor("verde"), cor("lateral")).pack(anchor="w")
    criar_rotulo(area_lateral, "Dados salvos em dispositivos_casa.pkl",
                 8, cor_texto=cor("texto_sutil"), fundo=cor("lateral"), wraplength=185, justify="left").pack(anchor="w", pady=(8, 0))

    principal = tk.Frame(estrutura, bg=cor("fundo"))
    principal.pack(side="left", fill="both", expand=True)
    barra_topo = tk.Frame(principal, bg=cor("fundo"), padx=26, pady=15)
    barra_topo.pack(fill="x")
    label_caminho = criar_rotulo(barra_topo, "Meu lar  /  " + (CATEGORIAS[pagina_atual][0] if pagina_atual in CATEGORIAS else "Visão geral" if pagina_atual == "inicio" else "Atividades" if pagina_atual == "atividade" else comodo_ativo or "Cômodos"),
                                 10, "bold", cor("texto_fraco"), cor("fundo"))
    label_caminho.pack(side="left", padx=(0, 8))
    criar_botao(barra_topo, "☀ Modo claro" if tema_atual == "escuro" else "☾ Modo escuro",
                alternar_tema, "suave", True).pack(side="right", padx=(9, 0))
    criar_botao(barra_topo, "+ Adicionar", adicionar_dispositivo, "primario", True).pack(side="right")

    corpo = tk.Frame(principal, bg=cor("fundo"))
    corpo.pack(fill="both", expand=True, padx=(25, 11), pady=(0, 9))
    canvas_painel = tk.Canvas(corpo, bg=cor("fundo"), highlightthickness=0, bd=0)
    barra_rolagem = ttk.Scrollbar(corpo, orient="vertical", command=canvas_painel.yview)
    canvas_painel.configure(yscrollcommand=barra_rolagem.set)
    barra_rolagem.pack(side="right", fill="y")
    canvas_painel.pack(side="left", fill="both", expand=True)
    painel_scroll = tk.Frame(canvas_painel, bg=cor("fundo"))
    janela_canvas = canvas_painel.create_window((0, 0), window=painel_scroll, anchor="nw", width=900)
    painel_scroll.bind("<Configure>", lambda evento: canvas_painel.configure(scrollregion=canvas_painel.bbox("all")))
    canvas_painel.bind("<Configure>", lambda evento: canvas_painel.itemconfigure(janela_canvas, width=evento.width))
    canvas_painel.bind_all("<MouseWheel>", lambda evento: canvas_painel.yview_scroll(-1 if evento.delta > 0 else 1, "units"))

    status_bar = tk.Label(principal, text="Sistema pronto.", anchor="w", bg=cor("lateral"), fg=cor("texto_fraco"),
                          font=(FONTE_INTERFACE, 9), padx=22, pady=8)
    status_bar.pack(fill="x", side="bottom")
    renderizar_painel()

    if MODO_MAC:
        # Corrige o tamanho da área rolável após a janela aparecer na tela.
        def ajustar_canvas_mac():
            if not canvas_painel.winfo_exists():
                return
            canvas_painel.update_idletasks()
            largura = max(canvas_painel.winfo_width(), 400)
            canvas_painel.itemconfigure(janela_canvas, width=largura)
            painel_scroll.update_idletasks()
            canvas_painel.configure(scrollregion=canvas_painel.bbox("all"))
            canvas_painel.yview_moveto(0)
        janela.after(200, ajustar_canvas_mac)


reparar_wifi_antigo()
locais_dispositivos = carregar_comodos()
historico_atividades = carregar_historico()
try:
    montar_interface()
except Exception as erro:
    registrar_erro_interface(type(erro), erro, erro.__traceback__)
    raise
janela.after(120, processar_eventos_voz)
janela.protocol("WM_DELETE_WINDOW", fechar_interface)
janela.mainloop()
