# Mapa do Código: Pórtica App

> Atualizado em 11/11/2026 (EP-04). Referência rápida de arquitetura, módulos e convenções.
> Útil para onboarding de desenvolvedores e agentes de IA que trabalham no código.

---

## 1. Estrutura de Pastas

```
portica_app/
├── core/                          # Motor compartilhado (edição única)
│   ├── calculos/
│   │   ├── secao.py               # FONTE ÚNICA: BeamModel, d, cobrimento e materiais (EP-04.1)
│   │   └── engenharia.py          # Motor NBR 6118 (flexão, cisalhamento, pele)
│   ├── detailing/
│   │   ├── domain.py              # Engine geométrica (BeamDetailer, posicionar_armadura_pele)
│   │   ├── presentation.py        # Pipeline de desenho único (BeamSectionCommands, Flet, fpdf2)
│   │   └── dxf_export.py          # Exportação DXF (AutoCAD R2010 via BeamDetailer)
│   ├── relatorio_base.py          # Relatórios em PDF (desenhos via BeamDetailer, armadura As')
│   ├── utils_tempfile.py          # Utilitários de arquivo temporário
│   ├── version.py                 # Versão do app
│   └── assets/                    # Imagens, ícones, logos
├── ui/                            # Interface gráfica Flet
│   ├── viga/                      # Arquitetura modular de viga (EP-04.3, ~4.440 linhas divididas)
│   │   ├── state.py               # VigaState tipado e ViewContext
│   │   ├── form_geometry.py       # Geometria da seção (h, bw, bf, hf, b1esq, b1dir)
│   │   ├── form_materials.py      # Materiais (fck, fyk, CAA, γf)
│   │   ├── form_trechos.py        # Trechos manuais e esforços
│   │   ├── panel_ftool.py         # Painel FTOOL (arquivos, combinações, envelope)
│   │   ├── ftool_processing.py    # Processamento e dimensionamento FTOOL
│   │   ├── actions.py             # Ações do usuário (salvar/carregar .ptc, calcular, PDF, DXF)
│   │   ├── results_view.py        # Visualização de armaduras e verificações
│   │   └── viga.py                # Orquestração da tela e composição de contexto
│   ├── home.py                    # Tela inicial (cards de modo, projetos recentes)
│   ├── sidebar.py                 # Navegação lateral
│   ├── sobre.py                   # Tela "Sobre"
│   ├── dialogs.py                 # Diálogos informativos
│   ├── theme.py                   # Design system (paleta, tipografia, espaçamento)
│   ├── tables.py                  # Componentes de tabelas reutilizáveis
│   ├── recent_projects.py         # Gerenciamento de projetos recentes (.ptc)
│   ├── entrada.py                 # Entrada unificada (.ptc / FTOOL TXT)
│   └── ftool/                     # Módulos matemáticos FTOOL
│       ├── parser.py              # Leitor de arquivos TXT de esforços
│       ├── secoes_criticas.py     # Detecção de picos e vales
│       ├── dimensionamento.py     # Dimensionamento automático
│       ├── diagrama.py            # Diagramação de esforços M(x) e V(x)
│       ├── envelope.py            # Envoltória de combinações
│       ├── detailing.py           # Detalhamento de estribos por região
│       └── els.py                 # ELS (flecha + fissuração via BeamModel)
├── edicoes/
│   └── main.py                    # Entry point único da aplicação
├── build/
│   ├── build_portica.py           # Build único PyInstaller
│   ├── launcher.py                # Bootstrap congelado
│   └── flet_bootstrap.py          # Setup do cliente Flet
├── tests/                         # Suíte de testes (407 testes)
│   ├── benchmarks/                # Benchmarks normativos calculados à mão
│   └── test_*.py                  # Testes unitários e de integração
└── samples/                       # Arquivos de exemplo (FTOOL TXT, SVG)
```

---

## 2. core/calculos/secao.py: Fonte Única de Verdade (EP-04.1)

Criado para eliminar duplicação de geometria, cobrimento e altura útil $d$.

### Entidades e Funções Principais

