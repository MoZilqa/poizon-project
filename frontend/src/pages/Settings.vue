<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, money, post, put } from '../api'

const cfg = ref(null)
const saved = ref(null)
const err = ref('')
const ok = ref('')
const busy = ref(false)
const example = ref(null)

const fields = [
  ['markup', 'Наценка', '%'],
  ['delivery_shoes', 'Доставка: обувь', '₽'],
  ['delivery_clothes', 'Доставка: одежда', '₽'],
  ['delivery_accessories', 'Доставка: аксессуары', '₽'],
]
const auto = computed(() => cfg.value.rate_auto === '1')
const dirty = computed(() => JSON.stringify(cfg.value) !== JSON.stringify(saved.value))
const synced = computed(() => cfg.value.rate_synced_at
  ? new Date(cfg.value.rate_synced_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
  : 'ещё не обновлялся')

function set(next) {
  cfg.value = next
  saved.value = { ...next }
  post('/admin/calc', { category: 'shoes', price_cny: 500 }).then((r) => { example.value = r }).catch(() => {})
}

async function run(fn, done) {
  busy.value = true
  err.value = ok.value = ''
  try { set(await fn()); ok.value = done } catch (e) { err.value = e.message } finally { busy.value = false }
}

const save = () => run(() => put('/admin/settings', cfg.value),
  'Сохранено. Новые цены действуют для новых заказов; уже оформленные не меняются.')
// режим курса сохраняется сразу, вместе с остальными несохранёнными правками
const toggle = (v) => { if (cfg.value.rate_auto !== v) { cfg.value.rate_auto = v; save() } }
const syncNow = () => run(() => post('/admin/rate/sync'), 'Курс обновлён с ЦБ')

onMounted(async () => set(await api('/admin/settings')))
</script>

<template>
  <div v-if="cfg" class="card">
    <div class="bar">
      <h2>Курс юаня</h2>
      <div class="seg">
        <button :class="{ on: auto }" :disabled="busy" @click="toggle('1')">Авто, ЦБ РФ</button>
        <button :class="{ on: !auto }" :disabled="busy" @click="toggle('0')">Вручную</button>
      </div>
    </div>

    <div v-if="auto" class="rate">
      <div><span class="mut small">Курс ЦБ</span><div class="big-num">{{ cfg.rate_cbr || '—' }}</div></div>
      <label>Надбавка к ЦБ, %
        <input v-model="cfg.rate_extra" inputmode="decimal" style="width:110px">
      </label>
      <div><span class="mut small">Курс для расчёта, ₽/¥</span><div class="big-num">{{ saved.rate }}</div></div>
      <button :disabled="busy || dirty" :title="dirty ? 'Сначала сохраните изменения' : ''" @click="syncNow">Обновить сейчас</button>
    </div>
    <div v-else class="rate">
      <label>Курс для расчёта, ₽ за ¥
        <input v-model="cfg.rate" inputmode="decimal" style="width:140px">
      </label>
    </div>
    <p v-if="auto" class="mut small">
      Обновляется автоматически раз в час · последнее обновление: {{ synced }}.
      Курс = ЦБ × (1 + надбавка).
    </p>
    <p v-if="auto && cfg.rate_error" class="err small">Последняя попытка не удалась: {{ cfg.rate_error }}. Пока действует прежний курс.</p>
  </div>

  <div v-if="cfg" class="card">
    <h2>Наценка и доставка</h2>
    <p class="mut small">Итог = цена (¥) × курс × (1 + наценка) + доставка по категории</p>
    <div class="fields">
      <label v-for="[key, text, unit] in fields" :key="key">{{ text }}, {{ unit }}
        <input v-model="cfg[key]" inputmode="decimal">
      </label>
    </div>
    <label class="mt">Реквизиты для оплаты (клиент увидит их в боте)
      <textarea v-model="cfg.requisites" rows="4"></textarea>
    </label>
    <p v-if="err" class="err">{{ err }}</p>
    <p v-if="ok" class="ok">{{ ok }}</p>
    <div class="row mt">
      <button class="main" :disabled="!dirty || busy" @click="save">Сохранить</button>
      <span v-if="example" class="mut small">Пример по сохранённым настройкам: обувь за 500 ¥ = {{ money(example.total) }} ₽</span>
    </div>
  </div>
</template>
