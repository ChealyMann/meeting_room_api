import { createRouter, createWebHistory } from 'vue-router'

import { useSessionStore } from '../stores/session'
import { resolveNavigation } from './guard'

declare module 'vue-router' {
  interface RouteMeta {
    /** Open without signing in. */
    public?: boolean
    /** Shown in the top bar breadcrumb. */
    title?: string
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/sign-in',
      name: 'sign-in',
      component: () => import('../views/SignInView.vue'),
      meta: { public: true, title: 'Sign in' },
    },
    {
      path: '/change-password',
      name: 'change-password',
      component: () => import('../views/ChangePasswordView.vue'),
      meta: { title: 'Choose a new password' },
    },
    {
      path: '/no-access',
      name: 'no-access',
      component: () => import('../views/NoAccessView.vue'),
      meta: { title: 'No access' },
    },
    {
      path: '/',
      name: 'shell',
      component: () => import('../layouts/AppShell.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('../views/RoomsView.vue'),
          meta: { title: 'Rooms' },
        },
        {
          path: 'offices',
          name: 'offices',
          component: () => import('../views/OfficesView.vue'),
          meta: { title: 'Offices' },
        },
        {
          path: 'buildings',
          name: 'buildings',
          component: () => import('../views/BuildingsView.vue'),
          meta: { title: 'Buildings' },
        },
        {
          path: 'floors',
          name: 'floors',
          component: () => import('../views/FloorsView.vue'),
          meta: { title: 'Floors' },
        },
        {
          path: 'room-types',
          name: 'room-types',
          component: () => import('../views/RoomTypesView.vue'),
          meta: { title: 'Room types' },
        },
        {
          path: 'equipment',
          name: 'equipment',
          component: () => import('../views/EquipmentView.vue'),
          meta: { title: 'Equipment' },
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('../views/ProfileView.vue'),
          meta: { title: 'My profile' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'home' } },
  ],
})

let restoring: Promise<void> | null = null

router.beforeEach(async (to) => {
  const session = useSessionStore()
  if (!restoring) {
    restoring = session.restore()
    // Session lost mid-use (refresh refused): go to sign-in, then come back here (DSH-A05).
    session.$onAction(({ name, after }) => {
      if (name !== 'expire') return
      after(() => {
        const current = router.currentRoute.value
        if (current.meta.public) return
        void router.replace({ name: 'sign-in', query: { redirect: current.fullPath } })
      })
    })
  }
  await restoring
  return resolveNavigation({ name: String(to.name ?? ''), fullPath: to.fullPath, meta: to.meta }, session)
})

export default router
