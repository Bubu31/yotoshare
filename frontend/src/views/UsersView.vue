<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import { useMessage } from '../composables/useMessage'
import AlertMessage from '../components/AlertMessage.vue'

const authStore = useAuthStore()
const users = ref([])
const roles = ref([])
const showForm = ref(false)
const editingUser = ref(null)
const form = ref({ username: '', password: '', role_id: null })
const { message, showMessage } = useMessage()

onMounted(async () => {
  await Promise.all([fetchUsers(), fetchRoles()])
})

async function fetchUsers() {
  try {
    const response = await api.get('/api/users')
    users.value = response.data
  } catch (e) {
    showMessage('error', 'Erreur lors du chargement des utilisateurs')
  }
}

async function fetchRoles() {
  try {
    const response = await api.get('/api/roles')
    roles.value = response.data
    // Set default role_id to first non-Admin role, or first role
    if (roles.value.length > 0 && !form.value.role_id) {
      const defaultRole = roles.value.find(r => r.name !== 'Admin') || roles.value[0]
      form.value.role_id = defaultRole.id
    }
  } catch (e) {
    // Roles might fail if user doesn't have roles:access permission, ignore silently
  }
}

function openCreateForm() {
  editingUser.value = null
  const defaultRole = roles.value.find(r => r.name !== 'Admin') || roles.value[0]
  form.value = { username: '', password: '', role_id: defaultRole?.id || null }
  showForm.value = true
}

function openEditForm(user) {
  editingUser.value = user
  form.value = { username: user.username, password: '', role_id: user.role_id }
  showForm.value = true
}

function cancelForm() {
  showForm.value = false
  editingUser.value = null
  const defaultRole = roles.value.find(r => r.name !== 'Admin') || roles.value[0]
  form.value = { username: '', password: '', role_id: defaultRole?.id || null }
}

async function submitForm() {
  try {
    if (editingUser.value) {
      const data = {}
      if (form.value.password) data.password = form.value.password
      if (form.value.role_id !== editingUser.value.role_id) data.role_id = form.value.role_id
      await api.put(`/api/users/${editingUser.value.id}`, data)
      showMessage('success', 'Utilisateur modifié')
    } else {
      if (!form.value.username || !form.value.password) {
        showMessage('error', 'Le nom d\'utilisateur et le mot de passe sont requis')
        return
      }
      await api.post('/api/users', {
        username: form.value.username,
        password: form.value.password,
        role_id: form.value.role_id,
      })
      showMessage('success', 'Utilisateur créé')
    }
    cancelForm()
    await fetchUsers()
  } catch (e) {
    showMessage('error', e.response?.data?.detail || 'Erreur')
  }
}

async function deleteUser(user) {
  if (!confirm(`Supprimer l'utilisateur "${user.username}" ?`)) return

  try {
    await api.delete(`/api/users/${user.id}`)
    showMessage('success', 'Utilisateur supprimé')
    await fetchUsers()
  } catch (e) {
    showMessage('error', e.response?.data?.detail || 'Erreur lors de la suppression')
  }
}

function getRoleBadgeClass(user) {
  if (user.role_name === 'Admin' || user.role === 'admin') {
    return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
  }
  return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
}

function getRoleLabel(user) {
  return user.role_name || (user.role === 'admin' ? 'Admin' : 'Éditeur')
}
</script>

<template>
  <div>
    <div class="flex items-center mb-8">
      <router-link to="/admin" class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mr-4">
        <i class="fas fa-arrow-left text-xl"></i>
      </router-link>
      <h1 class="text-3xl font-bold text-gray-800 dark:text-white">
        <i class="fas fa-users text-primary-600 mr-2"></i>
        Utilisateurs
      </h1>
    </div>

    <AlertMessage :message="message" />

    <div class="flex justify-end mb-4">
      <button
        @click="showForm ? cancelForm() : openCreateForm()"
        class="btn btn-secondary text-sm"
      >
        <i :class="showForm ? 'fas fa-times' : 'fas fa-plus'" class="mr-1"></i>
        {{ showForm ? 'Annuler' : 'Ajouter' }}
      </button>
    </div>

    <div v-if="showForm" class="card p-4 mb-6">
      <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-4">
        {{ editingUser ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur' }}
      </h3>
      <form @submit.prevent="submitForm" class="space-y-4">
        <div v-if="!editingUser">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom d'utilisateur</label>
          <input
            v-model="form.username"
            type="text"
            class="input"
            placeholder="Nom d'utilisateur"
            required
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ editingUser ? 'Nouveau mot de passe (laisser vide pour ne pas changer)' : 'Mot de passe' }}
          </label>
          <input
            v-model="form.password"
            type="password"
            class="input"
            placeholder="Mot de passe"
            :required="!editingUser"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Rôle</label>
          <select v-model="form.role_id" class="input">
            <option v-for="role in roles" :key="role.id" :value="role.id">
              {{ role.name }}
            </option>
          </select>
        </div>
        <div class="flex justify-end">
          <button type="submit" class="btn btn-primary">
            <i class="fas fa-check mr-1"></i>
            {{ editingUser ? 'Modifier' : 'Créer' }}
          </button>
        </div>
      </form>
    </div>

    <div class="space-y-2">
      <div
        v-for="user in users"
        :key="user.id"
        class="flex items-center justify-between bg-white dark:bg-gray-800 px-4 py-3 rounded-lg shadow-sm border dark:border-gray-700"
      >
        <div class="flex items-center gap-3">
          <i class="fas fa-user text-gray-400"></i>
          <span class="font-medium dark:text-white">{{ user.username }}</span>
          <span
            :class="[
              'px-2 py-0.5 text-xs rounded-full',
              getRoleBadgeClass(user)
            ]"
          >
            {{ getRoleLabel(user) }}
          </span>
        </div>
        <div class="flex gap-2">
          <button
            v-if="authStore.hasPermission('users', 'modify')"
            @click="openEditForm(user)"
            class="text-gray-400 hover:text-primary-600"
            title="Modifier"
          >
            <i class="fas fa-edit"></i>
          </button>
          <button
            v-if="authStore.hasPermission('users', 'delete')"
            @click="deleteUser(user)"
            class="text-gray-400 hover:text-red-600"
            title="Supprimer"
          >
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
      <div
        v-if="users.length === 0"
        class="text-gray-500 dark:text-gray-400 text-center py-8"
      >
        Aucun utilisateur
      </div>
    </div>
  </div>
</template>
