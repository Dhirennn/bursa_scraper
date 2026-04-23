from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    authors: str
    year: int
    title: str
    venue: str
    note: str = ""

    def short(self) -> str:
        return f"{self.authors} ({self.year})"

    def full(self) -> str:
        base = f"{self.authors} ({self.year}). {self.title}. {self.venue}."
        return f"{base} {self.note}" if self.note else base


NOVY_MARX_2013 = Citation(
    authors="Novy-Marx, R.",
    year=2013,
    title="The Other Side of Value: The Gross Profitability Premium",
    venue="Journal of Financial Economics 108(1): 1-28",
)
GORDON_2013_EM_QUALITY = Citation(
    authors="Gordon, M.",
    year=2013,
    title="The Profitability Premium in EM Markets",
    venue="PIMCO Research",
    note="Equal-weighted long-high-ROE short-low-ROE +5.1%/yr in emerging markets.",
)
FAMA_FRENCH_1992 = Citation(
    authors="Fama, E. F., & French, K. R.",
    year=1992,
    title="The Cross-Section of Expected Stock Returns",
    venue="Journal of Finance 47(2): 427-465",
)
FAMA_FRENCH_2015 = Citation(
    authors="Fama, E. F., & French, K. R.",
    year=2015,
    title="A Five-Factor Asset Pricing Model",
    venue="Journal of Financial Economics 116(1): 1-22",
)
ASNESS_MOSKOWITZ_PEDERSEN_2013 = Citation(
    authors="Asness, C. S., Moskowitz, T. J., & Pedersen, L. H.",
    year=2013,
    title="Value and Momentum Everywhere",
    venue="Journal of Finance 68(3): 929-985",
)
JEGADEESH_TITMAN_1993 = Citation(
    authors="Jegadeesh, N., & Titman, S.",
    year=1993,
    title="Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency",
    venue="Journal of Finance 48(1): 65-91",
)
ARNOTT_ASNESS_2003 = Citation(
    authors="Arnott, R. D., & Asness, C. S.",
    year=2003,
    title="Surprise! Higher Dividends = Higher Earnings Growth",
    venue="Financial Analysts Journal 59(1): 70-87",
)
WOMACK_1996 = Citation(
    authors="Womack, K. L.",
    year=1996,
    title="Do Brokerage Analysts' Recommendations Have Investment Value?",
    venue="Journal of Finance 51(1): 137-167",
)
HOU_XUE_ZHANG_2020 = Citation(
    authors="Hou, K., Xue, C., & Zhang, L.",
    year=2020,
    title="Replicating Anomalies",
    venue="Review of Financial Studies 33(5): 2019-2133",
    note="64-85% of 447 published anomalies insignificant at t>3 — motivates our 6-factor (not 60-factor) design.",
)
CARHART_BURSA_2011_2021 = Citation(
    authors="Carhart 4F study of Bursa Malaysia",
    year=2021,
    title="Carhart 4F applied to Bursa Malaysia size-sorted portfolios, 2011-2021",
    venue="See systematic-review of Bursa factor literature",
    note="Finds SMB/HML/MKT explanatory; momentum NOT significant on Bursa size-sorted portfolios.",
)
