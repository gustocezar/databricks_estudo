# language: pt
Funcionalidade: Faixa de atraso da parcela
  Como analista de cobrança do pós-venda
  Quero que toda parcela pendente caia em uma única faixa de atraso
  Para acompanhar a carteira por aging com os mesmos cortes em painéis, Genie e régua de cobrança

  Regra: A faixa depende só dos dias entre o vencimento e a data de referência

    Cenário: Parcela que vence hoje
      Dado uma parcela com 0 dias de atraso
      Quando calculo a faixa de atraso
      Então a faixa é "00_VENCE_HOJE"

    Cenário: Parcela com um mês de atraso fica na faixa de 16 a 30 dias
      Dado uma parcela com 30 dias de atraso
      Quando calculo a faixa de atraso
      Então a faixa é "02_16_A_30"

    Esquema do Cenário: Limites de cada faixa
      Dado uma parcela com <dias> dias de atraso
      Quando calculo a faixa de atraso
      Então a faixa é "<faixa>"

      Exemplos: Primeiro e último dia de cada faixa
        | dias | faixa         |
        | 1    | 01_1_A_15     |
        | 15   | 01_1_A_15     |
        | 16   | 02_16_A_30    |
        | 31   | 03_31_A_60    |
        | 60   | 03_31_A_60    |
        | 61   | 04_61_A_90    |
        | 90   | 04_61_A_90    |
        | 91   | 05_91_A_120   |
        | 120  | 05_91_A_120   |
        | 121  | 06_ACIMA_120  |
        | 365  | 06_ACIMA_120  |

  Regra: Parcela que ainda não venceu não tem faixa de atraso

    Cenário: Vencimento no futuro
      Dado uma parcela com -5 dias de atraso
      Quando calculo a faixa de atraso
      Então a parcela fica sem faixa
