'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '../lib/api/client';
import { 
  Search, Loader2, TrendingUp, Users, Play, ImageOff, 
  Zap, Activity, Layers, RefreshCw, BarChart3, Trophy, Star, Clock, User 
} from 'lucide-react';

type SearchMode = 'trends' | 'profiles' | 'deep';
type DeepSubMode = 'keywords' | 'username';

const SafeImage = ({ src, alt, className }: { src: string | null | undefined, alt: string, className?: string }) => {
  const [hasError, setHasError] = useState(false);
  
  // Функция для получения базового URL бэкенда
  const getBackendUrl = () => {
    if (typeof window === 'undefined') return 'https://xtrend-app.onrender.com';
    // Если работаем локально
    if (window.location.hostname === 'localhost') {
      return 'http://localhost:8000';
    }
    // Для production используем Render URL
    return 'https://xtrend-app.onrender.com';
  };

  // Используем прокси для TikTok изображений
  const getImageUrl = (url: string | null | undefined) => {
    if (!url) return null;
    // Проверяем все варианты TikTok CDN доменов (любой домен с tiktokcdn)
    if (url.includes('tiktokcdn')) {
      // Используем прокси через backend
      const backendUrl = getBackendUrl();
      return `${backendUrl}/api/images/proxy?url=${encodeURIComponent(url)}`;
    }
    return url;
  };
  
  const imageUrl = getImageUrl(src);
  
  if (!imageUrl || hasError) return (
    <div className={`flex items-center justify-center bg-zinc-800 text-zinc-600 ${className}`}>
      <ImageOff className="w-6 h-6 opacity-20" />
    </div>
  );
  
  return (
    <img 
      src={imageUrl} 
      alt={alt} 
      className={className} 
      referrerPolicy="no-referrer" 
      loading="lazy" 
      onError={() => setHasError(true)}
    />
  );
};

