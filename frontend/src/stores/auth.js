import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const role = ref(localStorage.getItem('role') || null)
  const roleId = ref(JSON.parse(localStorage.getItem('roleId') || 'null'))
  const roleName = ref(localStorage.getItem('roleName') || null)
  const permissions = ref(JSON.parse(localStorage.getItem('permissions') || '{}'))

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => roleName.value === 'Admin' || role.value === 'admin')

  function hasPermission(scope, action) {
    if (roleName.value === 'Admin' || role.value === 'admin') return true
    return permissions.value?.[scope]?.[action] ?? false
  }

  async function login(username, password) {
    const response = await api.post('/api/auth/login', { username, password })
    token.value = response.data.access_token
    role.value = response.data.role
    roleId.value = response.data.role_id
    roleName.value = response.data.role_name
    permissions.value = response.data.permissions || {}

    localStorage.setItem('token', token.value)
    localStorage.setItem('role', role.value)
    localStorage.setItem('roleId', JSON.stringify(roleId.value))
    localStorage.setItem('roleName', roleName.value)
    localStorage.setItem('permissions', JSON.stringify(permissions.value))

    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    return response.data
  }

  function logout() {
    token.value = null
    role.value = null
    roleId.value = null
    roleName.value = null
    permissions.value = {}

    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('roleId')
    localStorage.removeItem('roleName')
    localStorage.removeItem('permissions')

    delete api.defaults.headers.common['Authorization']
  }

  function initAuth() {
    if (token.value) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    }
  }

  initAuth()

  return {
    token,
    role,
    roleId,
    roleName,
    permissions,
    isAuthenticated,
    isAdmin,
    hasPermission,
    login,
    logout,
    initAuth,
  }
})
