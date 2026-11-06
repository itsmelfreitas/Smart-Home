import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from CasaInteligente import (
    CasaInteligente,
    LampadaInteligente,
    ArCondicionado,
    SensorPresenca,
    SensorTemperatura,
    ConexaoWiFi,
)



casa = CasaInteligente()

janela = tk.Tk()
janela.title("Casa Inteligente - Painel de Controle")
janela.geometry("1050x650")
janela.minsize(900, 550)

estilo = ttk.Style()
try:
    estilo.theme_use("clam")
except tk.TclError:
    pass


def reparar_wifi_antigo():
    """Inicializa o Wi-Fi de aparelhos antigos salvos sem esses atributos."""
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


def obter_selecionado():
    """Retorna (ID, objeto) do dispositivo selecionado na tabela."""
    selecionados = tabela.selection()

    if not selecionados:
        messagebox.showwarning(
            "Selecao necessaria",
            "Selecione um dispositivo na lista primeiro."
        )
        return None, None

    valores = tabela.item(selecionados[0], "values")
    id_disp = int(valores[0])

    try:
        dispositivo = casa.get_dispositivo(id_disp)
        return id_disp, dispositivo
    except Exception as erro:
        messagebox.showerror("Erro", str(erro))
        atualizar_lista()
        return None, None


def nome_tipo(dispositivo):
    if isinstance(dispositivo, LampadaInteligente):
        return "Lampada"
    if isinstance(dispositivo, ArCondicionado):
        return "Ar-condicionado"
    if isinstance(dispositivo, SensorPresenca):
        return "Sensor de presenca"
    if isinstance(dispositivo, SensorTemperatura):
        return "Sensor de temperatura"
    return "Dispositivo"


# ATUALIZACAO DA TABELA

def atualizar_lista():
    for item in tabela.get_children():
        tabela.delete(item)

    dispositivos = casa.listar_dispositivos()

    for id_disp, dispositivo in dispositivos:
        nome = dispositivo.get_nome()
        tipo = nome_tipo(dispositivo)
        status = "Ligado" if dispositivo.is_ligado() else "Desligado"

        if isinstance(dispositivo, ConexaoWiFi):
            try:
                wifi = "Conectado" if dispositivo.is_conectado_wifi() else "Desconectado"
            except AttributeError:
                wifi = "Nao inicializado"
        else:
            wifi = "Nao possui"

        tabela.insert(
            "",
            tk.END,
            values=(id_disp, nome, tipo, status, wifi)
        )

    quantidade = len(dispositivos)
    contador.config(text=f"Dispositivos cadastrados: {quantidade}")


def mostrar_detalhes():
    id_disp, dispositivo = obter_selecionado()
    if dispositivo is None:
        return

    detalhes = (
        f"ID: {id_disp}\n"
        f"Nome: {dispositivo.get_nome()}\n"
        f"Tipo: {nome_tipo(dispositivo)}\n"
        f"Estado: {'Ligado' if dispositivo.is_ligado() else 'Desligado'}\n\n"
        f"{dispositivo.testar_status()}"
    )

    if isinstance(dispositivo, ConexaoWiFi):
        try:
            detalhes += (
                f"\n\nRede Wi-Fi: {dispositivo.get_ssid()}"
                f"\nConexao: {'Conectado' if dispositivo.is_conectado_wifi() else 'Desconectado'}"
            )
        except AttributeError:
            detalhes += "\n\nWi-Fi ainda nao inicializado."

    messagebox.showinfo("Detalhes do dispositivo", detalhes)


# ADICIONAR DISPOSITIVO

