"""
Gera imagens PNG das equacoes estruturais para uso no README.md.
As imagens sao renderizadas com matplotlib (mathtext) e salvas em
docs/equations/. O GitHub renderiza PNGs em arquivos .md.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "docs", "equations")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def render(tex: str, filename: str, fontsize: int = 18, color: str = "#212121",
           width: float = 9.0, height: float = 1.4):
    """Renderiza uma expressao LaTeX (mathtext) como PNG com fundo transparente."""
    fig = plt.figure(figsize=(width, height), dpi=200)
    fig.patch.set_alpha(0.0)
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.5, 0.5, tex, ha="center", va="center",
            fontsize=fontsize, color=color, usetex=False)
    out = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(out, dpi=200, bbox_inches="tight", pad_inches=0.08,
                transparent=True, facecolor="none")
    plt.close(fig)
    return out


# ── Flexao - Viga retangular ──────────────────────────────────────────────
render(r"$d \;=\; h - c - \phi_{t} - \dfrac{\phi_{l}}{2}$",
       "eq_d.png")

render(r"$KC \;=\; \dfrac{b_{w}\,d^{2}}{M_{d}}$",
       "eq_kc.png")

render(r"$-0{,}192\,\dfrac{f_{ck}}{10}\,KC\;\beta_{x}^{\,2} \;+\; 0{,}48\,\dfrac{f_{ck}}{10}\,KC\;\beta_{x} \;-\; 1 \;=\; 0$",
       "eq_2grau.png")

render(r"$\beta_{x,\min} \;=\; 0{,}45 \;\;(\text{se } f_{ck}<50\text{ MPa}) \quad\text{ou}\quad 0{,}35 \;\;(\text{se } f_{ck}\geq 50\text{ MPa})$",
       "eq_bxmin.png", width=14, height=1.6)

render(r"$x \;=\; \beta_{x}\,d$",
       "eq_x.png")

render(r"$k_{s} \;=\; \dfrac{1}{f_{yd}\,(1-\beta_{x}/2)} \,/\,10 \qquad \mathrm{[cm^{2}/(kN\cdot m)]}$",
       "eq_ks.png", width=11.5)

render(r"$A_{s,\text{req}} \;=\; k_{s}\,\dfrac{|M_{d}|}{d} \qquad \mathrm{[cm^{2}]}$",
       "eq_asreq.png", width=9)

render(r"$A_{s,\min} \;=\; \dfrac{\rho_{\min}\,b_{w}\,h}{100} \qquad \mathrm{[cm^{2}]}$",
       "eq_asmin.png")

render(r"$A_{s,\text{adot}} \;=\; \max(A_{s,\text{req}},\;A_{s,\min})$",
       "eq_asadot.png")

render(r"$n \;=\; \left\lceil\,\dfrac{A_{s,\text{adot}}}{A_{\phi}}\,\right\rceil$",
       "eq_nbarras.png")

render(r"$e_{h} \;=\; \dfrac{(b_{w} - 2c - 2\phi_{t}) - n\,\phi_{l}}{n - 1} \;\;\geq\;\; 2{,}0\;\text{cm}$",
       "eq_eh.png", width=12)


# ── Cisalhamento - Viga retangular ─────────────────────────────────────────
render(r"$V_{sd} \;=\; V_{k}\,\gamma_{f} \qquad (\gamma_{f}=1{,}4)$",
       "eq_vsd.png")

render(r"$V_{Rd2} \;=\; 0{,}27\,\lambda\,f_{cd}\,b_{w}\,d\,/\,10 \qquad \mathrm{[kN]}$",
       "eq_vrd2.png", width=10)

render(r"$f_{cd} \;=\; \dfrac{\alpha_{c}\,f_{ck}}{\gamma_{c}} \qquad \alpha_{c}=0{,}85,\;\; \gamma_{c}=1{,}4$",
       "eq_fcd.png", width=11)

render(r"$f_{ct,m} \;=\; 0{,}30\,f_{ck}^{\,2/3} \qquad\qquad f_{ctk,\inf} \;=\; 0{,}7\,f_{ct,m}$",
       "eq_fctm.png", width=11)

render(r"$f_{ctd} \;=\; \dfrac{f_{ctk,\inf}}{\gamma_{c}} \,/\,10 \qquad \mathrm{[kN/cm^{2}]}$",
       "eq_fctd.png", width=10)

render(r"$V_{c} \;=\; 0{,}6\,f_{ctd}\,b_{w}\,d \qquad \mathrm{[kN]}$",
       "eq_vc.png")

render(r"$V_{sw} \;=\; V_{sd} - V_{c}$",
       "eq_vsw.png")

render(r"$A_{sw}/s_{\min} \;=\; \rho_{w}\,b_{w} \qquad \mathrm{[cm^{2}/m]}$",
       "eq_aswmin.png")

render(r"$s \;=\; \dfrac{100}{A_{sw}/s_{\text{adot}}\,/\,A_{sw,\text{ramo}}} \qquad \mathrm{[cm]}$",
       "eq_sestribo.png", width=11)


# ── Viga T - Mesa colaborante ─────────────────────────────────────────────
render(r"$b_{f,\text{ef}} \;=\; \min(b_{f},\; b_{w} + b_{1,\text{esq}} + b_{1,\text{dir}})$",
       "eq_bfef.png", width=11)

render(r"$KC \;=\; \dfrac{b_{f,\text{ef}}\,d^{2}}{M_{d}}$",
       "eq_kc_t.png")

render(r"$0{,}8\,x \;<\; h_{f} \;\;\Longrightarrow\;\; \text{Linha neutra dentro da mesa (T valido)}$",
       "eq_ln_mesa.png", width=12.5)


print(f"OK: {len(os.listdir(OUTPUT_DIR))} imagens geradas em {OUTPUT_DIR}")
for f in sorted(os.listdir(OUTPUT_DIR)):
    print(" -", f)
