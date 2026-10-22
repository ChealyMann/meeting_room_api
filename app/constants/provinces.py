"""The fixed province list (spec section 8). Provinces are not a table; nobody can change them.

`locations.province` stores the code. A native speaker should check the Khmer names before release.
"""

from typing import NamedTuple


class Province(NamedTuple):
    code: str
    name_en: str
    name_kh: str


# Served by GET /provinces in this order: Phnom Penh first, then A to Z.
PROVINCES: tuple[Province, ...] = (
    Province("PHNOM_PENH", "Phnom Penh", "ភ្នំពេញ"),
    Province("BANTEAY_MEANCHEY", "Banteay Meanchey", "បន្ទាយមានជ័យ"),
    Province("BATTAMBANG", "Battambang", "បាត់ដំបង"),
    Province("KAMPONG_CHAM", "Kampong Cham", "កំពង់ចាម"),
    Province("KAMPONG_CHHNANG", "Kampong Chhnang", "កំពង់ឆ្នាំង"),
    Province("KAMPONG_SPEU", "Kampong Speu", "កំពង់ស្ពឺ"),
    Province("KAMPONG_THOM", "Kampong Thom", "កំពង់ធំ"),
    Province("KAMPOT", "Kampot", "កំពត"),
    Province("KANDAL", "Kandal", "កណ្ដាល"),
    Province("KEP", "Kep", "កែប"),
    Province("KOH_KONG", "Koh Kong", "កោះកុង"),
    Province("KRATIE", "Kratie", "ក្រចេះ"),
    Province("MONDULKIRI", "Mondulkiri", "មណ្ឌលគិរី"),
    Province("ODDAR_MEANCHEY", "Oddar Meanchey", "ឧត្ដរមានជ័យ"),
    Province("PAILIN", "Pailin", "ប៉ៃលិន"),
    Province("PREAH_SIHANOUK", "Preah Sihanouk", "ព្រះសីហនុ"),
    Province("PREAH_VIHEAR", "Preah Vihear", "ព្រះវិហារ"),
    Province("PREY_VENG", "Prey Veng", "ព្រៃវែង"),
    Province("PURSAT", "Pursat", "ពោធិ៍សាត់"),
    Province("RATANAKIRI", "Ratanakiri", "រតនគិរី"),
    Province("SIEM_REAP", "Siem Reap", "សៀមរាប"),
    Province("STUNG_TRENG", "Stung Treng", "ស្ទឹងត្រែង"),
    Province("SVAY_RIENG", "Svay Rieng", "ស្វាយរៀង"),
    Province("TAKEO", "Takeo", "តាកែវ"),
    Province("TBONG_KHMUM", "Tbong Khmum", "ត្បូងឃ្មុំ"),
)

_BY_CODE = {province.code: province for province in PROVINCES}

PROVINCE_CODES: frozenset[str] = frozenset(_BY_CODE)


def get_province(code: str) -> Province | None:
    return _BY_CODE.get(code)
