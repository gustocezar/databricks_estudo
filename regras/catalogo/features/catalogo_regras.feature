# language: pt
# Fora do portão da carga de propósito: o catálogo é governança e não pode parar a carga diária.
# Rode com: cd regras && .venv/bin/behave catalogo/features
Funcionalidade: Catálogo de regras com versão e vigência
  Como dono das regras de qualidade do pós-venda
  Quero que cada regra tenha uma única versão valendo em cada dia do dado
  Para que o evento de cada dia seja julgado pela regra que valia naquele dia

  Regra: Cada dia do dado tem exatamente uma versão aprovada de cada regra

    Cenário: Nenhum dia sem regra e nenhum dia com duas versões
      Quando confiro as versões vigentes em todos os dias da base
      Então nenhum dia fica sem versão ou com duas versões da mesma regra

  Regra: A versão vigente sai da data do dado, não da data da execução

    Esquema do Cenário: Versão vigente por data do dado
      Quando consulto a versão vigente da regra "<regra>" no dia <dia>
      Então a versão é <versao>

      Exemplos: Regras de produção (todas na versão 1 em 26/11/2026)
        | regra                         | dia        | versao |
        | uf_invalida                   | 2026-06-01 | 1      |
        | valores_fora_da_regra         | 2026-12-24 | 1      |
        | periodicidade_fora_do_dominio | 2027-01-08 | 1      |

    Cenário: Regra que não está no catálogo não tem versão
      Quando consulto a versão vigente da regra "regra_inexistente" no dia 2026-06-01
      Então a regra não tem versão nesse dia

  Regra: Toda falha da barreira pertence a uma regra de erro do catálogo

    Cenário: Os motivos da quarentena estão no catálogo
      Quando listo os motivos de rejeição da quarentena
      Então todos são regras de erro do catálogo

  Regra: Versão aprovada tem dono da decisão, e versão nova tem motivo

    Cenário: Versões aprovadas completas
      Quando confiro as versões aprovadas do catálogo
      Então toda versão aprovada tem quem aprovou e quando
      E toda versão depois da primeira tem motivo e origem

  Regra: A triagem só aceita as quatro classificações combinadas

    Cenário: Classificação fora do combinado é recusada
      Quando tento registrar uma triagem com a classificação "achismo"
      Então o registro é recusado pela tabela
