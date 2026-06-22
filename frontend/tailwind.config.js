/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './app/**/*.{vue,js,ts}',
    './app/app.vue',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Pretendard Variable"', 'Pretendard', 'system-ui', 'sans-serif'],
      },
      // ──────────────────────────────────────────────
      // 궁능 전용 팔레트 — 단청 와인 + 한지 크림 + 금색 포인트
      // 기존 rose-* 전체를 royal-*로 치환
      // ──────────────────────────────────────────────
      colors: {
        royal: {
          50:  '#FAF6EE',  // 한지 크림 (배경 연한 부분)
          100: '#F5EBD8',  // 베이지 (사용자 버블·카드 배경)
          200: '#E6DED0',  // 한지 라인 (테두리)
          300: '#D4B99A',  // 미색 (라이트 hover)
          400: '#A57458',  // 갈색 (보조)
          500: '#7A1F2B',  // 단청 와인 (주색) ★
          600: '#601421',  // 진와인 (hover/active)
          700: '#4A0F1A',  // 다크 와인
          800: '#2B2927',  // 먹색 (본문 텍스트)
          900: '#1A1818',  // 진먹
        },
        gold: {
          400: '#D4B872',
          500: '#B89E50',  // 황금 포인트 (강조)
          600: '#9C8340',
        },
      },
      backgroundImage: {
        // 한지 배경 그라디언트 — 은은한 크림톤
        'kossis-hero':
          'linear-gradient(135deg, #FAF6EE 0%, #FFFBEF 45%, #F0E6D2 100%)',
      },
      boxShadow: {
        // 와인 틴트 소프트 섀도
        soft: '0 4px 20px -6px rgba(122, 31, 43, 0.14)',
      },
    },
  },
  plugins: [],
}
