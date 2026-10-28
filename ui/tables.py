"""
Pórtica App - Conteudo das tabelas NBR usadas nos dialogs de informacao.
"""

# Tabela 6.1 - NBR 6118 - Classes de agressividade ambiental
TABELA_CAA = {
    "titulo": "Tabela 6.1 - Classes de agressividade ambiental (CAA)",
    "fonte":  "NBR 6118:2023, item 6.4.2 (tabela 6.1)",
    "cabecalho": ["CAA", "Agressividade", "Classificacao geral", "Risco"],
    "linhas": [
        ["I",   "Fraca",        "Rural / Submersa",        "Insignificante"],
        ["II",  "Moderada",     "Urbana (a,b)",            "Pequeno"],
        ["III", "Forte",        "Marinha (a) / Industrial (a,b)",  "Grande"],
        ["IV",  "Muito forte",  "Industrial (a,c) / Respingos de mar", "Elevado"],
    ],
    "notas": [
        "(a) Pode-se admitir uma classe mais branda (uma classe acima) para ambientes internos secos (salas, dormitorios, banheiros, cozinhas) ou com concreto revestido com argamassa e pintura.",
        "(b) Pode-se admitir uma classe mais branda (uma classe acima) em obras de clima seco, com umidade relativa do ar menor ou igual a 65%, com estruturas protegidas de chuva.",
        "(c) Ambientes quimicamente agressivos, tanques industriais, galvanoplastia, branqueamento em industrias de celulose e papel, armazens de fertilizantes, industrias quimicas.",
    ],
}

# Tabela 7.2 - Cobrimento nominal conforme CAA
TABELA_COBRIMENTO = {
    "titulo": "Cobrimento nominal minimo (mm) - Concreto armado",
    "fonte":  "NBR 6118:2023, tabela 7.2",
    "imagem": "viga_retangular_secao.png",
    "cabecalho": ["Componente", "CAA I", "CAA II", "CAA III", "CAA IV"],
    "linhas": [
        ["Laje",            "25", "30", "40", "50"],
        ["Viga / Pilar",    "25", "30", "40", "50"],
    ],
    "notas": [
        "Cobrimento nominal = cobrimento minimo + tolerancia de execucao (10 mm).",
        "Para controle rigoroso de execucao (fck >= 40 MPa, relacao agua/cimento controlada), o cobrimento pode ser reduzido em 5 mm.",
    ],
}

# Tabela 17.3 - rho_min para armaduras de flexao
TABELA_RHO_MIN = {
    "titulo": "Taxas minimas de armadura de flexao (rho_min, %)",
    "fonte":  "NBR 6118:2023, item 17.3.5.2.1",
    "cabecalho": ["Forma da secao", "rho_min"],
    "linhas": [
        ["Retangular",     "0,150 (fck <= 35 MPa)  |  0,209 (fck = 50 MPa)"],
        ["T (mesa comprimida)", "0,150 (fck <= 35 MPa)"],
    ],
    "notas": [
        "A taxa minima pode ser reduzida em 0,10% quando a armadura dupla for utilizada.",
    ],
}

# Tabela de diametros de barras
TABELA_DIAMETROS = {
    "titulo": "Diametros nominais de barras (CA-25, CA-50, CA-60)",
    "fonte":  "NBR 7480",
    "imagem": "partes_armadura_viga.png",
    "cabecalho": ["phi (mm)", "Area unitaria (cm2)", "Massa linear (kg/m)"],
    "linhas": [
        ["5,0",   "0,196",  "0,154"],
        ["6,3",   "0,312",  "0,245"],
        ["8,0",   "0,503",  "0,395"],
        ["10,0",  "0,785",  "0,617"],
        ["12,5",  "1,227",  "0,963"],
        ["16,0",  "2,011",  "1,578"],
        ["20,0",  "3,142",  "2,466"],
        ["25,0",  "4,909",  "3,853"],
        ["32,0",  "8,042",  "6,313"],
    ],
    "notas": [
        "Diametros padronizados pela NBR 7480. Valores de massa para aco CA-50.",
    ],
}

# Tabela 8.2 - Classes de concreto (NBR 6118)
TABELA_FCK = {
    "titulo": "Classes de concreto (NBR 6118)",
    "fonte":  "NBR 6118:2023, tabela 8.2",
    "cabecalho": ["Classe", "fck (MPa)", "fctm (MPa)", "Eci (GPa)"],
    "linhas": [
        ["C20", "20", "2,2", "25,0"],
        ["C25", "25", "2,6", "28,0"],
        ["C30", "30", "2,9", "30,7"],
        ["C35", "35", "3,2", "33,1"],
        ["C40", "40", "3,5", "35,4"],
        ["C45", "45", "3,8", "37,6"],
        ["C50", "50", "4,1", "39,6"],
        ["C55", "55", "4,2", "41,5"],
        ["C60", "60", "4,4", "43,4"],
    ],
    "notas": [
        "fctm = 0,30 . fck^(2/3) para concretos de agregados basalticos/graniticos.",
        "Eci = 5600 . raiz(fck) (MPa) para concretos com agregados de quartzito.",
        "Para CAA III, fck minimo = 30 MPa; CAA IV, fck minimo = 35 MPa.",
    ],
}

