import { createRouter, createWebHistory } from 'vue-router'

import { useSessionStore } from '../stores/session'
import { resolveNavigation } from './guard'

declare module 'vue-router' {
  interface RouteMeta {
    /** Open without signing in. */
    public?: boolean
    /** Shown in the top bar breadcrumb. */
    title?: string
    /** The roles that may open the page; none means every dashboard role. */
    roles?: string[]
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
          meta: { title: 'Rooms', roles: ['ADMIN'] },
        },
        {
          path: 'review',
          name: 'review',
          component: () => import('../views/ReviewView.vue'),
          meta: { title: 'To review', roles: ['PITIKA'] },
        },
        {
          path: 'bookings',
          name: 'bookings',
          component: () => import('../views/BookingsView.vue'),
          meta: { title: 'Bookings', roles: ['ADMIN', 'PITIKA'] },
        },
        {
          path: 'food-list',
          name: 'food-list',
          component: () => import('../views/FoodListView.vue'),
          meta: { title: 'Food list', roles: ['ADMIN', 'PITIKA'] },
        },
        {
          path: 'offices',
          name: 'offices',
          component: () => import('../views/OfficesView.vue'),
          meta: { title: 'Offices', roles: ['ADMIN'] },
        },
        {
          path: 'buildings',
          name: 'buildings',
          component: () => import('../views/BuildingsView.vue'),
          meta: { title: 'Buildings', roles: ['ADMIN'] },
        },
        {
          path: 'floors',
          name: 'floors',
          component: () => import('../views/FloorsView.vue'),
          meta: { title: 'Floors', roles: ['ADMIN'] },
        },
        {
          path: 'room-types',
          name: 'room-types',
          component: () => import('../views/RoomTypesView.vue'),
          meta: { title: 'Room types', roles: ['ADMIN'] },
        },
        {
          path: 'equipment',
          name: 'equipment',
          component: () => import('../views/EquipmentView.vue'),
          meta: { title: 'Equipment', roles: ['ADMIN'] },
        },
        {
          path: 'public-holidays',
          name: 'public-holidays',
          component: () => import('../views/HolidaysView.vue'),
          meta: { title: 'Public holidays', roles: ['ADMIN'] },
        },
        {
          path: 'catering-packages',
          name: 'catering-packages',
          component: () => import('../views/ServiceCatalogView.vue'),
          props: { kind: 'catering' },
          meta: { title: 'Catering packages', roles: ['ADMIN'] },
        },
        {
          path: 'it-services',
          name: 'it-services',
          component: () => import('../views/ServiceCatalogView.vue'),
          props: { kind: 'it' },
          meta: { title: 'IT services', roles: ['ADMIN'] },
        },
        {
          path: 'departments',
          name: 'departments',
          component: () => import('../views/DepartmentsView.vue'),
          meta: { title: 'Departments', roles: ['ADMIN'] },
        },
        {
          path: 'divisions',
          name: 'divisions',
          component: () => import('../views/DivisionsView.vue'),
          meta: { title: 'Divisions', roles: ['ADMIN'] },
        },
        {
          path: 'positions',
          name: 'positions',
          component: () => import('../views/PositionsView.vue'),
          meta: { title: 'Positions', roles: ['ADMIN'] },
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('../views/UsersView.vue'),
          meta: { title: 'Users', roles: ['ADMIN'] },
        },
        {
          path: 'roles',
          name: 'roles',
          component: () => import('../views/RolesView.vue'),
          meta: { title: 'Roles', roles: ['ADMIN'] },
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
  return resolveNavigation(
    { name: String(to.name ?? ''), fullPath: to.fullPath, meta: to.meta },
    { signedIn: session.signedIn, mustChangePassword: session.mustChangePassword, roles: session.roleCodes },
  )
})

export default router
