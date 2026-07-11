// 규칙 기반 앱 분류기
// AI(Claude)를 쓸 수 없거나 실패했을 때의 폴백. 흔한 한국/글로벌 앱 사전 기반.
// 각 카테고리의 keywords 중 하나라도 앱 이름(공백 제거·소문자)에 포함되면 그 폴더로 분류.
// 순서가 곧 우선순위 — 위쪽 카테고리가 먼저 매칭된다.

const CATEGORIES = [
  { name: "소통·SNS", emoji: "💬", keywords: [
    "카카오톡", "카톡", "라인", "line", "텔레그램", "telegram", "인스타", "insta", "페이스북",
    "facebook", "메신저", "messenger", "트위터", "twitter", "스레드", "thread", "틱톡", "tiktok",
    "왓츠앱", "whatsapp", "디스코드", "discord", "스냅챗", "snapchat", "밴드", "band", "위챗", "wechat",
    "카카오스토리", "네이버카페", "블라인드", "everytime", "에브리타임" ] },

  { name: "금융·결제", emoji: "💰", keywords: [
    "토스", "toss", "카카오뱅크", "카뱅", "카카오페이", "kakaopay", "삼성페이", "samsungpay",
    "네이버페이", "naverpay", "페이코", "payco", "페이팔", "paypal", "국민", "kb", "신한", "우리은행",
    "하나은행", "농협", "nh", "기업은행", "ibk", "sc제일", "케이뱅크", "kbank", "뱅크샐러드",
    "증권", "미래에셋", "키움", "nh투자", "한국투자", "업비트", "upbit", "빗썸", "bithumb",
    "코인", "coin", "보험", "카드", "현대카드", "롯데카드", "삼성카드" ] },

  { name: "쇼핑", emoji: "🛒", keywords: [
    "쿠팡", "coupang", "11번가", "지마켓", "gmarket", "옥션", "auction", "위메프", "티몬", "tmon",
    "무신사", "musinsa", "지그재그", "에이블리", "ably", "당근", "번개장터", "번장", "중고나라",
    "올리브영", "oliveyoung", "아마존", "amazon", "알리", "ali", "테무", "temu", "쉬인", "shein",
    "마켓컬리", "컬리", "kurly", "ssg", "신세계", "롯데온", "홈플러스", "이마트", "브랜디",
    "네이버쇼핑", "kream", "크림" ] },

  { name: "음식·배달", emoji: "🍔", keywords: [
    "배달의민족", "배민", "요기요", "yogiyo", "쿠팡이츠", "땡겨요", "스타벅스", "스벅", "starbucks",
    "맥도날드", "버거킹", "이디야", "메가커피", "컴포즈", "투썸", "빽다방", "다이닝", "캐치테이블",
    "테이블링", "망고플레이트", "식신" ] },

  { name: "교통·지도", emoji: "🗺️", keywords: [
    "네이버지도", "카카오맵", "카카오맵", "카카오t", "카카오택시", "카카오내비", "티맵", "tmap",
    "구글맵", "googlemaps", "지도", "map", "쏘카", "socar", "그린카", "따릉이", "코레일", "korail",
    "ktx", "srt", "고속버스", "티머니", "카카오버스", "지하철", "네이버지하철", "우버", "uber",
    "카카오모빌리티", "타다" ] },

  { name: "미디어·영상", emoji: "🎬", keywords: [
    "유튜브", "youtube", "넷플릭스", "netflix", "디즈니", "disney", "티빙", "tving", "웨이브",
    "wavve", "왓챠", "watcha", "쿠팡플레이", "라프텔", "laftel", "아프리카", "afreeca", "숲", "soop",
    "트위치", "twitch", "치지직", "chzzk", "네이버시리즈", "카카오페이지", "카카오웹툰", "네이버웹툰",
    "레진", "피키캐스트" ] },

  { name: "음악", emoji: "🎵", keywords: [
    "멜론", "melon", "지니", "genie", "벅스", "bugs", "플로", "flo", "스포티파이", "spotify",
    "애플뮤직", "applemusic", "사운드클라우드", "soundcloud", "유튜브뮤직", "youtubemusic",
    "바이브", "vibe", "네이버바이브" ] },

  { name: "사진·카메라", emoji: "📷", keywords: [
    "갤러리", "gallery", "카메라", "camera", "스노우", "snow", "소다", "soda", "b612", "포토",
    "photo", "포토샵", "photoshop", "라이트룸", "lightroom", "vsco", "픽스아트", "picsart",
    "픽샵", "포토스케이프", "구글포토", "googlephotos", "cymera", "유라이크", "ulike", "푸디" ] },

  { name: "게임", emoji: "🎮", keywords: [
    "게임", "game", "리그오브레전드", "롤", "lol", "배틀그라운드", "배그", "pubg", "원신", "genshin",
    "브롤스타즈", "brawl", "쿠키런", "clash", "클래시", "로블록스", "roblox", "마인크래프트",
    "minecraft", "포켓몬", "pokemon", "리니지", "던파", "메이플", "maple", "우마무스메", "블루아카이브",
    "명일방주", "발로란트", "valorant", "스팀", "steam" ] },

  { name: "업무·생산성", emoji: "🗂️", keywords: [
    "노션", "notion", "슬랙", "slack", "팀즈", "teams", "줌", "zoom", "지메일", "gmail", "아웃룩",
    "outlook", "메일", "mail", "캘린더", "calendar", "드라이브", "drive", "원드라이브", "onedrive",
    "닥스", "docs", "엑셀", "excel", "워드", "word", "파워포인트", "powerpoint", "ppt", "한글",
    "hwp", "에버노트", "evernote", "트렐로", "trello", "지라", "jira", "아사나", "asana", "피그마",
    "figma", "링크드인", "linkedin", "구글독스", "스프레드시트", "잔디", "flow", "먼데이", "monday",
    "옵시디언", "obsidian", "미리캔버스", "캔바", "canva", "챗지피티", "chatgpt", "gpt", "클로드",
    "claude", "제미나이", "gemini", "퍼플렉시티", "perplexity" ] },

  { name: "건강·운동", emoji: "🏃", keywords: [
    "삼성헬스", "shealth", "헬스", "health", "나이키", "nike", "런데이", "runday", "캐시워크",
    "cashwalk", "눔", "noom", "홈트", "필라", "만보기", "스트라바", "strava", "가민", "garmin",
    "핏빗", "fitbit", "다이어트", "diet", "인바디", "inbody", "굿닥", "똑닥", "삼성헬스" ] },

  { name: "교육·독서", emoji: "📚", keywords: [
    "듀오링고", "duolingo", "클래스101", "class101", "인프런", "inflearn", "유데미", "udemy",
    "밀리의서재", "밀리", "리디", "ridi", "교보문고", "교보", "알라딘", "예스24", "yes24", "스픽",
    "speak", "케이크", "cake", "산타", "santa", "야나두", "시원스쿨", "콴다", "qanda", "클래스팅",
    "에듀", "edu", "위인전", "브런치", "brunch" ] },

  { name: "여행·숙박", emoji: "✈️", keywords: [
    "야놀자", "yanolja", "여기어때", "아고다", "agoda", "부킹", "booking", "에어비앤비", "airbnb",
    "스카이스캐너", "skyscanner", "트리플", "triple", "마이리얼트립", "인터파크", "interpark",
    "호텔스", "hotels", "익스피디아", "expedia", "네이버항공", "제주항공", "대한항공", "아시아나",
    "티웨이", "여행" ] },

  { name: "유틸리티", emoji: "🔧", keywords: [
    "계산기", "calculator", "시계", "clock", "알람", "alarm", "날씨", "weather", "파일", "file",
    "나침반", "compass", "손전등", "flashlight", "녹음", "recorder", "메모", "memo", "노트", "note",
    "qr", "스캐너", "scanner", "클리너", "cleaner", "백신", "v3", "알약", "번역", "translate",
    "파파고", "papago", "다운로드", "돋보기", "타이머", "timer" ] },

  { name: "생활·기타", emoji: "🏠", keywords: [
    "정부24", "gov", "홈택스", "hometax", "국민비서", "질병관리청", "coov", "쿠브", "네이버",
    "naver", "다음", "daum", "구글", "google", "크롬", "chrome", "웨일", "whale", "사파리", "safari",
    "엣지", "edge", "삼성", "samsung", "갤럭시", "galaxy", "설정", "setting", "전화", "phone",
    "연락처", "contact", "메시지", "message", "삼성월렛", "스마트싱스", "smartthings", "기가지니",
    "리모컨", "아파트아이", "우리집", "직방", "다방", "부동산" ] },
];

