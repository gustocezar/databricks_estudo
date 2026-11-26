# Marca: cores, regras de uso e logo

> Fonte da marca da empresa para tudo o que o projeto mostra: painéis AI/BI, tema do Power BI, apresentações,
> gráficos e páginas. Regra do dono (26/11/2026): **antes de criar ou mudar qualquer coisa visual, procure aqui a
> marca e siga-a.** Ela vale para pessoas e para agentes ([AGENTS.md](../../AGENTS.md)).

## Situação em 26/11/2026: ainda não há marca

- **Neste repositório:** nenhum manual, paleta oficial ou logo. A busca por `marca`, `brand`, `logo`, `paleta`,
  imagens e temas só achou as paletas do próprio projeto.
- **Na conta do Claude:** nenhum sistema de design.
- **Nas apresentações:** nenhum sistema de design declarado.

Até a marca chegar, as cores do projeto ficam numa **fonte única**: [marca.json](marca.json), lida por
[marca.py](marca.py). Elas são **escolhas do projeto, não da empresa** (`"eh_marca_da_empresa": false`). Não use logo de
empresa real sem o arquivo oficial e não chame essas cores de "cores da marca".

### Fonte única (26/11/2026)

| O que | Valor | Por quê |
|---|---|---|
| Séries dos gráficos (8, ordem fixa) | claro `#2a78d6` `#eb6834` `#1baf7a` `#eda100` `#e87ba4` `#008300` `#6250d6` `#e34948`; escuro na mesma ordem, um degrau ajustado | paleta de referência da skill `dataviz`. O `validate_palette.js` passa em tudo nos fundos `#FFFFFF` e `#11171C` |
| Estado (só com ícone ou rótulo) | bom `#0ca30c`, alerta `#fab219`, sério `#ec835a`, crítico `#d03b3b` | separado das séries; nunca vira "série 4" |
| Magnitude (mapa de calor) | azul, de `#cde2fb` a `#104281` | um tom, claro → escuro |
| Painéis | fundo `#F7F8FA` / `#1F272D`, cartão `#FFFFFF` / `#11171C`, texto `#11171C` / `#E8ECF0`, seleção `#2272B4` / `#8ACAFF` | escolhas do projeto desde 20/11 |
| Apresentações | os 14 tokens de `apresentacao` (azul-marinho `#14213D`, terracota `#A94A14`, azul `#2F6690`, cinza `#9AA3AE`…) | o bloco `:root` do `deck.css` sai de `marca.py css_apresentacao()` |
| Tipografia | Space Grotesk (título) e Inter (corpo) | as das apresentações |

**Quem lê a fonte única:**
- `paineis_financeiros/gerar_paineis.py`, `dqx_studio/painel/gerar_painel.py`, `sustentacao/gerar_sustentacao.py` (tema
  dos 4 painéis AI/BI);
- `paineis_financeiros/powerbi/gerar_powerbi.py` (tema do Power BI, com as cores de sentimento);
- as 2 apresentações, pelo `deck.css`.

Nenhum desses arquivos tem código de cor próprio. A única cor fora da fonte é o ícone do domínio no Discover
(`governanca/ontologia.py`), porque o Unity Catalog pode aceitar só uma lista fixa de cores.

**Por que trocamos a paleta (L97).** Antes eram 5 paletas em 6 lugares. A dos painéis e do Power BI reprovou no
validador: roxo e azul vizinhos tinham ΔE 1,2 para daltônicos, e o mínimo é 8. A da sustentação também reprovou. A
de referência passa em tudo. Ela tem só um aviso: 3 cores ficam abaixo de 3:1 no branco, o que exige legenda ou
rótulo visível, e os painéis já têm os dois.

## O que pedir à área de marca

Coloque os arquivos nesta pasta e preencha `marca.json` (modelo abaixo):

1. **Logo oficial:**
   - versões em SVG para fundo claro e escuro;
   - área de proteção, tamanho mínimo e usos proibidos.
2. **Paleta:**
   - primárias, secundárias e neutras em hexadecimal;
   - cores de status (sucesso, atenção, erro);
   - cores proibidas ou restritas.
3. **Regras para dados:**
   - ordem das cores das séries nos gráficos;
   - cor de valor negativo e de destaque;
   - contraste mínimo (acessibilidade);
   - modo escuro.
4. **Tipografia:** famílias e pesos para título e corpo, e o que usar quando a fonte não estiver disponível (painel AI/BI
   e Power BI têm fontes limitadas).
5. **Modelos:** apresentação e relatório oficiais, se existirem.

```json
{
  "fonte": "manual da marca, versão e data",
  "logo": {"claro": "logo_fundo_claro.svg", "escuro": "logo_fundo_escuro.svg"},
  "cores": {"primaria": "#......", "secundaria": "#......", "neutras": ["#......"],
            "status": {"sucesso": "#......", "atencao": "#......", "erro": "#......"}},
  "series": ["#......", "#......"],
  "fundo": {"claro": "#......", "escuro": "#......"},
  "texto": {"claro": "#......", "escuro": "#......"},
  "tipografia": {"titulo": "...", "corpo": "..."}
}
```

## Quando a marca chegar

1. Troque os valores de `marca.json` pelos do manual. Mude `"eh_marca_da_empresa"` para `true`, preencha `"fonte"`
   (manual e versão) e `"logo"`.
2. Valide a paleta de séries antes de usar:
   `node <skill dataviz>/scripts/validate_palette.js "<cores>" --mode light --surface "#FFFFFF"` e o mesmo no
   escuro. Cor da marca que reprova vira cor de destaque, não de série.
3. Regere os painéis (`gerar_paineis.py`, `gerar_painel.py`, `gerar_sustentacao.py gerar`) e o Power BI
   (`gerar_powerbi.py`). Faça o deploy dos bundles e confira cada página.
4. Nas apresentações, troque o `:root` do `deck.css` por `python3 -c "import marca; print(marca.css_apresentacao())"`
   e ponha a logo na capa.
4. Para apresentações e designs no Claude, crie um sistema de design a partir da marca, para que todo artefato novo já
   nasça nela.
5. Registre no CHANGELOG a fonte (manual e versão) e a conferência.