def adicionar_dispositivo():
    id_disp = simpledialog.askinteger(
        "Adicionar dispositivo",
        "Digite um ID inteiro positivo:",
        parent=janela,
        minvalue=1
    )
    if id_disp is None:
        return

    tipo = simpledialog.askstring(
        "Tipo de dispositivo",
        "Digite uma opcao:\nlampada\nar\npresenca\ntemperatura",
        parent=janela
    )
    if tipo is None:
        return
    tipo = tipo.strip().lower()

    nome = simpledialog.askstring(
        "Nome do dispositivo",
        "Digite o nome do dispositivo:",
        parent=janela
    )
    if nome is None:
        return
    nome = nome.strip()

    if not nome:
        messagebox.showwarning("Campo obrigatorio", "O nome nao pode ficar vazio.")
        return

    try:
        if tipo == "lampada":
            dispositivo = LampadaInteligente(nome)
        elif tipo in ("ar", "ar-condicionado", "ar condicionado"):
            dispositivo = ArCondicionado(nome)
        elif tipo in ("presenca", "presença"):
            dispositivo = SensorPresenca(nome)
        elif tipo in ("temperatura", "sensor de temperatura"):
            dispositivo = SensorTemperatura(nome)
        else:
            messagebox.showerror(
                "Tipo invalido",
                "Escolha: lampada, ar, presenca ou temperatura."
            )
            return


        if isinstance(dispositivo, ConexaoWiFi):
            ssid = simpledialog.askstring(
                "Rede Wi-Fi",
                "Nome da rede Wi-Fi:",
                parent=janela,
                initialvalue="Casa"
            )
            if ssid is None:
                return
            ssid = ssid.strip()

            senha = simpledialog.askstring(
                "Senha Wi-Fi",
                "Senha da rede:",
                parent=janela,
                show="*",
                initialvalue="12345678"
            )
            if senha is None:
                return

            if not ssid:
                messagebox.showwarning("Campo obrigatorio", "O nome da rede nao pode ficar vazio.")
                return

            ConexaoWiFi.__init__(dispositivo, ssid, senha)

        casa.adicionar_dispositivo(id_disp, dispositivo)
        atualizar_lista()
        messagebox.showinfo("Cadastro concluido", f"{nome} foi cadastrado com sucesso.")

    except Exception as erro:
        messagebox.showerror("Erro ao cadastrar", str(erro))


# REMOVER DISPOSITIVO


def remover_dispositivo():
    id_disp, dispositivo = obter_selecionado()
    if dispositivo is None:
        return

    confirmar = messagebox.askyesno(
        "Confirmar remocao",
        f"Deseja remover '{dispositivo.get_nome()}' (ID {id_disp})?",
        parent=janela
    )

    if not confirmar:
        return

    try:
        casa.remover_dispositivo(id_disp)
        atualizar_lista()
        messagebox.showinfo("Remocao concluida", "Dispositivo removido com sucesso.")
    except Exception as erro:
        messagebox.showerror("Erro ao remover", str(erro))


# LIGAR E DESLIGAR

def ligar_dispositivo():
    id_disp, dispositivo = obter_selecionado()
    if dispositivo is None:
        return

    try:
        casa.ligar_dispositivo(id_disp)
        atualizar_lista()
        messagebox.showinfo("Dispositivo", f"{dispositivo.get_nome()} ligado com sucesso.")
    except Exception as erro:
        messagebox.showerror("Nao foi possivel ligar", str(erro))


def desligar_dispositivo():
    id_disp, dispositivo = obter_selecionado()
    if dispositivo is None:
        return

    try:
        casa.desligar_dispositivo(id_disp)
        atualizar_lista()
        messagebox.showinfo("Dispositivo", f"{dispositivo.get_nome()} desligado com sucesso.")
    except Exception as erro:
        messagebox.showerror("Nao foi possivel desligar", str(erro))


#WIFI


