<script setup lang="ts">
import {
  Briefcase,
  Building2,
  DoorOpen,
  GitFork,
  Landmark,
  Layers,
  LogOut,
  Network,
  Projector,
  ShieldCheck,
  Tags,
  Users,
  X,
} from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, type Component } from 'vue'
import { useRouter } from 'vue-router'

import { useSessionStore } from '../stores/session'
import { usePrivateImage } from '../composables/usePrivateImage'
import { NAV_GROUPS } from './nav'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const ICONS: Record<string, Component> = {
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

// Served from public/, not bundled.
const LOGO = '/nbc-logo.png'

const session = useSessionStore()
const router = useRouter()

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
  if (event.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <aside class="rail" :class="{ open }" aria-label="Main">
    <div class="brand">
      <img :src="LOGO" alt="National Bank of Cambodia" width="36" height="36" />
      <div class="brand-text"><b>Meeting Rooms</b><span>Admin</span></div>
      <button type="button" class="close" aria-label="Close menu" @click="emit('close')">
        <X aria-hidden="true" />
      </button>
    </div>

    <nav class="nav">
      <template v-for="group in NAV_GROUPS" :key="group.title ?? 'top'">
        <h2 v-if="group.title">{{ group.title }}</h2>
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
      </template>
    </nav>

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
  background: var(--color-rail);
  color: var(--color-rail-ink);
  border-right: 1px solid var(--color-rail-line);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
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
  overflow-y: auto;
  padding: 8px 12px 16px;
  scrollbar-color: var(--color-rail-line) transparent;
}
.nav h2 {
  margin: 16px 8px 4px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-rail-muted);
}
.nav a {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 6px;
  color: var(--color-rail-ink);
  font-size: 13.5px;
  text-decoration: none;
  transition: background-color 120ms ease;
}
.nav a svg.lucide {
  color: var(--color-rail-muted);
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
  padding: 12px 12px 12px 14px;
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

/* Collapsed rail: icons only; each link keeps its name for screen readers. */
@media (max-width: 1100px) and (min-width: 761px) {
  .brand {
    padding: 16px 14px;
  }
  .brand-text,
  .nav h2,
  .me-text {
    display: none;
  }
  .nav .label {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
  .nav {
    padding: 8px 8px 16px;
  }
  .nav a {
    justify-content: center;
    padding: 9px;
  }
  /* Initials over the sign-out button: the 64px rail still lets the user sign out. */
  .who {
    flex-direction: column;
    justify-content: center;
    padding: 12px 8px;
  }
  .me {
    flex: none;
    padding: 0;
  }
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
