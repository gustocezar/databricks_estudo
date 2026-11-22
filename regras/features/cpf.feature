# language: pt
Funcionalidade: CPF válido
  Como responsável pela qualidade do cadastro de clientes
  Quero saber se o CPF informado é válido
  Para avisar o cadastro e não usar um documento errado na cobrança

  # Números fictícios, usados só para teste.

  Regra: CPF válido tem 11 dígitos e os dois dígitos verificadores conferem

    Cenário: CPF com pontuação
      Dado o CPF "123.456.789-09"
      Quando verifico o CPF
      Então o CPF é válido

    Cenário: O mesmo CPF sem pontuação
      Dado o CPF "12345678909"
      Quando verifico o CPF
      Então o CPF é válido

    # Incidente I01 da simulação: último dígito trocado na origem.
    Cenário: Último dígito trocado
      Dado o CPF "123.456.789-08"
      Quando verifico o CPF
      Então o CPF é inválido

    Esquema do Cenário: Documentos inválidos
      Dado o CPF "<cpf>"
      Quando verifico o CPF
      Então o CPF é inválido

      Exemplos: Erros de digitação e de formato
        | cpf             | motivo                        |
        | 123.456.789-19  | primeiro dígito verificador   |
        | 1234567890      | só 10 dígitos                 |
        | 123456789091    | 12 dígitos                    |
        | 123.456.789-0X  | letra no lugar de dígito      |

    Cenário: Outro CPF válido
      Dado o CPF "987.654.321-00"
      Quando verifico o CPF
      Então o CPF é válido

  Regra: Dígitos todos iguais não formam CPF, mesmo passando no cálculo

    Esquema do Cenário: Sequências repetidas
      Dado o CPF "<cpf>"
      Quando verifico o CPF
      Então o CPF é inválido

      Exemplos:
        | cpf            |
        | 111.111.111-11 |
        | 000.000.000-00 |

  Regra: Sem CPF não há CPF válido

    Cenário: CPF não informado
      Dado um CPF não informado
      Quando verifico o CPF
      Então o CPF é inválido

    Cenário: CPF em branco
      Dado o CPF ""
      Quando verifico o CPF
      Então o CPF é inválido
