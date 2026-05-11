<script setup lang="ts">
import { useCartStore } from "@/stores/cart"

const cartStore = useCartStore()
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-30 h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4">
    <h1 class="text-lg font-semibold text-gray-900">
      Dify Plugin Offline Packager
    </h1>
    <button
      class="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
      @click="cartStore.toggleSidebar()"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="w-6 h-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z"
        />
      </svg>
      <span
        v-if="cartStore.itemCount > 0"
        data-testid="cart-badge"
        class="absolute -top-1 -right-1 min-w-5 h-5 flex items-center justify-center rounded-full bg-blue-600 text-white text-xs font-medium px-1"
      >
        {{ cartStore.itemCount }}
      </span>
    </button>
  </header>
</template>