# Classes de aco para armaduras (NBR 7480 / NBR 6118)
TABELA_ACO = {
    "titulo": "Classes de aco para armaduras (NBR 7480)",
    "fonte":  "NBR 7480 / NBR 6118:2023, item 7.2",
    "imagem": "partes_armadura_viga.png",
    "cabecalho": ["Classe", "fyk (MPa)", "Aplicacao tipica"],
    "linhas": [
        ["CA-25", "250", "Barras lisas/grossas (pouco usado)"],
        ["CA-50", "500", "Barras estriadas (mais comum, phi 5 a 32 mm)"],
        ["CA-60", "600", "Fios para estribos e telas (phi 5 a 10 mm)"],
    ],
    "notas": [
        "gamma_s = 1,15 (estados-limites ultimos).",
        "fyd = fyk / gamma_s.",
        "Estribos geralmente em CA-60 (fios) ou CA-50 (barras finas).",
        "Barras longitudinais geralmente em CA-50.",
    ],
}

# Tabela 11.1 - NBR 6118 - Coeficientes γf (simplificação por combinação)
TABELA_GAMMA_F = {
    "titulo": "Tabela 11.1 - Coeficientes de ponderacao das acoes (gf)",
    "fonte":  "NBR 6118:2023, tabela 11.1",
    "cabecalho": ["Combinacao", "gf (acoes variaveis)", "Uso tipico"],
    "linhas": [
        ["Normais",                     "1,4", "Situacoes de uso permanente"],
        ["Especiais ou de construcao",  "1,2", "Acoes durante execucao / especiais"],
        ["Excepcionais",                "1,0", "Acoes excepcionais (incendio, impacto)"],
    ],
    "notas": [
        "Simplificacao: o app aplica um unico gf por combinacao sobre os esforcos "
        "caracteristicos (sem majorar) informados na entrada.",
        "Tabela completa (por tipo de acao g, q, p, recalque) na NBR 6118:2023, tabela 11.1.",
        "Para cargas permanentes de pequena variabilidade (pre-moldados), gf pode ser "
        "reduzido para 1,3 em combinacoes normais.",
    ],
}

# ── Conteudo textual explicativo (nao-tabular) ──────────────────────────────

INFO_GEOMETRIA = {
    "titulo": "Geometria da secao transversal",
    "fonte":  "NBR 6118:2023, secao 6.2 / 17.2",
    "imagem": "viga_retangular_secao.png",
    "secoes": [
        {
            "titulo": "Altura h (cm)",
            "texto": "Altura total da secao da viga, incluindo a mesa se houver. "
                     "Para viga retangular, e a dimensao vertical da secao.",
        },
        {
            "titulo": "Largura bw (cm)",
            "texto": "Largura da alma (nervo) da viga. E a dimensao horizontal da secao "
                     "retangular, ou a largura da nerva em viga T.",
        },
        {
            "titulo": "Altura util d (cm)",
            "texto": "d = h - d', onde d' = cobrimento + phi_estribo + phi_barra/2. "
                     "E a distancia do bordo tracionado ao centro da armadura de tracao. "
                     "Usada em todos os calculos de flexao (KC, bx, As).",
        },
        {
            "titulo": "Cobrimento",
            "texto": "Definido pela CAA (Classe de Agressividade Ambiental). "
                     "Veja a tabela de cobrimento para valores por classe.",
        },
    ],
}

INFO_VIGA_T = {
    "titulo": "Viga T - Mesa colaborante",
    "fonte":  "NBR 6118:2023, secao 15.5.2",
    "imagem": "viga_t_secao.png",
    "secoes": [
        {
            "titulo": "Largura da mesa bf (cm)",
            "texto": "Largura total da mesa (nervura + abas). E a largura geometrica "
                     "da laje/flange que compoe a secao T.",
        },
        {
            "titulo": "Altura da mesa hf (cm)",
            "texto": "Espessura da mesa (geralmente igual a espessura da laje adjacente). "
                     "Para haver mesa colaborante, a linha neutra deve ficar dentro da mesa.",
        },
        {
            "titulo": "Mesa colaborante",
            "texto": "A mesa colabora na compressao quando 0,8 . x <= hf (linha neutra "
                     "dentro da flange). Se 0,8 . x > hf, a secao comporta-se como T "
                     "verdadeiro e o calculo considera a alma na compressao.",
        },
    ],
}

INFO_B1 = {
    "titulo": "Largura efetiva da mesa (bf,ef)",
    "fonte":  "NBR 6118:2023, item 15.5.2",
    "imagem": "viga_t_secao.png",
    "secoes": [
        {
            "titulo": "b1 esquerdo e b1 direito (cm)",
            "texto": "Cada b1 e a projecao da mesa para fora da alma, de cada lado. "
                     "Definem a contribuicao das abas laterais na largura efetiva.",
        },
        {
            "titulo": "Calculo do bf,ef",
            "texto": "bf,ef = bw + b1esq + b1dir, limitado a largura total bf. "
                     "No app: bf,ef = min(bf, bw + b1esq + b1dir).",
        },
        {
            "titulo": "Limites normativos",
            "texto": "Para vaos isolados: b1 <= 0,10 . a (a = vao entre apoios) e "
                     "b1 <= 0,5 . bf_adj (largura da mesa adjacente do outro lado). "
                     "O app aplica a simplificacao bf,ef = min(bf, bw + b1esq + b1dir).",
        },
    ],
}
