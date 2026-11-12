// The icon of a food or IT item: the one the Admin set, else a guess from its name and
// description, else a plain default. The name goes in data-icon so a test can read it.
import {
  Apple,
  Cable,
  Coffee,
  Cookie,
  CupSoda,
  GlassWater,
  Headset,
  Laptop,
  Mic,
  Monitor,
  Projector,
  Sandwich,
  Soup,
  Speaker,
  Utensils,
  Video,
  Wifi,
  type LucideIcon,
} from 'lucide-vue-next'
import type { Component } from 'vue'

import { iconFor } from '../../../utils/equipmentIcons'

type Guess = [RegExp, string, LucideIcon]

// Khmer words have no \b (it only knows Latin letters), so they stand on their own.
const FOOD: Guess[] = [
  [/\b(coffee|tea)|កាហ្វេ|តែ/i, 'coffee', Coffee],
  [/\b(lunch|dinner|meal|rice|buffet|box)|បាយ/i, 'utensils', Utensils],
  [/\b(soup|porridge|noodle)|បបរ|គុយទាវ/i, 'soup', Soup],
  [/\b(sandwich|bread|baguette)|នំបុ័ង/i, 'sandwich', Sandwich],
  [/\b(cake|pastr|cookie|snack)|នំ/i, 'cookie', Cookie],
  [/\bfruit|ផ្លែ/i, 'apple', Apple],
  [/\b(juice|soda|soft drink)/i, 'cup-soda', CupSoda],
  [/\bwater|ទឹក/i, 'glass-water', GlassWater],
]
const IT: Guess[] = [
  [/\bprojector/i, 'projector', Projector],
  [/\b(mic|microphone)/i, 'mic', Mic],
  [/\b(video|zoom|teams|camera)/i, 'video', Video],
  [/\b(sound|speaker|audio|interpret)/i, 'speaker', Speaker],
  [/\b(screen|display|tv|monitor)/i, 'monitor', Monitor],
  [/\b(wifi|wi-fi|internet|network)/i, 'wifi', Wifi],
  [/\b(laptop|computer|pc)\b/i, 'laptop', Laptop],
  [/\b(cable|hdmi|adapter)/i, 'cable', Cable],
]

export function serviceIcon(
  item: { name: string; description: string | null; icon?: string | null },
  kind: 'food' | 'it',
): { name: string; icon: Component } {
  const set = item.icon ? iconFor(item.icon) : null
  if (set && item.icon) return { name: item.icon, icon: set }
  const text = `${item.name} ${item.description ?? ''}`
  // A word match first in the name, then anywhere: "Fruit and water" is fruit, not water.
  for (const source of [item.name, text]) {
    const hit = (kind === 'food' ? FOOD : IT).find(([re]) => re.test(source))
    if (hit) return { name: hit[1], icon: hit[2] }
  }
  return kind === 'food' ? { name: 'utensils', icon: Utensils } : { name: 'headset', icon: Headset }
}
