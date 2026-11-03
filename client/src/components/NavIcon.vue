<script setup>
// Simple 24x24 stroke icons (currentColor) for the sidebar navigation.
defineProps({
  name: { type: String, required: true }
})
</script>

<template>
  <svg
    class="nav-icon"
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <template v-if="name === 'overview'">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </template>
    <template v-else-if="name === 'inventory'">
      <path d="M21 8 12 3 3 8v8l9 5 9-5V8Z" />
      <path d="m3 8 9 5 9-5" />
      <path d="M12 13v8" />
    </template>
    <template v-else-if="name === 'orders'">
      <path d="M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1Z" />
      <path d="M8 5H6a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2" />
      <path d="M9 12h6M9 16h6" />
    </template>
    <template v-else-if="name === 'finance'">
      <rect x="2.5" y="6" width="19" height="12" rx="2" />
      <circle cx="12" cy="12" r="2.5" />
      <path d="M6 9.5v.01M18 14.5v.01" />
    </template>
    <template v-else-if="name === 'demand'">
      <path d="M3 3v18h18" />
      <path d="m7 15 4-4 3 3 5-6" />
    </template>
    <template v-else-if="name === 'restocking'">
      <path d="M20 12a8 8 0 0 1-13.7 5.6L4 15.5" />
      <path d="M4 12a8 8 0 0 1 13.7-5.6L20 8.5" />
      <path d="M4 20v-4.5h4.5M20 4v4.5h-4.5" />
    </template>
    <template v-else-if="name === 'reports'">
      <path d="M14 3H7a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7l-4-4Z" />
      <path d="M14 3v4h4" />
      <path d="M9 17v-3M12 17v-5M15 17v-2" />
    </template>
    <template v-else-if="name === 'chevrons-left'">
      <path d="m11 17-5-5 5-5M18 17l-5-5 5-5" />
    </template>
    <template v-else-if="name === 'chevrons-right'">
      <path d="m13 17 5-5-5-5M6 17l5-5-5-5" />
    </template>
  </svg>
</template>
