<script setup lang="ts">
import { RouterView } from "vue-router"
import NavBar from "@/components/NavBar.vue"
import CartSidebar from "@/components/CartSidebar.vue"
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <NavBar />
    <main class="pt-14">
      <RouterView />
    </main>
    <CartSidebar />
  </div>
</template>
