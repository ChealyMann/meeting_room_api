import {
  Briefcase,
  Building2,
  CalendarCheck,
  CalendarDays,
  DoorOpen,
  GitFork,
  Inbox,
  Landmark,
  MonitorCog,
  Layers,
  ListChecks,
  Network,
  Projector,
  ShieldCheck,
  Tags,
  Users,
  Utensils,
  UtensilsCrossed,
  Wrench,
} from 'lucide-vue-next'
import type { Component } from 'vue'

export interface NavItem {
  label: string
  /** Lucide icon name, drawn by AppRail. */
  icon: string
  /** Route name; items without one are not built yet. */
  route?: string
  /** The roles that see the item; none means the Admin only. */
  roles?: string[]
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
      { label: 'To review', icon: 'inbox', route: 'review', roles: ['PITIKA'] },
      { label: 'To review', icon: 'inbox', route: 'owner-review', roles: ['ROOM_OWNER'] },
      { label: 'IT setup', icon: 'wrench', route: 'it-setup', roles: ['IT_LEAD'] },
      { label: 'My tasks', icon: 'list-checks', route: 'my-tasks', roles: ['IT_STAFF'] },
      { label: 'Bookings', icon: 'calendar-check', route: 'bookings', roles: ['ADMIN', 'PITIKA', 'ROOM_OWNER'] },
      { label: 'Food list', icon: 'utensils-crossed', route: 'food-list', roles: ['ADMIN', 'PITIKA'] },
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
  inbox: Inbox,
  wrench: Wrench,
  'list-checks': ListChecks,
  briefcase: Briefcase,
  users: Users,
  'shield-check': ShieldCheck,
}

/** The menu for these role codes: items the roles may see, and groups that keep any. A Pitika
 *  who also owns a room sees the owner page as "My rooms", so there are not two "To review". */
export function navFor(roles: string[]): NavGroup[] {
  const sees = (item: NavItem) => (item.roles ?? ['ADMIN']).some((role) => roles.includes(role))
  const named = (item: NavItem): NavItem =>
    item.route === 'owner-review' && roles.includes('PITIKA') ? { ...item, label: 'My rooms', icon: 'door-open' } : item
  return NAV_GROUPS.map((group) => ({ ...group, items: group.items.filter(sees).map(named) })).filter((group) => group.items.length > 0)
}

/** The rail's subtitle: the first dashboard role the user has, in the home order. */
export function roleTitle(roles: string[]): string {
  if (roles.includes('ADMIN')) return 'Admin'
  if (roles.includes('PITIKA')) return 'Pitika'
  if (roles.includes('ROOM_OWNER')) return 'Room owner'
  if (roles.includes('IT_LEAD')) return 'IT Lead'
  if (roles.includes('IT_STAFF')) return 'IT Staff'
  return ''
}

/** The menu item of this route for these roles (with "My rooms" applied), or null. */
function itemFor(route: unknown, roles: string[]): NavItem | null {
  const all = roles.length ? navFor(roles) : NAV_GROUPS
  return all.flatMap((group) => group.items).find((i) => i.route === route) ?? null
}

/** The page's name as the menu shows it ("My rooms"), or null for a page outside the menu. */
export function pageLabel(route: unknown, roles: string[]): string | null {
  return itemFor(route, roles)?.label ?? null
}

/** The menu icon of the page with this route name, if the menu has it. */
export function navIcon(route: unknown, roles: string[] = []): Component | undefined {
  const item = itemFor(route, roles)
  return item ? NAV_ICONS[item.icon] : undefined
}
