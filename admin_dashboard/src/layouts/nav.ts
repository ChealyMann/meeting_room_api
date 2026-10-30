import {
  Briefcase,
  Building2,
  DoorOpen,
  GitFork,
  Landmark,
  Layers,
  Network,
  Projector,
  ShieldCheck,
  Tags,
  Users,
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
  items: NavItem[]
}

export const NAV_GROUPS: NavGroup[] = [
  { title: null, items: [{ label: 'Rooms', icon: 'door-open', route: 'home' }] },
  {
    title: 'Places',
    items: [
      { label: 'Offices', icon: 'landmark', route: 'offices' },
      { label: 'Buildings', icon: 'building-2', route: 'buildings' },
      { label: 'Floors', icon: 'layers', route: 'floors' },
    ],
  },
  {
    title: 'Catalog',
    items: [
      { label: 'Room types', icon: 'tags', route: 'room-types' },
      { label: 'Equipment', icon: 'projector', route: 'equipment' },
    ],
  },
  {
    title: 'Organisation',
    items: [
      { label: 'Departments', icon: 'network', route: 'departments' },
      { label: 'Divisions', icon: 'git-fork', route: 'divisions' },
      { label: 'Positions', icon: 'briefcase', route: 'positions' },
    ],
  },
  {
    title: 'People',
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
