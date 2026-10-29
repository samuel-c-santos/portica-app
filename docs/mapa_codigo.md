# Mapa do Código: Pórtica App

> Atualizado em 04/08/2026. Referência rápida de arquivos, funções e classes.
> Útil para onboarding de desenvolvedores e IAs que trabalham no código.

---

## 1. Estrutura de Pastas

```
portica_app/
├── core/                          # Motor compartilhado (Standard + Premium)
│   ├── calculos/
│   │   └── engenharia.py          # Motor NBR 6118 (flexão, cisalhamento, pele)
│   ├── detailing/
│   │   ├── domain.py              # Engine geométrica (BeamDetailer, camadas)
│   │   ├── presentation.py        # Painter + renderers (Flet, fpdf2)
│   │   └── dxf_export.py          # Exportação DXF (AutoCAD R2010)
│   ├── relatorio_base.py          # PDF compartilhado (seções, legendas, relatórios)
│   ├── utils_tempfile.py          # Utilitários de arquivo temporário
│   ├── version.py                 # Versão do app
│   └── assets/                    # Imagens, ícones, logos
├── ui/                             # UI unificada (inserção manual + FTOOL)
│   ├── viga.py                     # Tela principal da viga (com FTOOL)
│   ├── home.py                     # Tela inicial (cards, projetos recentes)
│   ├── sidebar.py                  # Navegação lateral
│   ├── sobre.py                    # Tela "Sobre"
│   ├── dialogs.py                  # Diários informativos (tabelas, imagens)
│   ├── theme.py                    # Design system (cores, tipografia, componentes)
│   ├── tables.py                   # Tabelas reutilizáveis
│   ├── recent_projects.py          # Gerenciamento de projetos recentes (.ptc)
│   ├── entrada.py                  # Entrada unificada (.ptc / FTOOL TXT)
│   └── ftool/                      # Módulos FTOOL
│       ├── parser.py          # Parser de arquivos TXT do FTOOL
│       ├── secoes_criticas.py # Detecção de seções críticas
│       ├── dimensionamento.py # Dimensionamento automático
│       ├── diagrama.py        # Diagrama M(x)/V(x)
│       ├── envelope.py        # Envelope de combinações
│       ├── detailing.py       # Detalhamento de estribos por região
│       └── els.py             # ELS (flecha + fissuração)
├── edicoes/
│   └── main.py                     # Entry point único
├── build/
│   ├── build_portica.py           # Build unico (PyInstaller onefile/windowed)
│   ├── launcher.py                # Bootstrap congelado (SSL/certifi + Flet)
│   └── flet_bootstrap.py          # 1a execucao: baixa o cliente Flet (com progresso)
├── tests/                         # 220 testes automatizados
└── samples/                       # Arquivos de exemplo (FTOOL TXT, SVG)
```

---

## 2. core/calculos/engenharia.py: Motor NBR 6118

### Funções auxiliares

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `lambda_f(fck_mpa)` | 21 | Fator λ (0.80 p/ fck≤50, 1-fck/250 p/ fck>50) |
| `area_barra(d_mm)` | 75 | Área de uma barra (π·d²/4) |
| `fcd_mpa(fck)` | 80 | Resistência de cálculo à compressão |
| `fyd_kn_cm2(fyk)` | 84 | Tensão de escoamento de cálculo |
| `fctm_mpa(fck)` | 93 | Resistência média à tração |
| `fck_to_kgf_cm2(fck_mpa)` | 97 | Conversão MPa → kgf/cm² |
| `fctkinf_mpa(fck)` | 102 | fctk,inf (resistência característica inferior) |
| `fctd_kn_cm2(fck)` | 106 | Resistência de cálculo à tração |
| `validar_geometria(...)` | 110 | Valida h, bw, d, cob, etc. |
| `rho_min(fck)` | 152 | Taxa mínima de armadura |
| `asw_min_cm2_m(fck, bw, fyk)` | 159 | Armadura transversal mínima |
| `calcular_armadura_pele(h, bw, fck, aço)` | 173 | Armadura de pele (NBR 6118:17.3.5.2.3) |

