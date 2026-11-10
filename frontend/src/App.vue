<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth } from './api'

const route = useRoute()
const router = useRouter()
const authed = computed(() => route.name !== 'login')

function logout() {
  auth.token = ''
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="top">
    <RouterLink to="/" class="logo">Poizon<span>·</span>админка</RouterLink>
    <nav v-if="authed">
      <RouterLink :to="{ name: 'orders' }">Заказы</RouterLink>
      <RouterLink :to="{ name: 'settings' }">Настройки</RouterLink>
      <button class="link" @click="logout">Выйти</button>
    </nav>
  </header>
  <main>
    <RouterView />
  </main>
</template>
