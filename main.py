from abc import ABC, abstractmethod
import pickle

from CasaInteligente import (
    CasaInteligente,
    AssistenteVirtual,
    LampadaInteligente,
    ArCondicionado,
    SensorPresenca,
    SensorTemperatura,
)


def exibir_menu():
    print("\n" + "=" * 40)
    print("🏠 CASA INTELIGENTE - MENU INTERATIVO")
    print("=" * 40)
    print("1. Adicionar dispositivo")
    print("2. Listar dispositivos")
    print("3. Ligar dispositivo")
    print("4. Desligar dispositivo")
    print("5. Ajustar temperatura (Ar Condicionado)")
    print("6. Mudar cor (Lâmpada Inteligente)")
    print("7. Simular presença (Sensor de Presença)")
    print("8. Atualizar temperatura (Sensor de Temperatura)")
    print("9. Exibir detalhes de um dispositivo")
    print("0. Sair")
    print("=" * 40)


def selecionar_dispositivo(casa, tipo=None):
    dispositivos = casa.listar_dispositivos()

    if tipo is not None:
        dispositivos = [
            (id_disp, disp)
            for id_disp, disp in dispositivos
            if isinstance(disp, tipo)
        ]

    if not dispositivos:
        print("\nNenhum dispositivo compatível encontrado.")
        return None

    print("\n📋 Selecione um dispositivo:")
    print("-" * 40)

    for indice, (id_disp, dispositivo) in enumerate(dispositivos, start=1):
        nome = dispositivo.get_nome().title()
        estado = "Ligado" if dispositivo.is_ligado() else "Desligado"
    
        print(f"{indice}. {nome} | {estado}")

    print("0. Voltar")

    try:
        escolha = int(input("\nEscolha o dispositivo: "))

        if escolha == 0:
            return None

        if escolha < 1 or escolha > len(dispositivos):
            print("Opção inválida!")
            return None

        return dispositivos[escolha - 1][0]

    except ValueError:
        print("Digite uma opção numérica válida!")
        return None


def main():
    casa = CasaInteligente()
    assistente = AssistenteVirtual("Jarvis")

    while True:
        exibir_menu()
        opcao = input("Selecione uma opção: ")

        if opcao == "1":
            try:
                ids = casa.listar_ids_dispositivos()

                id_disp = max(ids, default=0) + 1

                tipo = input(
                    "Digite o tipo (lampada, ar, presenca, temperatura): "
                ).strip().lower()

                nome = input("Digite o nome do dispositivo: ")

                if tipo == "lampada":
                    cor = input("Digite a cor inicial da lâmpada: ")
                    dispositivo = LampadaInteligente(nome, cor)

                elif tipo == "ar":
                    temperatura = int(
                        input("Digite a temperatura inicial do ar condicionado: ")
                    )
                    dispositivo = ArCondicionado(nome, temperatura)

                elif tipo == "presenca":
                    dispositivo = SensorPresenca(nome)

                elif tipo == "temperatura":
                    temp_inicial = float(
                        input("Digite a temperatura inicial do sensor: ")
                    )
                    dispositivo = SensorTemperatura(nome, temp_inicial)

                else:
                    print("Tipo inválido!")
                    continue

                casa.adicionar_dispositivo(id_disp, dispositivo)

                print(
                    f"\nDispositivo '{nome}' adicionado com sucesso!"
                )
                print(f"ID interno: {id_disp}")

            except Exception as e:
                print(f"Erro ao adicionar dispositivo: {e}")

        elif opcao == "2":
            print("\n📋 Dispositivos cadastrados:")
            print(casa.exibir_todos())

        elif opcao == "3":
            id_disp = selecionar_dispositivo(casa)

            if id_disp is not None:
                try:
                    casa.ligar_dispositivo(id_disp)
                    dispositivo = casa.get_dispositivo(id_disp)
                    print(
                        f"\n{dispositivo.get_nome()} ligado com sucesso!"
                    )
                except Exception as e:
                    print(f"Erro: {e}")

        elif opcao == "4":
            id_disp = selecionar_dispositivo(casa)

            if id_disp is not None:
                try:
                    casa.desligar_dispositivo(id_disp)
                    dispositivo = casa.get_dispositivo(id_disp)
                    print(
                        f"\n{dispositivo.get_nome()} desligado com sucesso!"
                    )
                except Exception as e:
                    print(f"Erro: {e}")

        elif opcao == "5":
            id_disp = selecionar_dispositivo(casa, ArCondicionado)

            if id_disp is not None:
                try:
                    nova_temp = int(
                        input("Digite a nova temperatura (16-30°C): ")
                    )

                    dispositivo = casa.get_dispositivo(id_disp)
                    dispositivo.ajustar_temperatura(nova_temp)
                    casa.salvar_estado()

                    print(
                        f"Temperatura ajustada para {nova_temp}°C."
                    )

                except Exception as e:
                    print(f"Erro: {e}")

        elif opcao == "6":
            id_disp = selecionar_dispositivo(casa, LampadaInteligente)

            if id_disp is not None:
                try:
                    nova_cor = input("Digite a nova cor da lâmpada: ")

                    dispositivo = casa.get_dispositivo(id_disp)
                    dispositivo.mudar_cor(nova_cor)
                    casa.salvar_estado()

                    print(
                        f"Cor da lâmpada alterada para {nova_cor}."
                    )

                except Exception as e:
                    print(f"Erro: {e}")

        elif opcao == "7":
            id_disp = selecionar_dispositivo(casa, SensorPresenca)

            if id_disp is not None:
                try:
                    resposta = input(
                        "Presença detectada? (s/n): "
                    ).strip().lower()

                    if resposta not in ("s", "n"):
                        print("Resposta inválida! Digite s ou n.")
                        continue

                    presenca = resposta == "s"

                    resultado = casa.simular_presenca(
                        id_disp, presenca
                    )

                    print(resultado)

                except Exception as e:
                    print(f"Erro: {e}")

        elif opcao == "8":
            id_disp = selecionar_dispositivo(casa, SensorTemperatura)

            if id_disp is not None:
                try:
                    nova_temp = float(
                        input("Digite a nova temperatura: ")
                    )

                    casa.atualizar_sensor_temperatura(
                        id_disp, nova_temp
                    )

                    print(
                        f"Temperatura do sensor atualizada para {nova_temp}°C."
                    )

                except Exception as e:
                    print(f"Erro: {e}")

        elif opcao == "9":
            id_disp = selecionar_dispositivo(casa)

            if id_disp is not None:
                try:
                    dispositivo = casa.get_dispositivo(id_disp)

                    print("\nDetalhes do dispositivo:")
                    print(dispositivo)
                    print(dispositivo.testar_status())

                except Exception as e:
                    print(f"Erro: {e}")

        elif opcao == "0":
            print("Encerrando o sistema. Até logo!")
            break

        else:
            print("Opção inválida! Tente novamente.")


if __name__ == "__main__":
    main()
