# language: pt
Funcionalidade: Valor pendente da parcela (multa, juros e total)
  Como diretor financeiro do pós-venda
  Quero que multa, juros e total pendente sigam sempre a mesma conta
  Para que o saldo da carteira e a recuperação batam em todos os relatórios

  Regra: Multa de 2% sobre a parcela, fixa, arredondada em centavos

    Cenário: A multa não cresce com o atraso
      Dado uma parcela de R$ 100,00 com 90 dias de atraso
      Quando calculo os valores da pendência
      Então a multa é R$ 2,00

    Cenário: A parcela que vence hoje já tem multa (regra atual)
      Dado uma parcela de R$ 100,00 com 0 dias de atraso
      Quando calculo os valores da pendência
      Então a multa é R$ 2,00
      E os juros são R$ 0,00
      E o total pendente é R$ 102,00

  Regra: Juros de 1% ao mês, pró-rata em mês de 30 dias, arredondados em centavos

    Cenário: Um mês de atraso
      Dado uma parcela de R$ 100,00 com 30 dias de atraso
      Quando calculo os valores da pendência
      Então os juros são R$ 1,00
      E o total pendente é R$ 103,00

    Esquema do Cenário: Parcela, multa, juros e total
      Dado uma parcela de R$ <parcela> com <dias> dias de atraso
      Quando calculo os valores da pendência
      Então a multa é R$ <multa>
      E os juros são R$ <juros>
      E o total pendente é R$ <total>

      Exemplos: Valores de carteira
        | parcela  | dias | multa | juros | total    |
        | 150,00   | 10   | 3,00  | 0,50  | 153,50   |
        | 89,90    | 45   | 1,80  | 1,35  | 93,05    |
        | 33,33    | 1    | 0,67  | 0,01  | 34,01    |
        | 12,25    | 7    | 0,25  | 0,03  | 12,53    |
        | 1.234,56 | 61   | 24,69 | 25,10 | 1.284,35 |

  Regra: Parcela que ainda não venceu não tem juros nem total pendente

    Cenário: Vencimento no futuro
      Dado uma parcela de R$ 100,00 com -5 dias de atraso
      Quando calculo os valores da pendência
      Então os juros ficam sem valor
      E o total pendente fica sem valor

  Regra: Um total diferente da conta é inconsistente

    # Incidente I07 da simulação: o sistema de origem gravou o total com 10% a mais (bug no cálculo de juros).
    Cenário: Total gravado 10% acima da conta
      Dado uma parcela de R$ 100,00 com 30 dias de atraso
      E um total gravado de R$ 113,30
      Quando calculo os valores da pendência
      Então o total gravado não confere com a regra
