<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth, post } from '../api'

const route = useRoute()
const router = useRouter()
const password = ref('')
const err = ref('')
const busy = ref(false)

async function login() {
  busy.value = true
  err.value = ''
  try {
    auth.token = (await post('/auth/login', { password: password.value })).token
    router.replace(route.query.next || { name: 'orders' })
  } catch (e) { err.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <form class="card narrow" @submit.prevent="login">
    <h2>Вход для администратора</h2>
    <label>Пароль
      <input v-model="password" type="password" autocomplete="current-password" autofocus>
    </label>
    <p v-if="err" class="err">{{ err }}</p>
    <button class="main" :disabled="busy || !password">Войти</button>
  </form>
</template>
