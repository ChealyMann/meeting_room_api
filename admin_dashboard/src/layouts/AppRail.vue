<script setup lang="ts">
import { ChevronDown, ChevronRight, LogOut, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useSessionStore } from '../stores/session'
import { usePrivateImage } from '../composables/usePrivateImage'
import { NAV_GROUPS, NAV_ICONS as ICONS, type NavGroup } from './nav'

const props = defineProps<{ open: boolean; compact: boolean }>()
const emit = defineEmits<{ close: [] }>()

// Served from public/, not bundled.
const LOGO = '/nbc-logo.png'

const session = useSessionStore()
const router = useRouter()
const route = useRoute()

// Setup groups fold; the one holding the current page opens by itself, the others keep what
// the Admin chose. The folded (icon-only) rail shows every link, with no group headers.
const SETUP_AT = NAV_GROUPS.findIndex((group) => group.foldable)
const opened = ref<Record<string, boolean>>({})
const isOpen = (group: NavGroup) => !!opened.value[group.title ?? '']
function toggle(group: NavGroup) {
  opened.value = { ...opened.value, [group.title ?? '']: !isOpen(group) }
}
watch(
  () => route.name,
  (name) => {
    const holder = NAV_GROUPS.find((group) => group.foldable && group.items.some((item) => item.route === name))
    if (holder && !isOpen(holder)) toggle(holder)
  },
  { immediate: true },
)

// Folded rail (owner decision, 4 Nov 2026, option A): one icon per setup group; its links pop
// out in a small menu beside it. The icon of the group holding the current page is marked.
const holds = (group: NavGroup) => group.items.some((item) => item.route === route.name)
// The open menu, by group title (a stored group object would come back wrapped by Vue).
const menuTitle = ref<string | null>(null)
const menuGroup = computed(() => NAV_GROUPS.find((group) => group.title === menuTitle.value) ?? null)
const menuAt = ref({ top: 0, left: 0 })
const menuEl = ref<HTMLElement | null>(null)
function toggleMenu(group: NavGroup, event: MouseEvent) {
  if (menuTitle.value === group.title) {
    menuTitle.value = null
    return
  }
  const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
  menuAt.value = { top: Math.max(8, box.top - 8), left: box.right + 8 }
  menuTitle.value = group.title
}
watch([() => route.name, () => props.compact], () => (menuTitle.value = null))
function onPointerDown(event: PointerEvent) {
  const target = event.target as Element | null
  if (!menuGroup.value || !target) return
  if (menuEl.value?.contains(target) || target.closest('.group-icon')) return
  menuTitle.value = null
}
onMounted(() => document.addEventListener('pointerdown', onPointerDown))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onPointerDown))

// The user's photo, when they have one; otherwise the initials show.
const { imageUrl: photo } = usePrivateImage(
  () => session.user?.avatar_url ?? null,
  () => session.user?.updated_at,
)

