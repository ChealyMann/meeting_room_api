import { Projector } from 'lucide-vue-next'
import { describe, expect, it } from 'vitest'

import { EQUIPMENT_ICONS, iconFor } from '../equipmentIcons'

describe('equipment icons', () => {
  it('offers 50 Lucide icons, each with a unique name, a label and a component', () => {
    expect(EQUIPMENT_ICONS).toHaveLength(50)
    expect(new Set(EQUIPMENT_ICONS.map((i) => i.name)).size).toBe(50)
    for (const item of EQUIPMENT_ICONS) {
      expect(item.label).not.toBe('')
      expect(item.icon).toBeDefined()
    }
    expect(EQUIPMENT_ICONS[0]!.name).toBe('projector')
  })

  it('finds the component for a stored name, and nothing for others', () => {
    expect(iconFor('projector')).toBe(Projector)
    expect(iconFor('https://x/y.png')).toBeNull()
    expect(iconFor(null)).toBeNull()
  })
})
