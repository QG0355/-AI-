import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', component: () => import('../views/front/HomeView.vue') },
  { path: '/login', component: () => import('../views/front/LoginView.vue') },
  { path: '/register', component: () => import('../views/front/RegisterView.vue') },
  { path: '/foods', component: () => import('../views/front/FoodListView.vue'), meta: { requiresAuth: true } },
  { path: '/foods/:id', component: () => import('../views/front/FoodDetailView.vue'), meta: { requiresAuth: true } },
  { path: '/foods/manage', component: () => import('../views/front/FoodManageView.vue'), meta: { requiresAuth: true } },
  { path: '/analysis', component: () => import('../views/front/AnalysisView.vue'), meta: { requiresAuth: true } },
  { path: '/history', component: () => import('../views/front/HistoryView.vue'), meta: { requiresAuth: true } },
  { path: '/diet', component: () => import('../views/front/DietRecordView.vue'), meta: { requiresAuth: true } },
  { path: '/health', component: () => import('../views/front/HealthView.vue'), meta: { requiresAuth: true } },
  { path: '/profile', component: () => import('../views/front/ProfileView.vue'), meta: { requiresAuth: true } },
  {
    path: '/admin',
    component: () => import('../views/admin/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../views/admin/DashboardView.vue') },
      { path: 'users', component: () => import('../views/admin/UsersView.vue') },
      { path: 'foods', component: () => import('../views/admin/FoodsView.vue') },
      { path: 'categories', component: () => import('../views/admin/CategoriesView.vue') },
      { path: 'assessments', component: () => import('../views/admin/AssessmentsView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _, next) => {
  const token = localStorage.getItem('token')
  const userStr = localStorage.getItem('user')
  const user = userStr ? JSON.parse(userStr) : null

  if (to.meta.requiresAuth && !token) {
    return next('/login')
  }
  if (to.meta.requiresAdmin && user?.user_type !== 'admin') {
    return next('/')
  }
  next()
})

export default router

