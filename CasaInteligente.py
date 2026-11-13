from abc import ABC, abstractmethod
import pickle
from typing import Dict, List, Tuple, Type
from abc import ABCMeta, abstractmethod


class ComandoVoz(metaclass=ABCMeta):
    
    @abstractmethod
    def executar_comando(self, comando: str, id_disp: int, casa: 'CasaInteligente') -> str:
        pass

class ConexaoWiFi:
    __ssid: str
    __senha: str
    __conectado: bool

    def __init__(self, ssid: str, senha: str):
        self.__ssid = ssid
        self.__senha = senha
        self.__conectado = False

    def get_ssid(self) -> str:
        return self.__ssid

    def is_conectado_wifi(self) -> bool:
        return self.__conectado

    def conectar(self, senha_digitada: str = "12345678") -> str:
        if self.__conectado:
            return f"Já está conectado à rede '{self.__ssid}'."

        if senha_digitada == self.__senha:
            self.__conectado = True
            return f"Conectado com sucesso à rede Wi-Fi '{self.__ssid}'!"
        else:
            raise Exception("Erro Wi-Fi: Senha incorreta!")

    def desconectar(self) -> str:
        if self.__conectado:
            self.__conectado = False
            return f"Desconectado da rede '{self.__ssid}'."
        return "O dispositivo já está desconectado do Wi-Fi."


class AssistenteVirtual(ComandoVoz):
    __nome: str
    
    def __init__(self, nome: str = "Alexa"):
        self.__nome = nome
        
    def executar_comando(self, comando: str, id_disp: int, casa: 'CasaInteligente') -> str:
        if not isinstance(comando, str):
            raise TypeError("O comando deve ser um texto.")
            
        comando = comando.lower()
        
        try:
            if "ligar" in comando:
                casa.ligar_dispositivo(id_disp)
                return f"{self.__nome}: Ok, liguei o dispositivo {id_disp}."
            elif "desligar" in comando:
                casa.desligar_dispositivo(id_disp)
                return f"{self.__nome}: Ok, desliguei o dispositivo {id_disp}."
            else:
                return f"{self.__nome}: Desculpe, não entendi o comando."
        except Exception as e:
            return f"{self.__nome}: Não consegui executar. {str(e)}"
            
    def __str__(self):
        return f"Assistente Virtual\nNome: {self.__nome}"


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


class ArCondicionado(Dispositivo, ConexaoWiFi):
    __temperatura: int
    __temperatizador_min: int

    def __init__(self, nome: str, temperatura_inicial: int = 24):
        super().__init__(nome)
        self.__temperatura = temperatura_inicial
        self.__temperatizador_min = 0

    def ajustar_temperatura(self, temp: int):
        if not self.is_ligado():
            raise Exception("Erro: Não é possível ajustar. O Ar Condicionado está desligado!")
        if temp < 16 or temp > 30:
            raise Exception("Erro: Temperatura inválida! Escolha entre 16°C e 30°C.")
        self.__temperatura = temp

    def definir_temporizador(self, minutos: int) -> str:
        if not self.is_ligado():
            raise Exception("Erro: Não é possível programar o temporizador com o aparelho desligado!")
        if minutos <= 0:
            raise Exception("Erro: O tempo do temporizador deve ser maior que 0 minutos.")
        self.__temperatizador_min = minutos
        return f"Temporizador definido para {minutos} minutos."

    def cancelar_temporizador(self) -> str:
        if self.__temperatizador_min > 0:
            self.__temperatizador_min = 0
            return "Temporizador cancelado."
        else:
            return "Nenhum temporizador ativo para cancelar."

    def testar_status(self):
        return f"O Ar Condicionado {self.get_nome()} está refrigerando a {self.__temperatura}°C."

    def __str__(self):
        info = super().__str__()
        info += f'Temperatura: {self.__temperatura}°C\n'
        return info

    def __repr__(self):
        return f"ArCondicionado({super().__repr__()}, temperatura={self.__temperatura})"

class SensorPresenca(Dispositivo):
    __presenca_detectada: bool

    def __init__(self, nome: str):
        super().__init__(nome)
        self.__presenca_detectada = False

    def simular_deteccao(self, presenca: bool) -> str:
        if not self.is_ligado():
            raise Exception("Erro: O sensor de presença está desligado!")
        if not isinstance(presenca, bool):
            raise ValueError("A presença deve ser informada como True ou False.")

        self.__presenca_detectada = presenca
        if presenca:
            return f"Presença detectada pelo sensor '{self.get_nome()}'."
        return f"Nenhuma presença detectada pelo sensor '{self.get_nome()}'."

    def tem_presenca(self) -> bool:
        return self.__presenca_detectada

    def testar_status(self):
        if not self.is_ligado():
            return f"O sensor de presença {self.get_nome()} está desligado."
        if self.__presenca_detectada:
            return f"O sensor {self.get_nome()} detectou presença."
        return f"O sensor {self.get_nome()} não detectou presença."


