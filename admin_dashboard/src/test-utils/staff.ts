// Shapes the Staff page tests share.
export const building = (id: number, name: string) => ({ id, name_en: name, name_kh: 'អគារ', short_name: null })
export const roomItem = (id: number, name: string, extra: Record<string, unknown> = {}) => ({
  id,
  name_en: name,
  name_kh: 'បន្ទប់',
  short_desc: '4K screen / VC',
  capacity: 14,
  size_sqm: 50,
  start_time: '08:00',
  end_time: '17:00',
  category: { id: 1, name_en: 'Meeting room', name_kh: 'x' },
  floor: { id: 2, floor_label: 'Floor 2' },
  building: building(1, 'Head office'),
  location: { id: 1, name_en: 'NBC', name_kh: 'x' },
  province: { code: 'PHNOM_PENH', name_en: 'Phnom Penh', name_kh: 'x' },
  owner: null,
  cover_photo: null,
  is_active: true,
  is_bookable: true,
  is_private: false,
  ...extra,
})

