// Per-browser display choices: day or night, whether the sidebar is folded, and how the IT
// pages show setups (rows or cards).
// Kept in localStorage (a convenience only; the app works the same without it).
import { defineStore } from 'pinia'
import { ref, watchEffect } from 'vue'

export const THEME_KEY = 'nbc.admin.theme'
export const RAIL_KEY = 'nbc.admin.rail'
export const IT_VIEW_KEY = 'nbc.admin.itView'

export type Theme = 'light' | 'dark'
export type ItView = 'rows' | 'cards'

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Private mode or blocked storage: the choice lasts until reload.
  }
}

export const useUiStore = defineStore('ui', () => {
  // Day mode unless the user picked night here before (owner decision: never follow the OS).
  const theme = ref<Theme>(read(THEME_KEY) === 'dark' ? 'dark' : 'light')
  const railCollapsed = ref(read(RAIL_KEY) === 'collapsed')
  const itView = ref<ItView>(read(IT_VIEW_KEY) === 'cards' ? 'cards' : 'rows')

  watchEffect(() => {
    document.documentElement.dataset.theme = theme.value
  })

  function toggleTheme(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    write(THEME_KEY, theme.value)
  }

  function toggleRail(): void {
    railCollapsed.value = !railCollapsed.value
    write(RAIL_KEY, railCollapsed.value ? 'collapsed' : 'open')
  }

  function setItView(view: ItView): void {
    itView.value = view
    write(IT_VIEW_KEY, view)
  }

  return { theme, railCollapsed, itView, toggleTheme, toggleRail, setItView }
})