const initials = computed(() =>
  (session.user?.name_en ?? '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join(''),
)

async function signOut() {
  await session.signOut()
  await router.push({ name: 'sign-in' })
}

function onKey(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (menuTitle.value) menuTitle.value = null
  else emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <aside class="rail" :class="{ open, compact }" aria-label="Main">
    <div class="brand">
      <img :src="LOGO" alt="National Bank of Cambodia" width="36" height="36" />
      <div class="brand-text"><b>Meeting Rooms</b><span>Admin</span></div>
      <button type="button" class="close" aria-label="Close menu" @click="emit('close')">
        <X aria-hidden="true" />
      </button>
    </div>

    <nav class="nav">
      <template v-for="(group, index) in NAV_GROUPS" :key="group.title ?? 'top'">
        <h2 v-if="index === SETUP_AT && !compact">Setup</h2>
        <span v-if="index === SETUP_AT && compact" class="divider" aria-hidden="true" />
        <h2 v-if="group.title && !group.foldable && !compact">{{ group.title }}</h2>
        <button
          v-if="group.foldable && compact"
          type="button"
          class="group-icon"
          :class="{ holds: holds(group) }"
          :aria-label="group.title ?? ''"
          :title="group.title ?? ''"
          aria-haspopup="menu"
          :aria-expanded="menuTitle === group.title ? 'true' : 'false'"
          @click="toggleMenu(group, $event)"
        >
          <component :is="ICONS[group.icon ?? '']" aria-hidden="true" />
        </button>
        <button
          v-if="group.foldable && !compact"
          type="button"
          class="fold"
          :aria-expanded="isOpen(group) ? 'true' : 'false'"
          :title="group.title ?? ''"
          @click="toggle(group)"
        >
          <component :is="ICONS[group.icon ?? '']" aria-hidden="true" />
          <span class="label">{{ group.title }}</span>
          <span class="count">{{ group.items.length }}</span>
          <ChevronDown v-if="isOpen(group)" class="chevron" aria-hidden="true" />
          <ChevronRight v-else class="chevron" aria-hidden="true" />
        </button>
        <div v-if="!group.foldable || (!compact && isOpen(group))" :class="{ sub: group.foldable }">
        <template v-for="item in group.items" :key="item.label">
          <RouterLink
            v-if="item.route"
            v-slot="{ href, navigate, isExactActive }"
            :to="{ name: item.route }"
            custom
          >
            <a
              :href="href"
              :aria-current="isExactActive ? 'page' : undefined"
              :title="item.label"
              @click="navigate"
            >
              <component :is="ICONS[item.icon]" aria-hidden="true" />
              <span class="label">{{ item.label }}</span>
            </a>
          </RouterLink>
          <a v-else role="link" aria-disabled="true" title="Coming soon">
            <component :is="ICONS[item.icon]" aria-hidden="true" />
            <span class="label">{{ item.label }}</span>
          </a>
        </template>
        </div>
      </template>
    </nav>

    <Teleport to="body">
      <div
        v-if="menuGroup && compact"
        ref="menuEl"
        class="rail-menu"
        role="menu"
        :aria-label="menuGroup.title ?? ''"
        :style="{ top: `${menuAt.top}px`, left: `${menuAt.left}px` }"
      >
        <span class="menu-title">{{ menuGroup.title }}</span>
        <template v-for="item in menuGroup.items" :key="item.label">
          <RouterLink v-if="item.route" v-slot="{ href, navigate, isExactActive }" :to="{ name: item.route }" custom>
            <a :href="href" role="menuitem" :aria-current="isExactActive ? 'page' : undefined" @click="navigate">
              {{ item.label }}
            </a>
          </RouterLink>
        </template>
      </div>
    </Teleport>

    <div class="who">
      <RouterLink :to="{ name: 'profile' }" class="me" title="My profile">
        <span class="initials" aria-hidden="true">
          <img v-if="photo" :src="photo" alt="" />
          <template v-else>{{ initials }}</template>
        </span>
        <span class="me-text">
          <b>{{ session.user?.name_en }}</b>
          <span>{{ session.user?.email }}</span>
        </span>
        <span class="sr-only">My profile</span>
      </RouterLink>
      <button type="button" class="sign-out" aria-label="Sign out" title="Sign out" @click="signOut">
        <LogOut aria-hidden="true" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
.rail {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden; /* clips text while the rail narrows */
  background: var(--color-rail);
  color: var(--color-rail-ink);
  border-right: 1px solid var(--color-rail-line);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 14px 16px; /* logo at 14px: centred in the 64px folded rail too */
}
.brand img {
  width: 36px;
  height: 36px;
}
.brand b {
  display: block;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.brand-text span {
  display: block;
  font-size: 12px;
  color: var(--color-rail-muted);
}
.close {
  display: none;
}

.nav {
  flex: 1;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 8px 8px 16px; /* same in both states, so icons never move */
  scrollbar-color: var(--color-rail-line) transparent;
}
.nav h2 {
  margin: 16px 8px 4px 16px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-rail-muted);
  white-space: nowrap;
}
.nav a {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px 7px 16px; /* icon at 8 + 16 = 24px: centred in the 64px rail */
  overflow: hidden;
  border-radius: 6px;
  color: var(--color-rail-ink);
  font-size: 13.5px;
  text-decoration: none;
  white-space: nowrap;
  transition: background-color 120ms ease;
}
.nav a svg.lucide {
  color: var(--color-rail-muted);
}
/* A setup group's header: the same row as a link, with its count and a chevron. */
.fold {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 7px 10px 7px 16px;
  overflow: hidden;
  border: 0;
  border-radius: 6px;
  background: none;
  color: var(--color-rail-ink);
  font: inherit;
  font-size: 13.5px;
  white-space: nowrap;
  text-align: left;
  cursor: pointer;
  transition: background-color 120ms ease;
}
.fold:hover {
  background: rgba(255, 255, 255, 0.05);
}
.fold svg.lucide {
  color: var(--color-rail-muted);
}
.fold .label {
  flex: 1;
}
.fold .count {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-rail-muted);
}
.fold .chevron {
  width: 14px;
  height: 14px;
}
/* An open group's links sit under its header, on a thin rail line. */
.sub {
  margin: 2px 0 6px 23px;
  padding-left: 6px;
  border-left: 1px solid var(--color-rail-line);
}
.sub a {
  padding-left: 12px;
  font-size: 13px;
}
.nav a[href]:hover {
  background: rgba(255, 255, 255, 0.05);
}
.nav a[aria-disabled='true'] {
  color: var(--color-rail-muted);
  cursor: default;
}
.nav a[aria-current='page'] {
  background: var(--color-rail-raised);
}
.nav a[aria-current='page'] svg.lucide {
  color: var(--color-thread);
}
/* The security thread: a windowed 1px gold line, like the thread woven through a note. */
.nav a[aria-current='page']::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 1px;
  background: repeating-linear-gradient(
    to bottom,
    var(--color-thread) 0 5px,
    transparent 5px 8px
  );
}
.rail :focus-visible {
  outline-color: var(--color-thread);
}

