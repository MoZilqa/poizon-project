<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, dt, meta as loadMeta, money, post, put } from '../api'
import AuthImage from '../components/AuthImage.vue'
import StatusBadge from '../components/StatusBadge.vue'

const props = defineProps({ id: String })
const meta = ref({ statuses: {}, categories: {}, flow: [], branches: {} })
const o = ref(null)
const track = ref('')
const err = ref('')
const ok = ref('')
const busy = ref(false)

const ACTORS = { client: 'клиент', admin_bot: 'админ в боте', admin_site: 'админ на сайте' }
const isBranch = (s) => Object.values(meta.value.branches).includes(s)
const needsTrack = (s) => s === 'shipped_ru' && !track.value.trim()
const who = computed(() => o.value.user.username ? '@' + o.value.user.username : o.value.user.first_name || 'клиент')

async function run(fn, done) {
  busy.value = true
  err.value = ok.value = ''
  try {
    o.value = await fn()
    track.value = o.value.track_number || ''
    ok.value = done
  } catch (e) { err.value = e.message } finally { busy.value = false }
}

const load = () => run(() => api('/admin/orders/' + props.id))

function move(to) {
  const label = meta.value.statuses[to]
  if (isBranch(to) && !confirm(`Перевести заказ №${o.value.id} в «${label}»? Это необратимо.`)) return
  run(() => post(`/admin/orders/${props.id}/status`, { status: to, track_number: track.value || null }),
    `Статус: ${label}. Клиент получил уведомление в Telegram`)
}

const saveTrack = () => run(() => put(`/admin/orders/${props.id}/track`, { track_number: track.value }), 'Трек-номер сохранён')
const rejectReceipt = () => confirm('Отклонить чек? Клиента попросят прислать его заново.') &&
  run(() => post(`/admin/orders/${props.id}/reject-receipt`), 'Чек отклонён, клиент получил уведомление')

onMounted(async () => {
  meta.value = await loadMeta()
  await load()
})
</script>

<template>
  <RouterLink :to="{ name: 'orders' }" class="back">← Все заказы</RouterLink>
  <p v-if="err" class="err">{{ err }}</p>

  <template v-if="o">
    <div class="bar">
      <h1>Заказ №{{ o.id }}</h1>
      <StatusBadge :status="o.status" :label="meta.statuses[o.status]" />
    </div>
    <p v-if="ok" class="ok">{{ ok }}</p>

    <div class="grid">
      <div>
        <div class="card">
          <h2>Действия</h2>
          <p v-if="!o.allowed.length" class="mut">Заказ завершён</p>
          <template v-else>
            <div v-if="o.status === 'awaiting_payment' && o.has_receipt" class="note">
              Клиент прислал чек — проверьте поступление и подтвердите оплату.
            </div>
            <div class="row">
              <button v-for="to in o.allowed" :key="to" :disabled="busy || needsTrack(to)"
                      :class="isBranch(to) ? 'danger' : 'main'" @click="move(to)">
                {{ to === 'paid' && o.has_receipt ? 'Подтвердить оплату' : (isBranch(to) ? '' : '→ ') + meta.statuses[to] }}
              </button>
              <button v-if="o.status === 'awaiting_payment' && o.has_receipt" :disabled="busy" @click="rejectReceipt">
                Отклонить чек
              </button>
            </div>
          </template>
          <label class="mt">Трек-номер <span v-if="o.allowed.includes('shipped_ru')" class="mut">— обязателен для «Отправлен в РФ»</span>
            <div class="row">
              <input v-model="track" maxlength="64" placeholder="RU123456789CN">
              <button :disabled="busy || track === (o.track_number || '')" @click="saveTrack">Сохранить</button>
            </div>
          </label>
        </div>

        <div class="card">
          <h2>Заказ</h2>
          <dl>
            <dt>Товар</dt><dd><a :href="o.url" target="_blank" rel="noopener">{{ o.url }}</a></dd>
            <dt>Категория</dt><dd>{{ meta.categories[o.category] }}</dd>
            <dt>Размер</dt><dd>{{ o.size }}</dd>
            <dt>Цена</dt><dd>{{ o.price_cny }} ¥ → <b>{{ money(o.total_rub) }} ₽</b></dd>
            <dt>Клиент</dt>
            <dd>
              <a v-if="o.user.username" :href="'https://t.me/' + o.user.username" target="_blank">{{ who }}</a>
              <span v-else>{{ who }}</span>
              <span class="mut"> · ID {{ o.user.tg_id }}</span>
            </dd>
            <dt>Получатель</dt><dd>{{ o.recipient }}</dd>
            <dt>Создан</dt><dd>{{ dt(o.created_at) }}</dd>
          </dl>
        </div>
      </div>

      <div>
        <div class="card">
          <h2>Скриншот</h2>
          <AuthImage :src="`/admin/orders/${o.id}/files/screenshot`" alt="Скриншот товара" />
        </div>
        <div v-if="o.has_receipt" class="card">
          <h2>Чек</h2>
          <AuthImage :src="`/admin/orders/${o.id}/files/receipt`" alt="Чек" />
        </div>
        <div class="card">
          <h2>История</h2>
          <ol class="timeline">
            <li v-for="(h, i) in o.history" :key="i">
              <StatusBadge :status="h.status" :label="meta.statuses[h.status]" />
              <span class="mut small">{{ dt(h.created_at) }} · {{ ACTORS[h.actor] || h.actor }}</span>
            </li>
          </ol>
        </div>
      </div>
    </div>
  </template>
</template>
