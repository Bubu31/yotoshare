<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import { useMessage } from '../composables/useMessage'
import AlertMessage from '../components/AlertMessage.vue'

const authStore = useAuthStore()
const { message, showMessage } = useMessage()

const roles = ref([])
const showForm = ref(false)
const editingRole = ref(null)

const SCOPES = [
  { key: 'archives', label: 'Archives' },
  { key: 'categories', label: 'Catégories' },
  { key: 'ages', label: 'Âges' },
  { key: 'users', label: 'Utilisateurs' },
  { key: 'roles', label: 'Rôles' },
  { key: 'visuals', label: 'Visuels' },
  { key: 'visual_themes', label: 'Thèmes visuels' },
  { key: 'discord', label: 'Discord' },
  { key: 'packs', label: 'Packs' },
]

const ACTIONS = [
  { key: 'access', label: 'Accéder' },
  { key: 'modify', label: 'Modifier' },
  { key: 'delete', label: 'Supprimer' },
]

function emptyPermissions() {
  const perms = {}
  SCOPES.forEach(s => {
    perms[s.key] = { access: false, modify: false, delete: false }
  })
  return perms
}

const form = ref({
  name: '',
  description: '',
  permissions: emptyPermissions(),
})

onMounted(async () => {
  await fetchRoles()
})

async function fetchRoles() {
  try {
    const response = await api.get('/api/roles')
    roles.value = response.data
  } catch (e) {
    showMessage('error', 'Erreur lors du chargement des rôles')
  }
}

function openCreateForm() {
  editingRole.value = null
  form.value = {
    name: '',
    description: '',
    permissions: emptyPermissions(),
  }
  showForm.value = true
}

function openEditForm(role) {
  editingRole.value = role
  // Deep clone permissions, fill missing scopes
  const perms = emptyPermissions()
  if (role.permissions) {
    Object.keys(role.permissions).forEach(scope => {
      if (perms[scope]) {
        perms[scope] = { ...perms[scope], ...role.permissions[scope] }
      }
    })
  }
  form.value = {
    name: role.name,
    description: role.description || '',
    permissions: perms,
  }
  showForm.value = true
}

function cancelForm() {
  showForm.value = false
  editingRole.value = null
}

async function submitForm() {
  try {
    if (editingRole.value) {
      const data = {
        description: form.value.description,
        permissions: form.value.permissions,
      }
      // Only send name if changed and not system
      if (!editingRole.value.is_system && form.value.name !== editingRole.value.name) {
        data.name = form.value.name
      }
      await api.put(`/api/roles/${editingRole.value.id}`, data)
      showMessage('success', 'Rôle modifié')
    } else {
      if (!form.value.name) {
        showMessage('error', 'Le nom est requis')
        return
      }
      await api.post('/api/roles', {
        name: form.value.name,
        description: form.value.description,
        permissions: form.value.permissions,
      })
      showMessage('success', 'Rôle créé')
    }
    cancelForm()
    await fetchRoles()
  } catch (e) {
    showMessage('error', e.response?.data?.detail || 'Erreur')
  }
}

async function deleteRole(role) {
  if (!confirm(`Supprimer le rôle "${role.name}" ?`)) return

  try {
    await api.delete(`/api/roles/${role.id}`)
    showMessage('success', 'Rôle supprimé')
    await fetchRoles()
  } catch (e) {
    showMessage('error', e.response?.data?.detail || 'Erreur lors de la suppression')
  }
}

function isAdminRole(role) {
  return role.name === 'Admin'
}
</script>