.who {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 12px 12px 10px; /* initials at 10 + 6 = 16px: centred in the 64px rail */
  border-top: 1px solid var(--color-rail-line);
}
.me {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 4px 6px;
  border-radius: 6px;
  color: inherit;
  text-decoration: none;
}
.me:hover {
  background: rgba(255, 255, 255, 0.05);
}
.initials {
  flex: none;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--color-rail-raised);
  color: var(--color-thread);
  font-size: 12px;
  font-weight: 600;
}
.initials img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.me-text {
  min-width: 0;
}
.me-text b,
.me-text span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.me-text b {
  font-size: 13px;
  font-weight: 500;
}
.me-text span {
  font-size: 12px;
  color: var(--color-rail-muted);
}
.sign-out,
.close {
  flex: none;
  padding: 6px;
  border: 0;
  border-radius: 6px;
  background: none;
  color: var(--color-rail-muted);
  cursor: pointer;
}
.sign-out:hover,
.close:hover {
  color: var(--color-rail-ink);
  background: rgba(255, 255, 255, 0.06);
}

/* Text that fades when the rail folds. Opening: fade in after the rail has made room. */
.brand-text,
.nav h2,
.nav .label {
  white-space: nowrap;
  transition: opacity 160ms var(--ease-out-quint) 80ms;
}

/* Folded rail (toggle, or always on tablets): icons only. Icons keep their place; text
   fades out fast (no delay) and stays in the accessibility tree, so links keep their names. */
/* Folded: the daily links, a line, then one icon per setup group (its links pop out). */
.divider {
  display: block;
  height: 1px;
  margin: 10px 18px;
  background: var(--color-rail-line);
}
.group-icon {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  padding: 7px 10px 7px 16px; /* the icon lines up with the links above */
  border: 0;
  border-radius: 6px;
  background: none;
  color: var(--color-rail-muted);
  cursor: pointer;
}
.group-icon:hover,
.group-icon[aria-expanded='true'] {
  background: rgba(255, 255, 255, 0.05);
}
.group-icon.holds {
  background: var(--color-rail-raised);
  color: var(--color-thread);
}
.group-icon.holds::before,
.rail-menu a[aria-current='page']::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 1px;
  background: repeating-linear-gradient(to bottom, var(--color-thread) 0 5px, transparent 5px 8px);
}
.rail-menu {
  position: fixed;
  z-index: 60;
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 210px;
  box-sizing: border-box;
  padding: 8px;
  border: 1px solid var(--color-rail-line);
  border-radius: 10px;
  background: var(--color-rail);
  box-shadow: 0 12px 28px rgba(38, 7, 7, 0.35);
  font-family: var(--font-sans);
}
.menu-title {
  padding: 4px 10px 6px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-rail-muted);
}
.rail-menu a {
  position: relative;
  display: flex;
  align-items: center;
  height: 34px;
  padding: 0 10px 0 14px;
  border-radius: 6px;
  color: var(--color-rail-ink);
  font-size: 13.5px;
  text-decoration: none;
}
.rail-menu a:hover {
  background: rgba(255, 255, 255, 0.05);
}
.rail-menu a[aria-current='page'] {
  background: var(--color-rail-raised);
}
.rail-menu a:focus-visible,
.group-icon:focus-visible {
  outline: 2px solid var(--color-thread);
  outline-offset: -2px;
}
.compact .brand-text,
.compact .nav h2,
.compact .nav .label {
  opacity: 0;
  transition: opacity 100ms var(--ease-out-quint);
}
/* Initials over the sign-out button: the 64px rail still lets the user sign out.
   This switch is instant by design. */
.compact .who {
  flex-direction: column;
  justify-content: center;
  padding: 12px 8px;
}
.compact .me {
  flex: none;
  padding: 0;
}
.compact .me-text {
  display: none;
}

/* Phone: the rail is a drawer. */
@media (max-width: 760px) {
  .rail {
    display: none;
  }
  .rail.open {
    display: flex;
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 40;
    width: min(280px, 86vw);
    animation: drawer-in 240ms var(--ease-out-quint);
  }
  .close {
    display: inline-grid;
    margin-left: auto;
  }
}
@keyframes drawer-in {
  from {
    transform: translateX(-24px);
    opacity: 0;
  }
}
</style>
