import axios from 'axios';

// Адрес твоего Python-сервера
// Использует localhost для разработки, Render URL для production
const getApiUrl = () => {
  // Если работаем локально (на вашем компьютере)
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000/api';
  }
  // Для production на Vercel используем Render URL
  return 'https://xtrend-app.onrender.com/api';
};

const API_URL = getApiUrl();

// Для отладки: показываем какой URL используется
if (typeof window !== 'undefined') {
  console.log('🔗 API URL:', API_URL);
  console.log('📍 Hostname:', window.location.hostname);
}

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Улучшенная обработка ошибок
    if (error.response) {
      // Сервер ответил с кодом ошибки
      console.error('API Error Response:', {
        status: error.response.status,
        data: error.response.data,
        url: error.config?.url
      });
    } else if (error.request) {
      // Запрос был отправлен, но ответа не получено
      console.error('API Error: No response from server', {
        url: error.config?.url,
        message: 'Backend server may be down or unreachable'
      });
    } else {
      // Ошибка при настройке запроса
      console.error('API Error:', error.message);
    }
    return Promise.reject(error);
  }
);