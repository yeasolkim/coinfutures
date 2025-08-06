# 바이낸스 선물 거래 분석 및 Notion 자동화 시스템

바이낸스 선물 계정의 거래 데이터를 자동으로 분석하고, AI 피드백과 함께 Notion에 매매일지를 자동 생성하는 시스템입니다.

## 🎯 주요 기능

- **자동 거래 데이터 수집**: 바이낸스 선물 API를 통한 실시간 거래 내역 조회
- **Supabase 데이터 동기화**: Binance에서 데이터를 가져와서 Supabase의 trades, position_groups, daily_pnl 테이블 자동 업데이트
- **포지션 그룹핑**: Net Position 로직을 통한 정확한 포지션 생명주기 추적
- **기술적 분석**: RSI, MACD, 볼린저 밴드, 거래량 등 주요 지표 자동 계산
- **차트 생성**: 매매 타점이 표시된 전문적인 캔들스틱 차트 생성
- **AI 피드백**: OpenAI GPT-4를 활용한 매매 원칙 기반 자동 피드백
- **Notion 자동화**: 분석 결과를 구조화된 매매일지로 Notion에 자동 업로드

## 📋 요구사항

### Python 버전
- Python 3.8 이상

### 필요한 API 키
- **Binance API**: 선물 거래 내역 조회용
- **OpenAI API**: GPT-4 피드백 생성용  
- **Notion API**: 매매일지 자동 업로드용

## 🚀 설치 및 설정

### 1. 프로젝트 다운로드
```bash
git clone <repository-url>
cd coinfutures
```

### 2. 종속성 설치
```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정
`env_example.txt` 파일을 참고하여 `.env` 파일을 생성하고 API 키를 입력하세요:

```bash
cp env_example.txt .env
# .env 파일을 편집하여 실제 API 키 입력
```

### 4. API 키 설정 방법

#### Binance API
1. [Binance](https://www.binance.com)에 로그인
2. API Management → Create API
3. **선물 거래 권한 활성화** (Read Only 권한만 필요)
4. API Key와 Secret Key를 `.env` 파일에 입력

#### OpenAI API
1. [OpenAI Platform](https://platform.openai.com)에 로그인
2. API Keys 섹션에서 새 키 생성
3. GPT-4 사용 권한 확인
4. API Key를 `.env` 파일에 입력

#### Notion API
1. [Notion Developers](https://developers.notion.com)에서 Integration 생성
2. 권한: Read, Insert, Update content
3. Integration Token을 `.env` 파일에 입력
4. 매매일지용 Database 생성 및 Integration 연결
5. Database ID를 `.env` 파일에 입력

### 5. Notion 데이터베이스 설정

다음 속성을 가진 Notion 데이터베이스를 생성하세요:

| 속성명 | 타입 | 설명 |
|--------|------|------|
| 제목 | Title | 매매일지 제목 |
| 날짜 | Date | 거래 날짜 |
| 종목 | Rich Text | 거래 종목 |
| 거래횟수 | Number | 총 거래 횟수 |
| 평균가 | Number | 평균 체결가 |
| 총거래량 | Number | 총 거래량 |
| 수수료 | Number | 총 수수료 |
| 평가등급 | Select | AI 평가 등급 (A, B, C, D, F) |
| 상태 | Select | 처리 상태 |

## 💻 사용법

### 기본 사용법
```bash
# 특정 날짜의 매매일지 생성 (Supabase 기반)
python main.py --date 2024-01-15

# 오늘 날짜의 매매일지 생성
python main.py

# Binance → Supabase 동기화 테스트
python test_binance_sync.py --date 2024-01-15