export default function Home() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<SearchMode>('trends');
  const [error, setError] = useState('');
  const [deepMode, setDeepMode] = useState<DeepSubMode>('keywords');
  const [rescanHours, setRescanHours] = useState<number>(24);
  const [videoList, setVideoList] = useState<any[]>([]);
  const [currentReport, setCurrentReport] = useState<any>(null);
  const [sessionHistory, setSessionHistory] = useState<any[]>([]);

  // --- ✅ ФУНКЦИЯ МОНИТОРИНГА: ПОЛУЧЕНИЕ ОБНОВЛЕНИЙ ИЗ БУФЕРА БД ---
  const fetchFromDB = async (silent = false) => {
    if (!query.trim() || activeTab === 'profiles' || videoList.length === 0) return;
    if (!silent) setLoading(true);
    try {
      // Запрашиваем результаты сверки (Точка Б)
      const response = await apiClient.get(`/trends/results`, { 
        params: { 
          keyword: query,
          mode: activeTab === 'deep' ? deepMode : 'keywords'
        } 
      });

      if (response.data.items && response.data.items.length > 0) {
        const updatedFromDB = response.data.items;
        
        setVideoList(prevList => {
          return prevList.map(oldItem => {
            // Ищем это же видео в ответе от БД
            const freshItem = updatedFromDB.find((ni: any) => ni.url === oldItem.url);
            // Если в БД есть обновление с UTS (Точка Б), заменяем старые данные новыми
            if (freshItem && freshItem.last_scanned_at) {
              return freshItem;
            }
            return oldItem;
          });
        });
      }
    } catch (err) {
      console.error("Sync Error:", err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  // --- ✅ АВТО-ОБНОВЛЕНИЕ КАЖДЫЕ 15 СЕКУНД (ДЛЯ DEEP SCAN) ---
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (activeTab === 'deep' && videoList.length > 0) {
      interval = setInterval(() => {
        fetchFromDB(true); 
      }, 15000);
    }
    // Чистим таймер при смене вкладки или закрытии
    return () => {
        if (interval) clearInterval(interval);
    };
  }, [videoList.length, activeTab, query]);

  const extractUsername = (input: string): string => {
    // Извлекает username из URL или возвращает как есть, если уже username
    const trimmed = input.trim();
    
    // Если это URL TikTok, извлекаем username
    const urlMatch = trimmed.match(/tiktok\.com\/@([^/?]+)/);
    if (urlMatch) {
      return urlMatch[1];
    }
    
    // Если начинается с @, убираем его
    if (trimmed.startsWith('@')) {
      return trimmed.substring(1);
    }
    
    // Иначе возвращаем как есть (уже username)
    return trimmed;
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true); setError(''); setVideoList([]);

    try {
      if (activeTab === 'profiles') {
        const username = extractUsername(query);
        if (!username) {
          setError('Введите username или URL профиля TikTok');
          setLoading(false);
          return;
        }
        const response = await apiClient.get(`/profiles/${username}`);
        setCurrentReport(response.data);
        setSessionHistory(prev => [response.data, ...prev.filter(p => p.author.username !== response.data.author.username)]);
      } 
      else {
        const isDeep = activeTab === 'deep';
        // Отправляем запрос: бэкенд вернет Live данные и поставит задачу на рескан в БД
        const response = await apiClient.post('/trends/search', { 
          target: query,
          mode: isDeep ? deepMode : 'keywords',
          is_deep: isDeep,
          rescan_hours: rescanHours
        });
        setVideoList(response.data.items || []);
      }
    } catch (err: any) {
      console.error('Search error details:', err);
      const errorMessage = err.response?.data?.message || err.message || 'Ошибка связи с сервером';
      setError(`Ошибка: ${errorMessage}. Проверьте, что backend запущен на http://localhost:8000`);
    } finally { setLoading(false); }
  };

  const VideoCard = ({ item }: { item: any }) => {
    const views = item.stats?.playCount || 0;
    const initial = item.initial_stats?.playCount || views;
    const growth = views - initial; // Разница между Точкой Б и Точкой А

    return (
      <div className="group bg-zinc-900/40 border border-zinc-800/50 rounded-2xl overflow-hidden hover:border-blue-500/50 transition-all flex flex-col">
        <div className="relative aspect-[9/16] bg-black">
          <SafeImage src={item.cover_url} alt="Cover" className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
          
          {/*UTS & GROWTH BADGE */}
          <div className="absolute top-2 right-2 flex flex-col gap-1 items-end">
            <div className="bg-blue-600 text-white px-2 py-1 rounded-md text-[9px] font-black shadow-lg">
               UTS {item.uts_score > 0 ? item.uts_score.toFixed(1) : "WAIT"}
            </div>
            {growth > 0 && (
              <div className="bg-green-500 text-black px-2 py-0.5 rounded text-[8px] font-black animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.4)]">
                GROWTH 🚀
              </div>
            )}
          </div>

          <div className="absolute bottom-2 left-2 flex items-center gap-1 text-[10px] font-bold text-white drop-shadow-md">
            <Play className="w-3 h-3 fill-white" /> {views.toLocaleString()}
          </div>

          {/* ИНДИКАТОР РОСТА ПРОСМОТРОВ */}
          {growth > 0 && (
            <div className="absolute bottom-10 right-2 bg-zinc-900/90 border border-green-500/50 text-green-400 px-2 py-1 rounded text-[9px] font-bold">
              +{growth.toLocaleString()}
            </div>
          )}
        </div>
        <div className="p-3 flex-1 flex flex-col justify-between">
          <p className="text-[10px] text-zinc-400 line-clamp-2 italic leading-tight mb-3">"{item.title || item.description || "Без описания"}"</p>
          <a href={item.url} target="_blank" className="block w-full py-2 bg-zinc-800 hover:bg-blue-600 text-center rounded-lg text-[9px] font-black uppercase text-white transition-colors">Смотреть</a>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-100 pb-20 font-sans selection:bg-blue-500/30">
      <div className="max-w-7xl mx-auto px-4 py-10 flex flex-col items-center">
        
        {/* LOGO */}
        <div className="flex items-center gap-3 mb-10 animate-in fade-in slide-in-from-top-4 duration-700">
          <div className="p-2 bg-blue-600 rounded-xl shadow-[0_0_25px_rgba(37,99,235,0.4)]"><TrendingUp className="w-6 h-6 text-white" /></div>
          <h1 className="text-2xl font-black tracking-tighter uppercase italic">TrendScout Pro</h1>
        </div>

        {/* TABS */}
        <div className="flex p-1 bg-zinc-900 border border-zinc-800 rounded-2xl mb-10 overflow-x-auto max-w-full">
          {(['trends', 'profiles', 'deep'] as const).map((tab) => (
            <button key={tab} onClick={() => { setActiveTab(tab); setVideoList([]); setCurrentReport(null); setError(''); }}
              className={`flex items-center gap-2 px-8 py-2.5 rounded-xl text-[11px] font-black transition-all whitespace-nowrap ${
                activeTab === tab ? 'bg-zinc-800 text-white shadow-xl ring-1 ring-white/5' : 'text-zinc-500 hover:text-zinc-300'
              }`}>
              {tab === 'trends' ? 'ТРЕНДЫ' : tab === 'profiles' ? 'ПРОФИЛИ' : 'DEEP SCAN'}
            </button>
          ))}
        </div>

        {/* SEARCH BOX */}
        <div className="w-full max-w-2xl flex flex-col gap-4 mb-6">
          <div className="relative flex items-center bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden focus-within:border-blue-500/50 transition-all shadow-2xl">
            <Search className="ml-5 w-5 h-5 text-zinc-600" />
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder={activeTab === 'profiles' ? "Введите @username..." : "Введите тему для поиска..."}
              className="w-full bg-transparent py-4 px-4 text-sm outline-none text-white" />
            <button onClick={handleSearch} disabled={loading} className="mr-2 px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-black rounded-xl transition-all">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'АНАЛИЗ'}
            </button>
          </div>

          {/* MANUAL SYNC BUTTON */}
          <div className="flex gap-4 justify-center">
             {activeTab === 'deep' && videoList.length > 0 && (
                <button onClick={() => fetchFromDB()} className="flex items-center gap-2 px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-500 text-[10px] font-bold rounded-xl border border-zinc-800 transition-all">
                  <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> СИНХРОНИЗИРОВАТЬ С БД
                </button>
              )}
          </div>
        </div>

        {/* DEEP SCAN SETTINGS */}
        {activeTab === 'deep' && (
          <div className="w-full max-w-2xl mb-12 p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl animate-in fade-in slide-in-from-top-2">
            <div className="flex flex-col md:flex-row gap-6 items-center justify-between">
              <div className="flex p-1 bg-black rounded-xl border border-zinc-800">
                <button onClick={() => setDeepMode('keywords')} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[9px] font-black transition-all ${deepMode === 'keywords' ? 'bg-zinc-800 text-white' : 'text-zinc-600'}`}>
                  <TrendingUp className="w-3 h-3" /> ПО КЛЮЧУ
                </button>
                <button onClick={() => setDeepMode('username')} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[9px] font-black transition-all ${deepMode === 'username' ? 'bg-zinc-800 text-white' : 'text-zinc-600'}`}>
                  <User className="w-3 h-3" /> ПО ЮЗЕРУ
                </button>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">Рескан через (ч):</span>
                <input type="number" value={rescanHours} onChange={(e) => setRescanHours(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-16 bg-black border border-zinc-800 rounded-lg py-1.5 text-center text-xs font-bold text-blue-500 outline-none focus:border-blue-500/50" />
              </div>
            </div>
          </div>
        )}

        {error && <div className="text-red-400 bg-red-950/20 border border-red-900/40 px-6 py-3 rounded-xl mb-8 text-xs text-center">{error}</div>}

        {/* --- ОТЧЕТ ПРОФИЛЯ (100% Live) --- */}
        {activeTab === 'profiles' && currentReport && (
          <div className="w-full space-y-12 animate-in fade-in zoom-in duration-500">
             {/* Рендеринг отчета как в исходнике, но без сохранения в БД */}
             <div className="bg-zinc-900/30 border border-zinc-800 rounded-[2.5rem] p-8 backdrop-blur-md relative overflow-hidden">
                <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/5 blur-[120px] -z-10" />
                <div className="flex flex-col md:flex-row items-center gap-8 mb-12">
                  <div className="w-28 h-28 rounded-full border-4 border-blue-600/20 p-1 bg-black overflow-hidden shadow-2xl">
                    <SafeImage src={currentReport.author.avatar} alt="Avatar" className="w-full h-full rounded-full object-cover" />
                  </div>
                  <div className="flex-1 text-center md:text-left">
                    <h2 className="text-3xl font-black uppercase italic tracking-tight">@{currentReport.author.username}</h2>
                    <div className="mt-6 flex flex-wrap gap-8 justify-center md:justify-start">
                      <div className="flex flex-col"><span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mb-1">Followers</span><span className="text-2xl font-black">{currentReport.author.followers.toLocaleString()}</span></div>
                      <div className="flex flex-col border-l border-zinc-800 pl-8"><span className="text-[10px] text-zinc-500 font-bold uppercase flex items-center gap-1"><Activity className="w-3 h-3" /> Engagement</span><span className="text-2xl font-black text-blue-400">{currentReport.metrics.engagement_rate}%</span></div>
                      <div className="flex flex-col border-l border-zinc-800 pl-8"><span className="text-[10px] text-zinc-500 font-bold uppercase text-green-500">Viral Lift</span><span className="text-2xl font-black text-green-400">x{currentReport.metrics.avg_viral_lift}</span></div>
                      <div className="flex flex-col border-l border-zinc-800 pl-8"><span className="text-[10px] text-zinc-500 font-bold uppercase">Efficiency</span><span className="text-2xl font-black text-white">{currentReport.metrics.efficiency_score}/10</span></div>
                    </div>
                  </div>
                  <div className="bg-blue-600/10 border border-blue-500/20 p-5 rounded-3xl flex items-center gap-4 shadow-inner">
                    <Trophy className="w-10 h-10 text-blue-500" />
                    <div><p className="text-[10px] font-black text-blue-500 uppercase tracking-tighter">Status</p><p className="text-lg font-black uppercase italic">{currentReport.metrics.status}</p></div>
                  </div>
                </div>
                <div className="mb-14">
                  <h3 className="text-[11px] font-black text-zinc-500 uppercase tracking-[0.4em] mb-8 flex items-center gap-2"><Star className="w-4 h-4 text-yellow-500 fill-yellow-500" /> VIRAL MASTERPIECES (TOP 3)</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-8">{currentReport.top_3_hits.map((v: any, i: number) => <VideoCard key={`top-${i}`} item={v} />)}</div>
                </div>
                <div>
                  <h3 className="text-[11px] font-black text-zinc-500 uppercase tracking-[0.4em] mb-8 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-blue-500" /> RECENT AUDIT FEED (30 VIDEOS)</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-5">{currentReport.full_feed.map((v: any, i: number) => <VideoCard key={`feed-${i}`} item={v} />)}</div>
                </div>
             </div>
          </div>
        )}

        {/* --- СЕТКА ТРЕНДОВ И DEEP SCAN --- */}
        {activeTab !== 'profiles' && videoList.length > 0 && (
          <div className="w-full animate-in fade-in duration-700">
            <div className="flex items-center justify-between mb-8 px-2">
              <div className="flex items-center gap-2 text-zinc-500 text-[10px] font-black tracking-widest uppercase">
                {activeTab === 'deep' ? <Zap className="w-3 h-3 text-yellow-500 animate-pulse" /> : <Activity className="w-3 h-3 text-blue-500" />}
                {activeTab === 'deep' ? `Monitoring Live Viral Growth...` : 'Global Viral Content Results'}
              </div>
              <div className="text-[10px] font-bold bg-zinc-900 border border-zinc-800 px-4 py-1.5 rounded-xl text-zinc-400">
                {videoList.length} OBJECTS IDENTIFIED
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8">
              {videoList.map((v, i) => <VideoCard key={i} item={v} />)}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}