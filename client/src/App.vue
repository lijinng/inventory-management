<template>
  <div class="app" :class="{ 'sidebar-collapsed': collapsed }">
    <aside class="sidebar">
      <button
        type="button"
        class="sidebar-toggle"
        :aria-expanded="String(!collapsed)"
        aria-controls="sidebar-nav"
        :aria-label="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        :title="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        @click="toggleSidebar"
      >
        <NavIcon :name="collapsed ? 'chevrons-right' : 'chevrons-left'" />
        <span class="nav-label">{{ collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar') }}</span>
      </button>
      <nav id="sidebar-nav" class="nav-tabs" :aria-label="t('nav.mainNavigation')">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :class="{ active: $route.path === item.to }"
          :aria-label="item.label"
          :title="collapsed ? item.label : null"
        >
          <NavIcon :name="item.icon" />
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <div class="app-body">
    <header class="top-nav">
      <div class="nav-container">
        <div class="logo">
          <h1>{{ t('nav.companyName') }}</h1>
          <span class="subtitle">{{ t('nav.subtitle') }}</span>
        </div>
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </header>
    <FilterBar />
    <main class="main-content">
      <router-view />
    </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import NavIcon from './components/NavIcon.vue'

const SIDEBAR_KEY = 'sidebarCollapsed'
const WIDE_QUERY = '(min-width: 1024px)'

// Read the persisted choice; anything other than 'true'/'false' (or blocked storage) means "no preference".
const readStoredCollapsed = () => {
  try {
    const v = localStorage.getItem(SIDEBAR_KEY)
    return v === 'true' ? true : v === 'false' ? false : null
  } catch {
    return null
  }
}

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher,
    NavIcon
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    const navItems = computed(() => [
      { to: '/', icon: 'overview', label: t('nav.overview') },
      { to: '/inventory', icon: 'inventory', label: t('nav.inventory') },
      { to: '/orders', icon: 'orders', label: t('nav.orders') },
      { to: '/spending', icon: 'finance', label: t('nav.finance') },
      { to: '/demand', icon: 'demand', label: t('nav.demandForecast') },
      { to: '/restocking', icon: 'restocking', label: t('nav.restocking') },
      { to: '/reports', icon: 'reports', label: t('nav.reports') }
    ])

    // Sidebar: with no stored user choice, collapse below 1024px and expand above.
    // Once the user toggles, their choice wins over the breakpoint.
    const mq = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(WIDE_QUERY) : null
    const isWide = ref(mq ? mq.matches : true)
    const userCollapsed = ref(readStoredCollapsed())
    const collapsed = computed(() => userCollapsed.value ?? !isWide.value)
    const onMqChange = (e) => { isWide.value = e.matches }
    const toggleSidebar = () => {
      userCollapsed.value = !collapsed.value
      try {
        localStorage.setItem(SIDEBAR_KEY, String(userCollapsed.value))
      } catch { /* storage unavailable; choice lasts for this session only */ }
    }
    mq && mq.addEventListener('change', onMqChange)
    onBeforeUnmount(() => mq && mq.removeEventListener('change', onMqChange))

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      navItems,
      collapsed,
      toggleSidebar,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  flex-direction: row;
  min-height: 100vh;
  --sidebar-width: 220px;
}

.app.sidebar-collapsed {
  --sidebar-width: 64px;
}

/* Right-hand column; min-width: 0 lets wide tables scroll instead of overflowing the flex row */
.app-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  height: 100vh;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  padding: 0.75rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-x: hidden;
  overflow-y: auto;
  transition: width 0.2s ease;
  z-index: 110;
}

.sidebar-toggle,
.nav-tabs a {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  height: 40px;
  padding: 0 0.75rem;
  color: #64748b;
  text-decoration: none;
  font-family: inherit;
  font-weight: 500;
  font-size: 0.938rem;
  white-space: nowrap;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.sidebar-toggle {
  border-bottom: 1px solid transparent;
}

.sidebar-toggle:hover,
.nav-tabs a:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.sidebar-toggle:focus-visible,
.nav-tabs a:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.nav-icon {
  flex-shrink: 0;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Icons-only mode: hide text visually (aria-label on each link keeps the accessible name) */
.sidebar-collapsed .nav-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
}

.sidebar-collapsed .sidebar-toggle,
.sidebar-collapsed .nav-tabs a {
  justify-content: center;
  padding: 0;
}

.nav-tabs {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-tabs a.active {
  color: #2563eb;
  background: #eff6ff;
}

.top-nav {
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 2rem;
  height: 70px;
}

.nav-container > .language-switcher {
  margin-left: auto;
  margin-right: 1rem;
}

.logo {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  min-width: 0;
}

.logo h1 {
  font-size: 1.375rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
  white-space: nowrap;
}

.subtitle {
  font-size: 0.813rem;
  color: #64748b;
  font-weight: 400;
  padding-left: 0.75rem;
  border-left: 1px solid #e2e8f0;
}

/* Narrow viewports: drop the subtitle and tighten padding so the header fits next to the sidebar */
@media (max-width: 1023px) {
  .subtitle {
    display: none;
  }

  .nav-container {
    padding: 0 1rem;
  }

  .main-content {
    padding: 1rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar {
    transition: none;
  }
}

.main-content {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 2rem;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.375rem;
  letter-spacing: -0.025em;
}

.page-header p {
  color: #64748b;
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: white;
  padding: 1.25rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

.card {
  background: white;
  border-radius: 10px;
  padding: 1.25rem;
  border: 1px solid #e2e8f0;
  margin-bottom: 1.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-weight: 600;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: #f8fafc;
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
