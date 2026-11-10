<script setup>
defineProps({ status: String, label: String })
</script>

<template>
  <span class="badge" :class="'s-' + status">{{ label || status }}</span>
</template>