function normalize(s) {
  return String(s).toLowerCase().replace(/\s+/g, "");
}

// 앱 이름 하나를 카테고리 이름으로 매핑 (없으면 null)
function classifyOne(app) {
  const n = normalize(app);
  if (!n) return null;
  for (const cat of CATEGORIES) {
    for (const kw of cat.keywords) {
      if (n.includes(normalize(kw))) return cat;
    }
  }
  return null;
}

// 앱 배열 → 폴더 배열 [{name, emoji, apps}]
export function ruleCategorize(apps) {
  const buckets = new Map(); // name -> {name, emoji, apps, order}
  const unmatched = [];

  apps.forEach((app) => {
    const cat = classifyOne(app);
    if (!cat) {
      unmatched.push(app);
      return;
    }
    if (!buckets.has(cat.name)) {
      buckets.set(cat.name, {
        name: cat.name,
        emoji: cat.emoji,
        apps: [],
        order: CATEGORIES.indexOf(cat),
      });
    }
    buckets.get(cat.name).apps.push(app);
  });

  const folders = [...buckets.values()]
    .sort((a, b) => a.order - b.order)
    .map(({ name, emoji, apps }) => ({ name, emoji, apps }));

  if (unmatched.length) {
    folders.push({ name: "기타", emoji: "📦", apps: unmatched });
  }
  return folders;
}
