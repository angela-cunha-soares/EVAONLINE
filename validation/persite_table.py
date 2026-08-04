"""Full per-site validation table (Supplementary).

Generates the complete 17-site breakdown (EVAonline Fusion) so readers can
inspect site-level skill directly, sorted by KGE. Writes a ready-to-paste
LaTeX body to outputs/persite_table.tex.
"""

from __future__ import annotations

import pandas as pd

from validation import config

DISP = {
    "Alvorada_do_Gurgueia_PI": r"Alvorada do Gurgu\'eia, PI",
    "Araguaina_TO": r"Aragua\'ina, TO",
    "Balsas_MA": "Balsas, MA",
    "Barreiras_BA": "Barreiras, BA",
    "Bom_Jesus_PI": "Bom Jesus, PI",
    "Campos_Lindos_TO": "Campos Lindos, TO",
    "Carolina_MA": "Carolina, MA",
    "Corrente_PI": "Corrente, PI",
    "Formosa_do_Rio_Preto_BA": "Formosa do Rio Preto, BA",
    "Imperatriz_MA": "Imperatriz, MA",
    "Luiz_Eduardo_Magalhaes_BA": r"Lu\'is Eduardo Magalh\~aes, BA",
    "Pedro_Afonso_TO": "Pedro Afonso, TO",
    "Piracicaba_SP": "Piracicaba, SP",
    "Porto_Nacional_TO": "Porto Nacional, TO",
    "Sao_Desiderio_BA": r"S\~ao Desid\'erio, BA",
    "Tasso_Fragoso_MA": "Tasso Fragoso, MA",
    "Urucui_PI": r"Uru\c{c}u\'i, PI",
}


def main() -> None:
    out = config.ensure_outputs()
    d = pd.read_csv(config.FINAL_SUMMARY).sort_values("kge", ascending=False)

    lines = []
    for _, r in d.iterrows():
        lines.append(
            f"{DISP.get(r['city'], r['city'])} & {r['r2']:.3f} & {r['kge']:.3f} "
            f"& {r['nse']:.3f} & {r['mae']:.3f} & {r['rmse']:.3f} & {r['pbias']:+.2f} \\\\"
        )
    lines.append("\\midrule")
    lines.append(
        f"\\textbf{{Median}} & {d.r2.median():.3f} & {d.kge.median():.3f} & "
        f"{d.nse.median():.3f} & {d.mae.median():.3f} & {d.rmse.median():.3f} & "
        f"{d.pbias.median():+.2f} \\\\"
    )
    lines.append(
        f"\\textbf{{[Min, Max]}} & [{d.r2.min():.2f}, {d.r2.max():.2f}] & "
        f"[{d.kge.min():.2f}, {d.kge.max():.2f}] & [{d.nse.min():.2f}, {d.nse.max():.2f}] & "
        f"[{d.mae.min():.2f}, {d.mae.max():.2f}] & [{d.rmse.min():.2f}, {d.rmse.max():.2f}] & "
        f"[{d.pbias.min():+.2f}, {d.pbias.max():+.2f}] \\\\"
    )
    body = "\n".join(lines)
    (out / "persite_table.tex").write_text(body + "\n", encoding="utf-8")
    print(body)
    print(f"\nWritten to {out / 'persite_table.tex'}")


if __name__ == "__main__":
    main()