| Entidade / Função | Responsabilidade |
|-------------------|------------------|
| `BeamModel` | Dataclass imutável representando a seção transversal completa (`h, bw, bf, hf, caa, fck_mpa, fyk_kn_cm2, diam_estribo_mm, diam_barra_mm`). |
| `BeamModel.cob_mm` | Cobrimento nominal derivado de CAA (NBR 6118 Tabela 7.2). |
| `BeamModel.d_cm` | Altura útil $d = h - d'$ rigorosa e invariante. |
| `BeamModel.fcd_mpa`, `fctm_mpa`, `fctd_kn_cm2` | Propriedades mecânicas do concreto calculadas centralmente. |
| `BeamModel.Ecs_mpa` | Módulo de deformação tangente/secante do concreto. |
| `BeamModel.alpha_c`, `lambda_val` | Coeficientes do bloco retangular de tensões da NBR 6118. |
| `altura_util_cm(...)` | Única função para obter $d$ em todo o repositório ($d = h - d'$). |
| `d_linha_cm(...)` | Estimativa padronizada do centro de gravidade da armadura: $c_{nom} + \phi_e + \phi/2$. |

---

## 3. core/detailing/: Consolidação do Desenho (EP-04.4 & EP-04.5)

`BeamDetailer` e `BeamSectionCommands` são a **única fonte de geometria de armação** do sistema. Todas as 4 saídas consomem as mesmas coordenadas:

1. **Relatório PDF Retangular** (`core/relatorio_base.py:desenhar_secao_retangular`)
2. **Relatório PDF T** (`core/relatorio_base.py:desenhar_secao_t`)
3. **Flet Canvas UI** (`core/detailing/presentation.py:FletCanvasRenderer`)
4. **Exportação DXF** (`core/detailing/dxf_export.py:exportar_secao_dxf`)

### Unificações Implementadas
- **Armadura de Pele (`posicionar_armadura_pele`)**: Função matemática única em `core/detailing/domain.py` que calcula as cotas Y simétricas em ambas as faces laterais.
- **Grampos Suplementares**: Geometria padronizada em polilinha de 6 vértices com ganchos a 135° nas extremidades.
- **Viga T**: Armadura superior tracionada/comprimida distribuída corretamente na largura total da mesa ($b_f$), e não na alma.
- **Armadura de Compressão ($As' > 0$)**: Desenhada no topo em momentos positivos de armadura dupla e identificada explicitamente na legenda (`Barras Superiores (As')`).

---

## 4. ui/viga/: Arquitetura Modular (EP-04.3)

O antigo arquivo monolítico `ui/viga.py` (~4.440 linhas) foi decomposto no pacote modular `ui/viga/`:

| Módulo | Responsabilidade |
|--------|------------------|
| `state.py` | `VigaState` tipado e `ViewContext` contendo todas as referências de controles. Sem closures mutáveis globais. Testável sem Flet ativo. |
| `form_geometry.py` | Campos de entrada e validações da geometria de seção (retangular e T). |
| `form_materials.py` | Parâmetros de materiais (concreto fck, aço CA-50/60, cobrimento por classe de agressividade ambiental). |
| `form_trechos.py` | Gerenciamento dinâmico de trechos de cálculo manual com tabelas de esforços. |
| `panel_ftool.py` | Painel colapsável de integração com o FTOOL: drag & drop de arquivos, lista de combinações e envelope. |
| `ftool_processing.py` | Motor de importação, detecção de seções críticas, dimensionamento e diálogo modal de ELS. |
| `actions.py` | Tratamento de eventos de alto nível: cálculo, persistência de arquivos `.ptc`, geração de relatórios PDF e DXF. |
| `results_view.py` | Renderização visual dos resultados de flexão e cisalhamento, com chips de status normativo. |
| `viga.py` | Ponto de entrada leve: orquestra a montagem do layout e a ligação entre os componentes. |

---

## 5. Tratamento de Exceções e Resiliência (EP-04.6)

- Todos os blocos genéricos `except Exception` na interface foram substituídos por capturas de exceções específicas (`json.JSONDecodeError`, `OSError`, `ValueError`, `KeyError`, `RuntimeError`).
- Erros são registrados com traceback via `logging.getLogger(__name__)` e exibidos de forma visível ao usuário através de snacks e toasts contextuais.
- O sentinela numérico de cálculo (`bx = 999.0` / `x = 999.0 * d`) foi encapsulado na constante privada `_SENTINELA_BX` em `core/calculos/engenharia.py`, sendo convertido deterministicamente para `None` na interface pública.

---

## 6. Suíte de Testes Automatizados

O projeto conta com **407 testes automatizados** passando integralmente (incluindo benchmarks normativos calculados à mão):

| Arquivo de Teste | Qtd Testes |
|-------------------|------------|
| `tests/test_detailing_domain.py` | 40 |
| `tests/test_viga_modulos.py` | 20 |
| `tests/test_entrada_ftool.py` | 19 |
| `tests/test_conversao.py` | 17 |
| `tests/test_engenharia.py` | 17 |
| `tests/test_els_contorno.py` | 16 |
| `tests/test_grampos.py` | 15 |
| `tests/test_parser_ftool.py` | 14 |
| `tests/benchmarks/test_bench_materiais.py` | 13 |
| `tests/test_cisalhamento.py` | 13 |
| `tests/test_secoes_criticas.py` | 13 |
| `tests/benchmarks/test_bench_cisalhamento.py` | 12 |
| `tests/test_els.py` | 12 |
| `tests/test_flexao_t.py` | 11 |
| `tests/benchmarks/test_bench_flexao.py` | 10 |
| `tests/test_integridade_flexao.py` | 10 |
| `tests/test_pele.py` | 10 |
| `tests/test_ajustes_els.py` | 9 |
| `tests/test_convergencia_flexao.py` | 9 |
| `tests/test_fluxo_desenho.py` | 9 |
| `tests/benchmarks/test_bench_pele.py` | 8 |
| `tests/test_beam_model.py` | 8 |
| `tests/benchmarks/test_bench_fissuracao.py` | 7 |
| `tests/test_armadura_dupla.py` | 7 |
| `tests/test_dimensionamento_fluxo.py` | 7 |
| `tests/test_dominio.py` | 7 |
| `tests/test_guardas_entrada.py` | 7 |
| `tests/benchmarks/test_bench_viga_t.py` | 6 |
| `tests/test_detailing.py` | 6 |
| `tests/test_dimensionamento.py` | 6 |
| `tests/test_envelope.py` | 6 |
| `tests/benchmarks/test_bench_els.py` | 5 |
| `tests/test_dxf.py` | 5 |
| `tests/test_relatorio.py` | 5 |
| `tests/test_ajustes_barras_extras.py` | 4 |
| `tests/test_armadura_pele_correcoes.py` | 4 |
| `tests/test_diagrama.py` | 4 |
| `tests/test_equivalencia_desenho.py` | 4 |
| `tests/test_fluxo_envelope.py` | 3 |
| `tests/test_relatorio_ep019.py` | 3 |
| `tests/test_flecha_diametro.py` | 2 |
| `tests/test_integridade_pdf.py` | 2 |
| `tests/test_serialization.py` | 2 |