### Classes de resultado

| Classe | Linha | Campos principais |
|--------|-------|-------------------|
| `ResultadoFlexao` | 282 | `as_usado_cm2`, `qtd_barras`, `phi_barra_inf`, `camadas_adotadas`, `layout_convergido`, `pele_qtd`, `pele_phi` |
| `ResultadoBitola` | 337 | `phi_adotado`, `n_barras`, `as_calc`, `as_usado` |
| `ResultadoCisalhamento` | 787 | `asw_s_cm2m`, `phi_estribo`, `s_adotado_cm`, `passa_smax` |
| `ResultadoFlexaoT` | 926 | Herda `ResultadoFlexao` + `bf_efetivo_cm`, `hf_cm`, `ln_mesa` |

### Funções de cálculo

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `dimensionar_bitola_iterativa(...)` | 352 | Loop convergente de d (cobri + estripos + camadas) |
| `calcular_flexao_viga_comum(...)` | 521 | Flexão retangular completa (domínio, As, pele, cisalhamento) |
| `calcular_cisalhamento_viga_comum(...)` | 808 | Cisalhamento (Vsw, Asw/min, s_max, fywd) |
| `bf_efetivo_viga_t(...)` | 980 | Largura efetiva da mesa (vãos adjacentes) |
| `calcular_flexao_viga_t(...)` | 1008 | Flexão viga T (LN na mesa, bf efetivo) |

---

## 3. core/detailing/: Engine Geométrica de Seção

### domain.py: Lógica de posicionamento

| Classe | Linha | Responsabilidade |
|--------|-------|-----------------|
| `BarPosition` | 28 | Posição de uma barra (x, y, layer, phi_mm, is_corner_bar) |
| `ReinforcementLayer` | 53 | Uma camada (index, bar_count, y_centroid) |
| `SupplementaryStirrup` | 70 | Grampo suplementar (posição, raio) |
| `SectionLayoutData` | 82 | Resultado do layout (bar_positions, layers, layer_count, ev_min) |
| `BeamDetailingInput` | 152 | Input do detailer (bw, h, phi, cob, total_bars, is_t, bf, hf) |
| `BeamDetailer` | 171 | Distribui barras em camadas respeitando NBR 6118 (e_h, e_v) |

### presentation.py: Painter agnóstico + renderers

**Comandos (comandos de desenho independentes de renderer):**

| Classe | Linha | Responsabilidade |
|--------|-------|-----------------|
| `CmdRect` | 60 | Retângulo |
| `CmdCircle` | 69 | Círculo |
| `CmdLine` | 78 | Linha |
| `CmdPolyline` | 87 | Polilinha |
| `CmdArcPath` | 95 | Arco |
| `CmdText` | 107 | Texto |
| `CmdPolygon` | 117 | Polígono |

**Painter e renderers:**

| Classe/Função | Linha | Responsabilidade |
|---------------|-------|-----------------|
| `BeamSectionCommands` | 133 | Gera lista de comandos a partir de `SectionLayoutData` |
| `FletCanvasRenderer` | 488 | Renderiza comandos na UI (Flet Canvas) |
| `FpdfRenderer` | 654 | Renderiza comandos em PDF (fpdf2) |
| `desenhar_secao_com_detailer(...)` | 819 | Wrapper: detailer + painter + renderer para PDF |

### dxf_export.py: Exportação DXF

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `exportar_secao_dxf(...)` | 5 | Gera arquivo DXF (R2010) com seção retangular ou T |

---

## 4. core/relatorio_base.py: PDF Compartilhado

### Classes e funções auxiliares

