<script setup lang="ts">
import { RouterView } from "vue-router"
import NavBar from "@/components/NavBar.vue"
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <NavBar />
    <main class="pt-14">
      <RouterView />
    </main>
  </div>
</template>
