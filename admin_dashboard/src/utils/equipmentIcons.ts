// The icons an equipment item can have (DSH-C02). The API stores the Lucide name (kebab case);
// this fixed list keeps the picker short and the bundle small. A stored name that is not here
// (from the mobile app, or a URL) is kept and shown as "Unknown icon".
import {
  Accessibility,
  AirVent,
  Airplay,
  Armchair,
  BatteryCharging,
  Cable,
  Calendar,
  Camera,
  Cast,
  Clipboard,
  Clock,
  Coffee,
  CupSoda,
  Droplets,
  Fan,
  FlipHorizontal,
  Gamepad2,
  Headphones,
  Keyboard,
  KeyRound,
  Lamp,
  Laptop,
  Lightbulb,
  Lock,
  Mic,
  Monitor,
  Mouse,
  NotebookPen,
  Package,
  PenLine,
  Phone,
  Plug,
  Presentation,
  Printer,
  Projector,
  Radio,
  Router,
  Snowflake,
  Sofa,
  Speaker,
  SquarePen,
  Thermometer,
  Tv,
  TvMinimal,
  Usb,
  Utensils,
  Video,
  Volume2,
  Webcam,
  Wifi,
} from 'lucide-vue-next'
import type { Component } from 'vue'

export interface EquipmentIcon {
  /** What the API stores: the Lucide name. */
  name: string
  /** A short English word to search by. */
  label: string
  icon: Component
}

export const EQUIPMENT_ICONS: ReadonlyArray<EquipmentIcon> = [
  { name: 'projector', label: 'Projector', icon: Projector },
  { name: 'presentation', label: 'Presentation board', icon: Presentation },
  { name: 'monitor', label: 'Monitor', icon: Monitor },
  { name: 'tv', label: 'TV', icon: Tv },
  { name: 'tv-minimal', label: 'Screen', icon: TvMinimal },
  { name: 'airplay', label: 'Screen sharing', icon: Airplay },
  { name: 'cast', label: 'Cast', icon: Cast },
  { name: 'video', label: 'Video call', icon: Video },
  { name: 'webcam', label: 'Webcam', icon: Webcam },
  { name: 'camera', label: 'Camera', icon: Camera },
  { name: 'mic', label: 'Microphone', icon: Mic },
  { name: 'speaker', label: 'Speaker', icon: Speaker },
  { name: 'volume-2', label: 'Sound', icon: Volume2 },
  { name: 'headphones', label: 'Headphones', icon: Headphones },
  { name: 'phone', label: 'Phone', icon: Phone },
  { name: 'laptop', label: 'Laptop', icon: Laptop },
  { name: 'keyboard', label: 'Keyboard', icon: Keyboard },
  { name: 'mouse', label: 'Mouse', icon: Mouse },
  { name: 'printer', label: 'Printer', icon: Printer },
  { name: 'cable', label: 'Cable', icon: Cable },
  { name: 'plug', label: 'Power socket', icon: Plug },
  { name: 'usb', label: 'USB', icon: Usb },
  { name: 'wifi', label: 'Wi-Fi', icon: Wifi },
  { name: 'router', label: 'Router', icon: Router },
  { name: 'battery-charging', label: 'Charger', icon: BatteryCharging },
  { name: 'lamp', label: 'Lamp', icon: Lamp },
  { name: 'lightbulb', label: 'Light', icon: Lightbulb },
  { name: 'air-vent', label: 'Air conditioning', icon: AirVent },
  { name: 'fan', label: 'Fan', icon: Fan },
  { name: 'snowflake', label: 'Cooling', icon: Snowflake },
  { name: 'thermometer', label: 'Thermometer', icon: Thermometer },
  { name: 'armchair', label: 'Armchair', icon: Armchair },
  { name: 'sofa', label: 'Sofa', icon: Sofa },
  { name: 'coffee', label: 'Coffee', icon: Coffee },
  { name: 'cup-soda', label: 'Drinks', icon: CupSoda },
  { name: 'utensils', label: 'Catering', icon: Utensils },
  { name: 'droplets', label: 'Water', icon: Droplets },
  { name: 'clipboard', label: 'Clipboard', icon: Clipboard },
  { name: 'pen-line', label: 'Pen', icon: PenLine },
  { name: 'notebook-pen', label: 'Notebook', icon: NotebookPen },
  { name: 'square-pen', label: 'Whiteboard', icon: SquarePen },
  { name: 'accessibility', label: 'Accessible', icon: Accessibility },
  { name: 'lock', label: 'Lock', icon: Lock },
  { name: 'key-round', label: 'Key', icon: KeyRound },
  { name: 'package', label: 'Supplies', icon: Package },
  { name: 'clock', label: 'Clock', icon: Clock },
  { name: 'calendar', label: 'Calendar', icon: Calendar },
  { name: 'radio', label: 'Radio', icon: Radio },
  { name: 'gamepad-2', label: 'Controller', icon: Gamepad2 },
  { name: 'flip-horizontal', label: 'Mirror', icon: FlipHorizontal },
]

const BY_NAME = new Map(EQUIPMENT_ICONS.map((item) => [item.name, item.icon]))

/** The component for a stored icon name, or null when it is not in the list (or empty). */
export function iconFor(name: string | null): Component | null {
  return (name && BY_NAME.get(name)) || null
}