| Classe/Função | Linha | Responsabilidade |
|---------------|-------|-----------------|
| `PorticaPDF(FPDF)` | 85 | Subclasse de FPDF com configurações do Pórtica |
| `_n(valor, casas)` | 63 | Formata número para exibição |
| `_diam(d_mm)` | 72 | Formata diâmetro (ex: "φ16") |
| `_caa_nome(caa)` | 77 | Nome do agressivo (I, II, III) |
| `_desenhar_grampos_segunda_camada(...)` | 950 | Desenha grampos suplementares no PDF |
| `_desenhar_nota_cavaletes(...)` | 1027 | Nota "cavaletes" quando há 2ª camada |
| `_split_layers(n, phi, bw, cob, estribo)` | 1064 | Divide barras em camadas (máx 2, fallback manual) |
| `_legenda_secao(...)` | 1425 | Legenda da seção (cores, símbolos) |
| `_converter_svg_para_png(svg_path)` | 1479 | Converte SVG → PNG para PDF |

### Funções de desenho de seção (4 funções independentes, atenção)

| Função | Linha | Gera | Usa layout_convergido? |
|--------|-------|------|------------------------|
| `desenhar_secao_retangular(...)` | 1099 | PDF (viga retangular) | Sim (opcional, fallback `_split_layers`) |
| `desenhar_secao_t(...)` | 1250 | PDF (viga T) | Sim (opcional, fallback `_split_layers`) |

> **Nota:** `desenhar_secao_com_detailer` (presentation.py:819) e `exportar_secao_dxf` (dxf_export.py:5)
> são as outras 2 funções de desenho. Total: 4 funções independentes com lógica própria de pele.
> Bug F6 (27/07/2026) aconteceu porque uma correção em 3 não cobriu a 4ª.

### Funções de relatório completo

| Função | Linha | Gera |
|--------|-------|------|
| `gerar_relatorio_viga_comum(...)` | 1516 | PDF completo (Standard, viga retangular) |
| `gerar_relatorio_viga_t(...)` | 1817 | PDF completo (Standard, viga T) |

---

## 5. ui/ftool/: Módulos FTOOL

### parser.py: Leitura de arquivos TXT

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `parse_momento(filepath)` | 66 | Lê arquivo de momento fletor (x, M) |
| `parse_cortante(filepath)` | 102 | Lê arquivo de cortante (x, V) |
| `parse_deformacao(filepath)` | 136 | Lê arquivo de deformação (x, δ, θ, κ) |
| `parse_tudo(pasta)` | 174 | Lê todos os arquivos de uma pasta |
| `validate_file_type(filepath, tipo)` | 215 | Valida tipo do arquivo (heurísticas) |

### secoes_criticas.py: Detecção de seções críticas

| Classe/Função | Linha | Responsabilidade |
|---------------|-------|-----------------|
| `SecaoCritica` | 11 | Seção crítica (x, momento, cortante, tipo, descricao) |
| `interpolar_y(curva, x)` | 20 | Interpola y em uma curva (x, y) |
| `detectar_maximos_locais(pontos)` | 54 | Detecta picos de momento (>=) |
| `detectar_minimos_locais(pontos)` | 81 | Detecta vales de momento |
| `detectar_apoios(momentos, cortantes)` | 108 | Detecta apoios por descontinuidade de V |
| `detectar_pontos_momento_nulo(pontos)` | 138 | Detecta M=0 (ponto de inflexão) |
| `calcular_lo_para_secao(...)` | 166 | Calcula l0 (vão teórico) a partir de M=0 |
| `detectar_todas_secoes(momentos, cortantes)` | 222 | Combina todas as detecções |

### dimensionamento.py: Dimensionamento automático

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `dimensionar_trechos_ftool(...)` | 16 | Dimensiona todas as seções críticas (flexão + ELS + pele) |
| `gerar_relatorio_premium(...)` | 230 | Texto do relatório Premium |
| `gerar_relatorio_viga_comum_premium(...)` | 281 | PDF Premium (viga retangular) |
| `gerar_relatorio_viga_t_premium(...)` | 434 | PDF Premium (viga T) |

### els.py: Estado Limite de Serviço

