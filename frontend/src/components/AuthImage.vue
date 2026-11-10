<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { blobUrl } from '../api'

// Картинка из админ-API (с авторизацией). Если это не картинка (PDF-чек) — показываем ссылку
const props = defineProps({ src: String, alt: String })
const url = ref('')
const isImage = ref(true)
const err = ref('')

watch(() => props.src, async (src) => {
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''
  err.value = ''
  try {
    url.value = await blobUrl(src)
    const type = (await fetch(url.value).then((r) => r.blob())).type
    isImage.value = type.startsWith('image/')
  } catch (e) { err.value = e.message }
}, { immediate: true })

onBeforeUnmount(() => url.value && URL.revokeObjectURL(url.value))
</script>

<template>
  <p v-if="err" class="mut small">{{ err }}</p>
  <a v-else-if="url" :href="url" target="_blank" class="shot">
    <img v-if="isImage" :src="url" :alt="alt">
    <span v-else>Открыть файл</span>
  </a>
  <div v-else class="shot skeleton"></div>
</template>
