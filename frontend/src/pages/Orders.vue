<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, dt, meta as loadMeta, money } from '../api'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const meta = ref({ statuses: {}, categories: {} })
const stats = ref(null)
const page = ref({ items: [], total: 0 })
const err = ref('')
const loading = ref(false)
const PAGE = 30

// фильтры живут в URL, чтобы ссылку на выборку можно было открыть заново
const status = computed(() => route.query.status ?? 'active')
const q = ref(route.query.q || '')
const offset = computed(() => Number(route.query.offset || 0))

const chips = computed(() => {
  const c = stats.value?.counts || {}
  return [
    ['active', 'В работе', stats.value?.active],
    ['receipt', 'Чеки на проверке', null],
    ...Object.entries(meta.value.statuses).map(([k, name]) => [k, name, c[k]]),
    ['', 'Все', null],
  ]
})

async function load() {
  loading.value = true
  err.value = ''
  try {
    const params = new URLSearchParams({ limit: PAGE, offset: offset.value })
    if (status.value) params.set('status', status.value)
    if (route.query.q) params.set('q', route.query.q)
    ;[page.value, stats.value] = await Promise.all([api('/admin/orders?' + params), api('/admin/stats')])
  } catch (e) { err.value = e.message } finally { loading.value = false }
}

const go = (patch) => router.replace({ query: { ...route.query, offset: undefined, ...patch } })
let t
watch(q, (v) => { clearTimeout(t); t = setTimeout(() => go({ q: v || undefined }), 300) })
watch(() => route.query, load)

// новые заказы из бота появляются без перезагрузки
let timer
onMounted(async () => {
  meta.value = await loadMeta()
  await load()
  timer = setInterval(() => document.visibilityState === 'visible' && load(), 30000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div v-if="stats" class="tiles">
    <div class="tile"><span>В работе</span><b>{{ stats.active }}</b></div>
    <div class="tile"><span>Новые</span><b>{{ stats.counts.new }}</b></div>
    <div class="tile"><span>Ждут оплаты</span><b>{{ stats.counts.awaiting_payment }}</b></div>
    <div class="tile"><span>Оплачено, ₽</span><b>{{ money(stats.revenue) }}</b></div>
    <div class="tile"><span>Клиентов</span><b>{{ stats.clients }}</b></div>
  </div>

  <div class="card">
    <div class="bar">
      <h2>Заказы <span class="mut">{{ page.total }}</span></h2>
      <input v-model="q" class="search" placeholder="Поиск: №, @username, ФИО, трек">
    </div>
    <div class="chips">
      <button v-for="[key, name, n] in chips" :key="key" :class="{ on: status === key }"
              @click="go({ status: key })">{{ name }}<i v-if="n">{{ n }}</i></button>
    </div>

    <p v-if="err" class="err">{{ err }}</p>
    <p v-else-if="!page.items.length && !loading" class="mut empty">Заказов нет</p>
    <div v-else class="scroll">
      <table class="orders">
        <thead>
          <tr><th>№</th><th>Создан</th><th>Клиент</th><th>Товар</th><th class="r">Итого</th><th>Статус</th></tr>
        </thead>
        <tbody>
          <tr v-for="o in page.items" :key="o.id" @click="router.push({ name: 'order', params: { id: o.id } })">
            <td><b>{{ o.id }}</b></td>
            <td class="mut">{{ dt(o.created_at) }}</td>
            <td>{{ o.user.username ? '@' + o.user.username : o.user.first_name }}
              <div class="mut small">{{ o.recipient.split(',')[0] }}</div></td>
            <td>{{ meta.categories[o.category] }}, {{ o.size }}<div class="mut small">{{ o.price_cny }} ¥</div></td>
            <td class="r nowrap">{{ money(o.total_rub) }} ₽</td>
            <td>
              <StatusBadge :status="o.status" :label="meta.statuses[o.status]" />
              <span v-if="o.has_receipt && o.status === 'awaiting_payment'" class="badge s-receipt">чек</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="page.total > PAGE" class="pager">
      <button :disabled="offset === 0" @click="go({ offset: offset - PAGE || undefined })">← Назад</button>
      <span class="mut">{{ offset + 1 }}–{{ Math.min(offset + PAGE, page.total) }} из {{ page.total }}</span>
      <button :disabled="offset + PAGE >= page.total" @click="go({ offset: offset + PAGE })">Дальше →</button>
    </div>
  </div>
</template>