| Classe/Função | Linha | Responsabilidade |
|---------------|-------|-----------------|
| `AjustesELS` | 16 | Ajustes manuais (barras_extras, phi_minimo_mm, h_override_cm, fck_override_mpa) |
| `_e_modulus(fck)` | 82 | Módulo de elasticidade do concreto |
| `_propriedades_secao_t(...)` | 89 | Propriedades geométricas da seção T |
| `_momento_inercia_bruto_viga(...)` | 113 | Inércia bruta (Ig) |
| `_momento_fissuracao(...)` | 125 | Momento de fissuração (Mr) |
| `_estadio_ii_viga(...)` | 140 | Inércia do Estádio II (seção fissurada) |
| `_inercia_equivalente(...)` | 200 | Inércia equivalente (Ieq), por Branson |
| `calcular_flecha(...)` | 210 | Flecha imediata + diferida (integração numérica de κ) |
| `calcular_fissuracao(...)` | 360 | Abertura de fissuras (wk₁, wk₂) |
| `_sugerir_correcao_flecha(...)` | 481 | Sugestões quando flecha não passa |
| `_sugerir_correcao_fissuracao(...)` | 502 | Sugestões quando fissuração não passa |
| `gerar_relatorio_els(...)` | 519 | Texto do relatório ELS |

### diagrama.py: Diagrama de esforços

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `_desenhar_grafico(...)` | 11 | Desenha gráfico M(x) ou V(x) em fpdf2 |
| `gerar_diagrama_esforcos(...)` | 215 | Gera diagrama completo (M + V) no PDF |

### envelope.py: Envelope de combinações

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `calcular_envelope(combinacoes)` | 10 | Calcula envelope (máx M, máx V por seção) |
| `detectar_secoes_envelope(...)` | 79 | Detecta seções críticas do envelope |
| `gerar_relatorio_envelope(...)` | 199 | Gera relatório do envelope |

### detailing.py: Detalhamento de estribos

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `_calc_asw_s(vk, gamma_f, ...)` | 12 | Calcula Asw/s (armadura transversal) |
| `_calc_espacamento(asw_s, phi)` | 22 | Calcula espaçamento do estribo |
| `_encontrar_apoios(cortantes)` | 30 | Encontra posições de apoio |
| `detalhar_estribos(...)` | 39 | Detalha estribos por região (V(x) → espaçamento) |
| `calcular_qtd_estribos(regioes)` | 118 | Calcula quantidade de estribos por região |
| `gerar_tabela_detailing(regioes)` | 129 | Gera tabela de detalhamento em texto |

---

## 6. ui/: UI (componentes compartilhados)

### viga.py: Tela principal da viga

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `build_viga_screen(...)` | 213 | Constrói tela completa (geometria, trechos, cálculo, PDF, DXF) |

### home.py: Tela inicial

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `build_home(...)` | 301 | Cards de modo + projetos recentes |

### theme.py: Design system

| Classe | Linha | Responsabilidade |
|--------|-------|-----------------|
| `Palette` | 97 | Cores do tema (PRIMARY, SECONDARY, SURFACE, etc.) |
| `Type` | 134 | Tipografia (display, headline, title, body, label) |
| `Spacing` | 153 | Espaçamentos padrão |
| `Radius` | 165 | Border radius |

Funções de componente: `primary_button`, `tonal_button`, `outlined_button`, `success_button`, `surface_card`, `section_header`, `field`, `status_chip`, `icon_pill`.

### recent_projects.py: Projetos recentes

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `get_recent()` | 36 | Lista projetos recentes |
| `add_recent(path, modo)` | 47 | Adiciona projeto à lista |
| `remove_recent(path)` | 75 | Remove projeto da lista |

---

## 7. ui/: viga.py (tela principal com FTOOL)

### viga.py: Tela principal da viga (com FTOOL)

| Função | Linha | Responsabilidade |
|--------|-------|-----------------|
| `build_viga_screen(...)` | 221 | Constrói tela completa com FTOOL (parser, seções, dimensionamento, ELS, PDF, DXF) |

> A função `build_viga_screen` em ui/viga.py tem ~3200 linhas e orquestra
> todo o fluxo: parser → seções críticas → dimensionamento → ELS → diagrama → PDF/DXF.

---

## 8. Fluxos Principais

