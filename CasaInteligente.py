from abc import ABC, abstractmethod
import pickle


class ConexaoWiFi:
    def conectar(self):
        return "Conectado à rede Wi-Fi."
        
    def desconectar(self):
        return "Desconectado da rede Wi-Fi."


class Dispositivo(ABC):
    __nome: str
    __ligado: bool

    def __init__(self, nome: str):
        self.__nome = nome
        self.__ligado = False

    def get_nome(self) -> str:
        return self.__nome
        
    def is_ligado(self) -> bool:
        return self.__ligado

    def ligar(self):
        if not self.__ligado:
            self.__ligado = True
        else:
            raise Exception(f"Erro: {self.__nome} já está ligado!") 

    def desligar(self):
        if self.__ligado:
            self.__ligado = False
        else:
            raise Exception(f"Erro: {self.__nome} já está desligado!") 

    def __str__(self):
        status = "Ligado" if self.__ligado else "Desligado"
        info = (f'Nome: {self.__nome}\n'
                f'Status: {status}\n')
        return info

    def __repr__(self):
        return f"Dispositivo(nome='{self.__nome}', ligado={self.__ligado})"

    @abstractmethod
    def testar_status(self):
        pass


class LampadaInteligente(Dispositivo, ConexaoWiFi):
    __cor: str

    def __init__(self, nome: str, cor_inicial: str = "Branca"):
        super().__init__(nome) 
        self.__cor = cor_inicial

    def mudar_cor(self, nova_cor: str):
        if self.is_ligado():
            self.__cor = nova_cor
        else:
            raise Exception("Erro: Não é possível mudar a cor. A lâmpada está desligada!")

    def testar_status(self):
        return f"A Lâmpada {self.get_nome()} está emitindo luz {self.__cor}."

    def __str__(self):
        info = super().__str__() 
        info += f'Cor: {self.__cor}\n'
        return info

    def __repr__(self):
        return f"LampadaInteligente({super().__repr__()}, cor='{self.__cor}')" 


class ArCondicionado(Dispositivo):
    __temperatura: int

    def __init__(self, nome: str, temperatura_inicial: int = 24):
        super().__init__(nome)
        self.__temperatura = temperatura_inicial

    def ajustar_temperatura(self, temp: int):
        if not self.is_ligado():
            raise Exception("Erro: Não é possível ajustar. O Ar Condicionado está desligado!")
        if temp < 16 or temp > 30:
            raise Exception("Erro: Temperatura inválida! Escolha entre 16°C e 30°C.") 
        self.__temperatura = temp

    def testar_status(self):
        return f"O Ar Condicionado {self.get_nome()} está refrigerando a {self.__temperatura}°C."

    def __str__(self):
        info = super().__str__()
        info += f'Temperatura: {self.__temperatura}°C\n'
        return info

    def __repr__(self):
        return f"ArCondicionado({super().__repr__()}, temperatura={self.__temperatura})"


class CasaInteligente:
    __dispositivos: dict
    __nome_arquivo: str

    def __init__(self):
        self.__dispositivos = {} 
        self.__nome_arquivo = 'dispositivos_casa.pkl'

    def adicionar_dispositivo(self, id_disp: int, dispositivo: Dispositivo):
        self.__dispositivos[id_disp] = dispositivo
        self.salvar_estado()

    def get_dispositivo(self, id_disp: int):
        if id_disp in self.__dispositivos:
            return self.__dispositivos[id_disp]
        else:
            raise Exception("Erro: Dispositivo não encontrado no sistema!")

    def exibir_todos(self):
        for id_disp, disp in self.__dispositivos.items():
            print(f"--- ID {id_disp} ---")
            print(disp) 

    def salvar_estado(self):
        with open(self.__nome_arquivo, 'wb') as arquivo:
            pickle.dump(self.__dispositivos, arquivo) 

    def carregar_estado(self):
        try:
            with open(self.__nome_arquivo, 'rb') as arquivo:
                self.__dispositivos = pickle.load(arquivo)
        except FileNotFoundError:
            self.__dispositivos = {}