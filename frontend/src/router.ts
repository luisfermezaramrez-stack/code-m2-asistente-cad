import { createRouter, createWebHistory, type RouterHistory, type RouteRecordRaw } from 'vue-router'
import HistoryDetailView from './views/HistoryDetailView.vue'
import HistoryView from './views/HistoryView.vue'
import NewRequestView from './views/NewRequestView.vue'
import NotFoundView from './views/NotFoundView.vue'
import SettingsView from './views/SettingsView.vue'

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: { name: 'nueva-solicitud' } },
  { path: '/nueva-solicitud', name: 'nueva-solicitud', component: NewRequestView },
  { path: '/historial', name: 'historial', component: HistoryView },
  // Reapertura de una solicitud anterior (HU-37, RF-3): URL propia y recargable.
  { path: '/historial/:identificador', name: 'historial-solicitud', component: HistoryDetailView },
  { path: '/ajustes', name: 'ajustes', component: SettingsView },
  { path: '/:pathMatch(.*)*', name: 'sin-ruta', component: NotFoundView },
]

export function createAppRouter(history: RouterHistory = createWebHistory()) {
  return createRouter({ history, routes })
}
