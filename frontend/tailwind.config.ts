import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}", // Сканирует все файлы в src
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
export default config;