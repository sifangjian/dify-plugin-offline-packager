<script setup lang="ts">
import { ref } from "vue"
import { useRouter } from "vue-router"
import { useCartStore } from "@/stores/cart"
import { usePackagerStore } from "@/stores/packager"
import CartItem from "@/components/CartItem.vue"
import ArchitectureSelector from "@/components/ArchitectureSelector.vue"

const router = useRouter()
const cartStore = useCartStore()
const packagerStore = usePackagerStore()

const showArchSelector = ref(false)

function onStartPack(): void {
  if (cartStore.isEmpty) return
  showArchSelector.value = true
}

async function onArchConfirm(architecture: string): Promise<void> {
  showArchSelector.value = false
  packagerStore.setArchitecture(architecture)
  await packagerStore.startPackFromCart(cartStore.items)
  cartStore.closeSidebar()
  router.push({ name: "package" })
}

function appendPack(): void {
  packagerStore.appendPack(cartStore.items)
  cartStore.closeSidebar()
}

function goToPackage(): void {
  cartStore.closeSidebar()
  router.push({ name: "package" })
}
</script>

<template>
  <div data-testid="cart-sidebar">
    <div
      v-if="cartStore.isOpen"
      data-testid="sidebar-overlay"
      class="fixed inset-0 z-40 bg-black/50 transition-opacity"
      @click="cartStore.closeSidebar()"
    />
    <div
      data-testid="sidebar-panel"
      :class="[
        'fixed top-0 right-0 z-50 h-full w-96 max-w-full bg-white shadow-xl transition-transform duration-300 flex flex-col',
        cartStore.isOpen ? 'translate-x-0' : 'translate-x-full'
      ]"
    >
      <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h2
          data-testid="cart-title"
          class="text-lg font-semibold text-gray-900"
        >
          打包列表
          <span
            v-if="cartStore.itemCount > 0"
            class="text-gray-500 font-normal"
          >
            ({{ cartStore.itemCount }})
          </span>
        </h2>
        <div class="flex items-center gap-2">
          <button
            v-if="!cartStore.isEmpty"
            data-testid="clear-all-btn"
            class="text-sm text-gray-500 hover:text-red-600"
            @click="cartStore.clearAll()"
          >
            清空
          </button>
          <button
            data-testid="close-sidebar-btn"
            class="p-1 text-gray-400 hover:text-gray-600"
            @click="cartStore.closeSidebar()"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-4">
        <div
          v-if="cartStore.isEmpty"
          class="flex flex-col items-center justify-center h-full text-gray-400"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-12 h-12"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z"
            />
          </svg>
          <p class="mt-4 text-sm">
            打包列表为空，去搜索添加插件吧
          </p>
        </div>

        <div
          v-else
          class="flex flex-col gap-3"
        >
          <CartItem
            v-for="item in cartStore.items"
            :key="item.plugin_id"
            :plugin="item"
          />
        </div>
      </div>

      <div class="border-t border-gray-200 p-4 flex flex-col gap-2">
        <button
          v-if="!packagerStore.isPacking"
          data-testid="start-pack-btn"
          class="w-full py-2.5 rounded-lg text-white font-medium transition-colors"
          :class="cartStore.isEmpty
            ? 'bg-gray-300 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700'"
          :disabled="cartStore.isEmpty"
          @click="onStartPack"
        >
          开始打包
        </button>
        <template v-else>
          <button
            data-testid="append-pack-btn"
            class="w-full py-2.5 rounded-lg text-white font-medium transition-colors"
            :class="cartStore.isEmpty
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'"
            :disabled="cartStore.isEmpty"
            @click="appendPack"
          >
            追加到打包
          </button>
          <button
            data-testid="view-pack-btn"
            class="w-full py-2.5 rounded-lg text-blue-600 font-medium transition-colors border border-blue-300 hover:bg-blue-50"
            @click="goToPackage"
          >
            查看打包
          </button>
        </template>
      </div>
    </div>

    <ArchitectureSelector
      v-model="showArchSelector"
      :selected-architecture="packagerStore.selectedArchitecture"
      @confirm="onArchConfirm"
    />
  </div>
</template>
