import {
  Briefcase,
  Building2,
  CalendarCheck,
  CalendarDays,
  DoorOpen,
  GitFork,
  Landmark,
  MonitorCog,
  Layers,
  Network,
  Projector,
  ShieldCheck,
  Tags,
  Users,
  Utensils,
  UtensilsCrossed,
} from 'lucide-vue-next'
import type { Component } from 'vue'

export interface NavItem {
  label: string
  /** Lucide icon name, drawn by AppRail. */
  icon: string
  /** Route name; items without one are not built yet. */
  route?: string
}

export interface NavGroup {
  title: string | null
  /** Setup groups fold (owner decision, 4 Nov 2026: "daily first, setup folds"); they carry an icon. */
  foldable?: boolean
  icon?: string
  items: NavItem[]
}

// The pages used every day come first; the setup lists fold below them.
export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Daily',
    items: [
      { label: 'Bookings', icon: 'calendar-check', route: 'bookings' },
      { label: 'Food list', icon: 'utensils-crossed', route: 'food-list' },
      { label: 'Rooms', icon: 'door-open', route: 'home' },
    ],
  },
  {
    title: 'Places',
    foldable: true,
    icon: 'building-2',
    items: [
      { label: 'Offices', icon: 'landmark', route: 'offices' },
      { label: 'Buildings', icon: 'building-2', route: 'buildings' },
      { label: 'Floors', icon: 'layers', route: 'floors' },
    ],
  },
  {
    title: 'Catalog',
    foldable: true,
    icon: 'tags',
    items: [
      { label: 'Room types', icon: 'tags', route: 'room-types' },
      { label: 'Equipment', icon: 'projector', route: 'equipment' },
      { label: 'Catering packages', icon: 'utensils', route: 'catering-packages' },
      { label: 'IT services', icon: 'monitor-cog', route: 'it-services' },
      { label: 'Public holidays', icon: 'calendar-days', route: 'public-holidays' },
    ],
  },
  {
    title: 'Organisation',
    foldable: true,
    icon: 'network',
    items: [
      { label: 'Departments', icon: 'network', route: 'departments' },
      { label: 'Divisions', icon: 'git-fork', route: 'divisions' },
      { label: 'Positions', icon: 'briefcase', route: 'positions' },
    ],
  },
  {
    title: 'People',
    foldable: true,
    icon: 'users',
    items: [
      { label: 'Users', icon: 'users', route: 'users' },
      { label: 'Roles', icon: 'shield-check', route: 'roles' },
    ],
  },
]

/** The Lucide component for each `NavItem.icon` name. */
export const NAV_ICONS: Record<string, Component> = {
  'door-open': DoorOpen,
  landmark: Landmark,
  'building-2': Building2,
  layers: Layers,
  tags: Tags,
  projector: Projector,
  utensils: Utensils,
  'utensils-crossed': UtensilsCrossed,
  'monitor-cog': MonitorCog,
  'calendar-check': CalendarCheck,
  'calendar-days': CalendarDays,
  network: Network,
  'git-fork': GitFork,
  briefcase: Briefcase,
  users: Users,
  'shield-check': ShieldCheck,
}

/** The menu icon of the page with this route name, if the menu has it. */
export function navIcon(route: unknown): Component | undefined {
  const item = NAV_GROUPS.flatMap((group) => group.items).find((i) => i.route === route)
  return item && NAV_ICONS[item.icon]
}
