export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  ssr: false,
  srcDir: 'app/',
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss'],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      apiBase: '',
    },
  },
  nitro: {
    // dev 모드: Vite dev 서버가 /api 요청을 로컬 백엔드로 프록시
    devProxy: {
      '/api': {
        target: 'http://127.0.0.1:8002/api',
        changeOrigin: true,
      },
    },
    // prod(nuxt generate → static) 단계에선 런타임 프록시 없음. nginx 게이트웨이가 /api 프록시 담당.
    routeRules: {
      '/api/**': { proxy: 'http://backend:8002/api/**' },
    },
  },
  app: {
    buildAssetsDir: '/_nuxt-panel/',
    head: {
      title: '궁능유적본부 AI',
      link: [
        {
          rel: 'stylesheet',
          href: 'https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css',
        },
      ],
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
    },
  },
  tailwindcss: {
    cssPath: '~/assets/css/main.css',
  },
  // nuxt generate 정적 빌드 후 dist로 복사됨
})