# 포지션 그룹핑 업데이트
python position_grouper.py
```

### Supabase 설정 (선택사항)
Supabase를 사용하면 더 정확한 포지션 추적이 가능합니다:

1. **Supabase 프로젝트 생성**
   - [Supabase](https://supabase.com)에서 새 프로젝트 생성
   - API URL과 API Key를 `.env` 파일에 추가

2. **테이블 초기화**
   ```bash
   python -c "from supabase_manager import SupabaseManager; import asyncio; asyncio.run(SupabaseManager().initialize_tables())"
   ```

3. **데이터 동기화**
   ```bash
   python test_binance_sync.py --date 2024-01-15
   ```

### 옵션 설명
- `--symbol`: 분석할 거래 종목 (기본값: BTCUSDT)
- `--date`: 분석 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)
- `--timeframes`: 분석할 시간 프레임들 (기본값: 5m 15m 4h)
- `--all-symbols`: 여러 종목 일괄 처리
- `--config-check`: API 키 설정 확인

## 📊 출력물

### 1. Supabase 데이터베이스
- **trades**: 모든 거래 기록
- **position_groups**: 포지션 그룹 (Net Position 로직)
- **daily_pnl**: 일별 P&L 요약

### 2. Notion 매매일지
- 감정적 제목과 함께한 매매일지
- 포지션별 상세 분석
- 일별 거래 요약
- 시장 난이도 평가

### 3. 로그 파일
- `trading_journal.log`: 실행 로그 및 오류 기록

### 4. 텍스트 파일 (`reports/` 디렉토리)
- `daily_journal_YYYY-MM-DD.txt`: 텍스트 형식 매매일지

## 🔧 매매 원칙 커스터마이징

`config.py` 파일의 `TRADING_RULES` 부분을 수정하여 본인만의 매매 원칙을 설정할 수 있습니다:

```python
TRADING_RULES = """
나의 매매 원칙:
1. RSI 30 이하일 때만 매수 진입
2. RSI 70 이상일 때 매도 진입 고려
3. MACD 저점에서 반등 시 진입
4. 거래량 증가 확인 시 진입
5. 추세 확인 후 진입
6. 손절은 진입가 대비 2% 이내
7. 익절은 진입가 대비 3% 이상
"""
```

## 🛠️ 프로젝트 구조

```
coinfutures/
├── main.py                    # 메인 실행 파일 (매매일지 생성)
├── config.py                  # 설정 및 API 키 관리
├── utils.py                   # 공통 유틸리티 함수
├── binance_connector.py       # 바이낸스 API 연동
├── supabase_manager.py        # Supabase 데이터베이스 관리
├── position_grouper.py        # 포지션 그룹핑 로직
├── test_binance_sync.py       # Binance → Supabase 동기화 테스트
├── notion_uploader.py         # Notion API 연동
├── sentiment_generator.py     # 감정적 매매일지 생성
├── requirements.txt           # Python 종속성
├── env_example.txt            # 환경변수 예시
├── README.md                  # 사용 설명서
└── reports/                   # 생성된 매매일지 저장소
```

## ⚠️ 주의사항

1. **API 키 보안**: `.env` 파일을 절대 공개 저장소에 업로드하지 마세요
2. **API 제한**: 바이낸스 API 요청 제한을 준수하세요
3. **테스트넷**: 처음 사용 시 `BINANCE_TESTNET=True`로 설정하여 테스트해보세요
4. **권한 설정**: Binance API는 선물 거래 Read 권한만 활성화하세요
5. **OpenAI 비용**: GPT-4 사용 시 토큰 사용량에 따른 비용이 발생합니다

## 🐛 문제 해결

### 일반적인 오류

1. **API 키 오류**
   ```bash
   python main.py --config-check
   ```

2. **Notion 연결 실패**
   - Database ID가 올바른지 확인
   - Integration이 Database에 연결되어 있는지 확인

3. **차트 생성 실패**
   - 한글 폰트 설치 확인
   - `charts/` 디렉토리 권한 확인

4. **거래 데이터 없음**
   - 지정한 날짜에 실제 거래가 있었는지 확인
   - 심볼명이 정확한지 확인 (예: BTCUSDT)

### 로그 확인
상세한 오류 정보는 `trading_journal.log` 파일에서 확인할 수 있습니다.

## 📈 확장 기능

### 1. Railway 자동 실행 (권장)
Railway를 사용하면 지역 제한 없이 매일 자동으로 실행됩니다:

1. **Railway 설정**
   - [Railway.app](https://railway.app)에서 계정 생성
   - GitHub 저장소 연결
   - 환경변수 설정 (API 키들)
   - Cron Job 설정 (매일 오전 9시 1분)

2. **상세 설정 방법**
   - `RAILWAY_SETUP.md` 파일 참조
   - 무료 티어로 충분 (월 500시간)

### 2. GitHub Actions 자동 실행 (지역 제한 있음)
GitHub Actions는 Binance API 지역 제한으로 인해 권장하지 않습니다.

### 2. 로컬 자동 실행
cron 또는 Task Scheduler를 사용하여 매일 자동 실행:
```bash
# 매일 오전 9시에 실행
0 9 * * * cd /path/to/coinfutures && python main.py
```

### 2. 다중 계정 지원
여러 바이낸스 계정의 거래를 분석하려면 설정 파일을 수정하세요.

### 3. 알림 기능
Discord, Slack, Telegram 등으로 분석 완료 알림을 추가할 수 있습니다.

## 🤝 기여하기

버그 리포트, 기능 제안, 코드 개선은 언제나 환영합니다!

## 📄 라이선스

MIT License

## 📞 지원

문제가 발생하면 이슈를 생성하거나 문서를 확인해주세요.

---

**⚡ 안전한 거래하세요! 이 도구는 분석 목적이며, 투자 결정은 본인의 책임입니다.** 