<template>
  <div>
    <div class="flex items-center mb-8">
      <router-link to="/admin" class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mr-4">
        <i class="fas fa-arrow-left text-xl"></i>
      </router-link>
      <h1 class="text-3xl font-bold text-gray-800 dark:text-white">
        <i class="fas fa-shield-alt text-primary-600 mr-2"></i>
        Rôles &amp; Permissions
      </h1>
    </div>

    <AlertMessage :message="message" />

    <div v-if="authStore.hasPermission('roles', 'modify')" class="flex justify-end mb-4">
      <button
        @click="showForm ? cancelForm() : openCreateForm()"
        class="btn btn-secondary text-sm"
      >
        <i :class="showForm ? 'fas fa-times' : 'fas fa-plus'" class="mr-1"></i>
        {{ showForm ? 'Annuler' : 'Nouveau rôle' }}
      </button>
    </div>

    <!-- Create/Edit Form -->
    <div v-if="showForm" class="card p-6 mb-6">
      <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-4">
        {{ editingRole ? `Modifier le rôle "${editingRole.name}"` : 'Nouveau rôle' }}
      </h3>
      <form @submit.prevent="submitForm" class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom</label>
            <input
              v-model="form.name"
              type="text"
              class="input"
              placeholder="Ex: Modérateur"
              :disabled="editingRole?.is_system"
              required
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
            <input
              v-model="form.description"
              type="text"
              class="input"
              placeholder="Description du rôle"
            />
          </div>
        </div>

        <!-- Permissions Matrix -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Permissions</label>
          <div class="overflow-x-auto">
            <table class="w-full border-collapse">
              <thead>
                <tr class="border-b dark:border-gray-700">
                  <th class="text-left py-2 px-3 text-sm font-medium text-gray-700 dark:text-gray-300">Scope</th>
                  <th
                    v-for="action in ACTIONS"
                    :key="action.key"
                    class="text-center py-2 px-3 text-sm font-medium text-gray-700 dark:text-gray-300"
                  >
                    {{ action.label }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="scope in SCOPES"
                  :key="scope.key"
                  class="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <td class="py-2 px-3 text-sm text-gray-800 dark:text-gray-200">{{ scope.label }}</td>
                  <td
                    v-for="action in ACTIONS"
                    :key="action.key"
                    class="text-center py-2 px-3"
                  >
                    <input
                      type="checkbox"
                      v-model="form.permissions[scope.key][action.key]"
                      :disabled="isAdminRole(editingRole || {})"
                      class="w-4 h-4 text-primary-600 rounded focus:ring-primary-500 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="flex justify-end gap-2">
          <button type="button" @click="cancelForm" class="btn btn-secondary">
            Annuler
          </button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="isAdminRole(editingRole || {})"
          >
            <i class="fas fa-check mr-1"></i>
            {{ editingRole ? 'Modifier' : 'Créer' }}
          </button>
        </div>
      </form>
    </div>

    <!-- Roles List -->
    <div class="space-y-3">
      <div
        v-for="role in roles"
        :key="role.id"
        class="card p-4"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <i v-if="role.is_system" class="fas fa-lock text-amber-500" title="Rôle système"></i>
            <i v-else class="fas fa-shield-alt text-primary-500"></i>
            <div>
              <span class="font-semibold text-gray-800 dark:text-white">{{ role.name }}</span>
              <span v-if="role.is_system" class="ml-2 px-2 py-0.5 text-xs rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                Système
              </span>
            </div>
            <span v-if="role.description" class="text-sm text-gray-500 dark:text-gray-400">
              &mdash; {{ role.description }}
            </span>
          </div>
          <div class="flex gap-2">
            <button
              v-if="authStore.hasPermission('roles', 'modify')"
              @click="openEditForm(role)"
              class="text-gray-400 hover:text-primary-600"
              title="Modifier"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button
              v-if="authStore.hasPermission('roles', 'delete') && !role.is_system"
              @click="deleteRole(role)"
              class="text-gray-400 hover:text-red-600"
              title="Supprimer"
            >
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>

        <!-- Compact permissions display -->
        <div class="overflow-x-auto">
          <table class="w-full text-sm border-collapse">
            <thead>
              <tr class="border-b dark:border-gray-700">
                <th class="text-left py-1 px-2 text-xs font-medium text-gray-500 dark:text-gray-400">Scope</th>
                <th
                  v-for="action in ACTIONS"
                  :key="action.key"
                  class="text-center py-1 px-2 text-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  {{ action.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="scope in SCOPES"
                :key="scope.key"
                class="border-b dark:border-gray-700/50"
              >
                <td class="py-1 px-2 text-gray-600 dark:text-gray-300">{{ scope.label }}</td>
                <td
                  v-for="action in ACTIONS"
                  :key="action.key"
                  class="text-center py-1 px-2"
                >
                  <i
                    :class="[
                      role.permissions?.[scope.key]?.[action.key]
                        ? 'fas fa-check text-green-500'
                        : 'fas fa-times text-gray-300 dark:text-gray-600'
                    ]"
                  ></i>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div
        v-if="roles.length === 0"
        class="text-center py-8 text-gray-500 dark:text-gray-400"
      >
        Aucun rôle
      </div>
    </div>
  </div>
</template>