class SensorTemperatura(Dispositivo):
    __temperatura: float

    def __init__(self, nome: str, temperatura_inicial: float = 22.0):
        super().__init__(nome)
        self.__temperatura = float(temperatura_inicial)

    def atualizar_temperatura(self, nova_temperatura: float):
        if not self.is_ligado():
            raise Exception("Erro: O sensor de temperatura está desligado!")
        if not isinstance(nova_temperatura, (int, float)):
            raise ValueError("A temperatura precisa ser um número.")
        self.__temperatura = float(nova_temperatura)

    def get_temperatura(self) -> float:
        return self.__temperatura

    def testar_status(self):
        if not self.is_ligado():
            return f"O sensor de temperatura {self.get_nome()} está desligado."
        return f"O sensor {self.get_nome()} está registrando {self.__temperatura:.1f}°C."


class CasaInteligente:
    __dispositivos: Dict[int, Dispositivo]
    __nome_arquivo: str

    def __init__(self, nome_arquivo: str = 'dispositivos_casa.pkl'):
        self.__dispositivos = {}
        self.__nome_arquivo = nome_arquivo
        self.carregar_estado()

    def adicionar_dispositivo(self, id_disp: int, dispositivo: Dispositivo):
        if not isinstance(id_disp, int) or isinstance(id_disp, bool) or id_disp <= 0:
            raise ValueError("O ID deve ser um número inteiro positivo.")
        if not isinstance(dispositivo, Dispositivo):
            raise TypeError("O objeto informado não é um dispositivo válido.")
        if id_disp in self.__dispositivos:
            raise ValueError(f"Já existe um dispositivo cadastrado com o ID {id_disp}.")

        self.__dispositivos[id_disp] = dispositivo
        self.salvar_estado()

    def remover_dispositivo(self, id_disp: int):
        if id_disp not in self.__dispositivos:
            raise Exception("Erro: Dispositivo não encontrado no sistema!")

        dispositivo_removido = self.__dispositivos.pop(id_disp)
        self.salvar_estado()
        return dispositivo_removido

    def get_dispositivo(self, id_disp: int):
        if id_disp in self.__dispositivos:
            return self.__dispositivos[id_disp]
        raise Exception("Erro: Dispositivo não encontrado no sistema!")

    def listar_dispositivos(self) -> List[Tuple[int, Dispositivo]]:
   
        return list(self.__dispositivos.items())

    def listar_por_estado(self, ligado: bool) -> List[Tuple[int, Dispositivo]]:
        return [
            (id_disp, disp)
            for id_disp, disp in self.__dispositivos.items()
            if disp.is_ligado() == ligado
        ]

    def listar_por_tipo(self, tipo_dispositivo: Type[Dispositivo]) -> List[Tuple[int, Dispositivo]]:
        if not isinstance(tipo_dispositivo, type) or not issubclass(tipo_dispositivo, Dispositivo):
            raise TypeError("Informe uma classe válida derivada de Dispositivo.")
        return [
            (id_disp, disp)
            for id_disp, disp in self.__dispositivos.items()
            if isinstance(disp, tipo_dispositivo)
        ]

    def listar_sensores(self) -> List[Tuple[int, Dispositivo]]:
        return [
            (id_disp, disp)
            for id_disp, disp in self.__dispositivos.items()
            if isinstance(disp, (SensorPresenca, SensorTemperatura))
        ]

    def ligar_dispositivo(self, id_disp: int):
        dispositivo = self.get_dispositivo(id_disp)
        dispositivo.ligar()
        self.salvar_estado()

    def desligar_dispositivo(self, id_disp: int):
        dispositivo = self.get_dispositivo(id_disp)
        dispositivo.desligar()
        self.salvar_estado()

    def simular_presenca(self, id_disp: int, presenca: bool) -> str:
        dispositivo = self.get_dispositivo(id_disp)
        if not isinstance(dispositivo, SensorPresenca):
            raise TypeError("O dispositivo informado não é um sensor de presença.")
        resultado = dispositivo.simular_deteccao(presenca)
        self.salvar_estado()
        return resultado

    def atualizar_sensor_temperatura(self, id_disp: int, temperatura: float):
        dispositivo = self.get_dispositivo(id_disp)
        if not isinstance(dispositivo, SensorTemperatura):
            raise TypeError("O dispositivo informado não é um sensor de temperatura.")
        dispositivo.atualizar_temperatura(temperatura)
        self.salvar_estado()

    def exibir_todos(self):
        if not self.__dispositivos:
            print("Nenhum dispositivo cadastrado.")
            return
        for id_disp, disp in self.__dispositivos.items():
            print(f"--- ID {id_disp} ---")
            print(disp)
            print(disp.testar_status())

    def salvar_estado(self):
        with open(self.__nome_arquivo, 'wb') as arquivo:
            pickle.dump(self.__dispositivos, arquivo)

    def carregar_estado(self):
        try:
            with open(self.__nome_arquivo, 'rb') as arquivo:
                dados = pickle.load(arquivo)
                if not isinstance(dados, dict):
                    raise ValueError("O arquivo salvo não contém um cadastro válido.")
                self.__dispositivos = dados
        except FileNotFoundError:
            self.__dispositivos = {}
