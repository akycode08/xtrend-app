// Описание Тренда (для поиска)
export interface Trend {
    id: number;
    platform_id: string;
    url: string;
    description: string;
    cover_url: string;
    vertical: string;
    author_username: string;
    author_followers: number;
    stats: {
      playCount: number;
      diggCount: number;
      commentCount: number;
      shareCount: number;
    };
    uts_score: number;      // Твой главный балл
    similarity_score: number;
    reach_score: number;
    uplift_score: number;
    ai_summary?: string;
  }
  
  // Описание Профиля (для аудита)
  export interface ProfileReport {
    source: 'cache' | 'live';
    channel: {
      id: string;
      name: string;      // username
      nickName: string;  // display name
      fans: number;
      avatar: string;
      signature?: string; // bio
    };
    videos: any[]; // Тут список видео
  }
  
  // Описание Конкурента (для Spy Mode)
  export interface CompetitorData {
    username: string;
    top_3_hits: any[];
    latest_feed: any[];
  }