def conectar_wifi():
    id_disp, dispositivo = obter_selecionado()
    if dispositivo is None:
        return

    if not isinstance(dispositivo, ConexaoWiFi):
        messagebox.showwarning(
            "Wi-Fi indisponivel",
            "O dispositivo selecionado nao possui conexao Wi-Fi."
        )
        return

    try:
        rede = dispositivo.get_ssid()
        senha = simpledialog.askstring(
            "Conectar ao Wi-Fi",
            f"Digite a senha da rede '{rede}':",
            parent=janela,
            show="*"
        )
        if senha is None:
            return

        resultado = dispositivo.conectar(senha)
        casa.salvar_estado()
        atualizar_lista()
        messagebox.showinfo("Wi-Fi", resultado)

    except Exception as erro:
        messagebox.showerror("Falha na conexao", str(erro))


def desconectar_wifi():
    id_disp, dispositivo = obter_selecionado()
    if dispositivo is None:
        return

    if not isinstance(dispositivo, ConexaoWiFi):
        messagebox.showwarning(
            "Wi-Fi indisponivel",
            "O dispositivo selecionado nao possui conexao Wi-Fi."
        )
        return

    try:
        resultado = dispositivo.desconectar()
        casa.salvar_estado()
        atualizar_lista()
        messagebox.showinfo("Wi-Fi", resultado)
    except Exception as erro:
        messagebox.showerror("Falha ao desconectar", str(erro))


cabecalho = ttk.Frame(janela, padding=(20, 18))
cabecalho.pack(fill="x")

titulo = ttk.Label(
    cabecalho,
    text="CASA INTELIGENTE",
    font=("Arial", 21, "bold")
)
titulo.pack(anchor="w")

subtitulo = ttk.Label(
    cabecalho,
    text="Painel de gerenciamento de dispositivos",
    font=("Arial", 10)
)
subtitulo.pack(anchor="w", pady=(3, 0))

conteudo = ttk.Frame(janela, padding=(20, 5, 20, 20))
conteudo.pack(fill="both", expand=True)

menu = ttk.LabelFrame(conteudo, text="Menu principal", padding=12)
menu.pack(side="left", fill="y", padx=(0, 18))

area_lista = ttk.LabelFrame(conteudo, text="Dispositivos cadastrados", padding=12)
area_lista.pack(side="right", fill="both", expand=True)



botoes = [
    ("Adicionar dispositivo", adicionar_dispositivo),
    ("Remover selecionado", remover_dispositivo),
    ("Ligar dispositivo", ligar_dispositivo),
    ("Desligar dispositivo", desligar_dispositivo),
    ("Conectar Wi-Fi", conectar_wifi),
    ("Desconectar Wi-Fi", desconectar_wifi),
    ("Ver detalhes", mostrar_detalhes),
    ("Atualizar lista", atualizar_lista),
]

for texto, comando in botoes:
    botao = ttk.Button(menu, text=texto, command=comando)
    botao.pack(fill="x", pady=5)

colunas = ("id", "nome", "tipo", "estado", "wifi")
tabela = ttk.Treeview(
    area_lista,
    columns=colunas,
    show="headings",
    height=18
)

tabela.heading("id", text="ID")
tabela.heading("nome", text="Nome")
tabela.heading("tipo", text="Tipo")
tabela.heading("estado", text="Estado")
tabela.heading("wifi", text="Wi-Fi")

tabela.column("id", width=55, anchor="center")
tabela.column("nome", width=170)
tabela.column("tipo", width=145)
tabela.column("estado", width=100, anchor="center")
tabela.column("wifi", width=115, anchor="center")

tabela.pack(side="top", fill="both", expand=True)

tabela.bind("<Double-1>", lambda evento: mostrar_detalhes())

contador = ttk.Label(area_lista, text="Dispositivos cadastrados: 0")
contador.pack(anchor="w", pady=(10, 0))

orientacao = ttk.Label(
    area_lista,
    text="Selecione um dispositivo na tabela para executar uma acao.",
    foreground="#555555"
)
orientacao.pack(anchor="w", pady=(5, 0))

reparar_wifi_antigo()
atualizar_lista()
janela.mainloop()