### Fluxo Standard (inserção manual)
```
viga.py:build_viga_screen
  → engenharia.py:calcular_flexao_viga_comum (ou calcular_flexao_viga_t)
  → engenharia.py:calcular_cisalhamento_viga_comum
  → engenharia.py:calcular_armadura_pele
  → relatorio_base.py:gerar_relatorio_viga_comum (ou gerar_relatorio_viga_t)
    → desenhar_secao_retangular (ou desenhar_secao_t)
  → dxf_export.py:exportar_secao_dxf
```

### Fluxo Premium (FTOOL)
```
viga.py:build_viga_screen
  → parser.py:parse_momento / parse_cortante / parse_deformacao
  → secoes_criticas.py:detectar_todas_secoes
  → dimensionamento.py:dimensionar_trechos_ftool
    → engenharia.py:calcular_flexao_viga_t (ou calcular_flexao_viga_comum)
    → detailing/domain.py:BeamDetailer.detail (layout de camadas)
    → els.py:calcular_flecha / calcular_fissuracao
  → diagrama.py:gerar_diagrama_esforcos
  → dimensionamento.py:gerar_relatorio_viga_t_premium (ou gerar_relatorio_viga_comum_premium)
    → relatorio_base.py:desenhar_secao_t (ou desenhar_secao_retangular)
  → dxf_export.py:exportar_secao_dxf
```

---

## 9. Atenção: Funções de Desenho de Seção (4 independentes)

Estas 4 funções desenham a seção transversal e cada uma tem lógica própria de posicionamento da armadura de pele. Qualquer correção visual deve ser aplicada nas 4:

| # | Função | Arquivo | Gera |
|---|--------|---------|------|
| 1 | `desenhar_secao_retangular` | `core/relatorio_base.py:1099` | PDF (viga retangular) |
| 2 | `desenhar_secao_t` | `core/relatorio_base.py:1250` | PDF (viga T) |
| 3 | `desenhar_secao_com_detailer` | `core/detailing/presentation.py:819` | PDF/FPDF (detailer) |
| 4 | `exportar_secao_dxf` | `core/detailing/dxf_export.py:5` | DXF (arquivo) |

---

## 10. Testes (201 testes)

| Arquivo | Qtd | Cobertura |
|---------|-----|-----------|
| `test_detailing_domain.py` | 35 | BeamDetailer, camadas, grampos, e_h, e_v |
| `test_engenharia.py` | 17 | Flexão retangular, domínio, γf, λf |
| `test_conversao.py` | 15 | fcd, fyd, fctm, γf table |
| `test_grampos.py` | 15 | Grampos suplementares |
| `test_parser_ftool.py` | 14 | Parser FTOOL TXT + validate_file_type |
| `test_els.py` | 12 | ELS flecha + fissuração + α Mr + fctm wk₁ + seção T |
| `test_secoes_criticas.py` | 10 | Detecção de seções críticas |
| `test_pele.py` | 9 | Armadura de pele, 6 diâmetros |
| `test_flexao_t.py` | 9 | Viga T, LN na mesa, bf efetivo |
| `test_ajustes_els.py` | 9 | Ajustes manuais ELS (AjustesELS) |
| `test_cisalhamento.py` | 9 | Majoração, Vsw, λf, fywd, s_max |
| `test_envelope.py` | 6 | Envelope de combinações |
| `test_dimensionamento.py` | 6 | Dimensionamento automático |
| `test_armadura_dupla.py` | 5 | Armadura de compressão |
| `test_detailing.py` | 5 | Detalhamento de estribos |
| `test_ajustes_barras_extras.py` | 4 | Recálculo de layout com barras extras |
| `test_convergencia_flexao.py` | 4 | Loop iterativo de d |
| `test_armadura_pele_correcoes.py` | 3 | Correções visuais da pele |
| `test_dxf.py` | 3 | Exportação DXF |
| `test_diagrama.py` | 3 | Diagrama M(x)/V(x) |
| `test_serialization.py` | 2 | .ptc JSON, recent projects |
| `test_flecha_diametro.py` | 2 | Flecha varia com φ |
| `test_relatorio.py` | 2 | Geração de PDF |
