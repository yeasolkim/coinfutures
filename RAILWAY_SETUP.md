# Railway 설정 가이드

Railway를 사용하여 매일 자동으로 매매일지를 생성하는 방법입니다.

## 🚀 Railway 설정 단계

### 1. Railway 계정 생성
1. [Railway.app](https://railway.app)에 접속
2. GitHub 계정으로 로그인
3. "Start a New Project" 클릭

### 2. GitHub 저장소 연결
1. "Deploy from GitHub repo" 선택
2. `yeasolkim/coinfutures` 저장소 선택
3. "Deploy Now" 클릭

### 3. 환경변수 설정
Railway 대시보드에서 다음 환경변수들을 설정:

```
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_notion_database_id
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
BINANCE_TESTNET=false
```

### 4. Cron Job 설정
1. Railway 대시보드 → "Settings" 탭
2. "Cron Jobs" 섹션에서 "Add Cron Job" 클릭
3. 설정:
   - **Command**: `python railway_scheduler.py`
   - **Schedule**: `1 9 * * *` (매일 오전 9시 1분)
   - **Timezone**: `Asia/Seoul`

### 5. 배포 확인
1. "Deployments" 탭에서 배포 상태 확인
2. "Logs" 탭에서 실행 로그 확인

## 📋 Railway 장점

- ✅ **지역 제한 없음**: Binance API 정상 접근
- ✅ **무료 티어**: 월 500시간 무료
- ✅ **자동 배포**: GitHub 푸시 시 자동 배포
- ✅ **실시간 로그**: 실행 결과 실시간 확인
- ✅ **환경변수 관리**: 안전한 API 키 관리

## 🔧 문제 해결

### 배포 실패 시
1. Railway 로그 확인
2. 환경변수 설정 확인
3. requirements.txt 의존성 확인

### Cron Job 실행 안됨
1. 시간대 설정 확인 (Asia/Seoul)
2. 명령어 경로 확인
3. 권한 설정 확인

## 💰 비용

- **무료 티어**: 월 500시간 (매일 1분 실행 시 충분)
- **유료 플랜**: 월 $5부터 (더 많은 리소스 필요 시)

## 📞 지원

문제가 발생하면 Railway 로그를 확인하거나 GitHub Issues에 문의하세요. 