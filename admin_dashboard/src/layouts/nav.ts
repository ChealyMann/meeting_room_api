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
      { label: 'Offices', icon: 'landmark' },
      { label: 'Buildings', icon: 'building-2' },
      { label: 'Floors', icon: 'layers' },
    ],
  },
  {
    title: 'Catalog',
    items: [
      { label: 'Room types', icon: 'tags' },
      { label: 'Equipment', icon: 'projector' },
    ],
  },
  {
    title: 'Organisation',
    items: [
      { label: 'Departments', icon: 'network' },
      { label: 'Divisions', icon: 'git-fork' },
      { label: 'Positions', icon: 'briefcase' },
    ],
  },
  {
    title: 'People',
    items: [
      { label: 'Users', icon: 'users' },
      { label: 'Roles', icon: 'shield-check' },
    ],
  },
]
