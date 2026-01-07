<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue';

// 初始化主题
onMounted(() => {
  const savedTheme = localStorage.getItem('theme') || 'dark';
  applyTheme(savedTheme);
  
  // 监听系统主题变化
  if (savedTheme === 'auto') {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      const currentTheme = localStorage.getItem('theme');
      if (currentTheme === 'auto') {
        applyTheme('auto');
      }
    });
  }
});

const applyTheme = (theme) => {
  const root = document.documentElement;
  
  if (theme === 'auto') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
  } else {
    root.setAttribute('data-theme', theme);
  }
};
</script>

<style scoped>
</style>
