# 🚀 바이낸스 선물 거래 분석 시스템 - 빠른 시작

## 🎉 **현재 완벽 작동 상태**

✅ **바이낸스 실시간 데이터** - 거래 내역 + K라인  
✅ **AI 기술 분석** - RSI, MACD, 볼링거밴드 등  
✅ **전문 차트 생성** - 캔들스틱 + 지표 차트  
✅ **GPT-4 AI 피드백** - 매매 원칙 기반 분석  
❌ **Notion 자동 업로드** - 토큰 이슈 (수동 가능)

---

## ⚡ **즉시 사용 가능한 명령어**

### **1. 비트코인 분석**
```bash
cd /Users/yeasolkim/Documents/GitHub/coinfutures
source trading_env/bin/activate
python3 quick_analysis.py BTCUSDT
```

### **2. 이더리움 분석**
```bash
python3 quick_analysis.py ETHUSDT
```

### **3. 기타 코인 분석**
```bash
python3 quick_analysis.py SOLUSDT
python3 quick_analysis.py ADAUSDT
python3 quick_analysis.py DOGEUSDT
```

### **4. 전체 시스템 실행 (Notion 제외)**
```bash
python3 main.py --symbol BTCUSDT
```

---

## 📊 **실행 결과**

### **실시간 분석 출력:**
```
💰 현재 가격: 113,324 USDT
🟡 RSI: 45.9 - 중립
📊 MACD: 23.49 / Signal: 69.30 (하락)
📊 거래량: 0.09x (낮음)
📊 볼린저밴드: 15% (중간 위치)

📈 최근 24시간 거래: 6개
📍 최근 거래: BUY @ 112,850

🤖 AI 종합 평가: C등급
💪 주요 장점:
   • 가격 추세를 확인하고 상승 추세에서 매수 진입
   • 수수료를 통제하려는 노력
🔧 개선 포인트:
   • RSI 과매도/과매수 시점 활용 부족
   • MACD 신호 타이밍 개선 필요
```

### **자동 생성 파일:**
- `charts/BTCUSDT_5m_20250803_134154.png` - 캔들차트
- `charts/BTCUSDT_indicators_20250803_134154.png` - 지표차트

---

## 🎯 **핵심 기능**

### **📈 실시간 데이터 수집**
- **바이낸스 선물 거래 내역** (최근 24시간)
- **K라인 데이터** (5분/15분/4시간봉)
- **현재 시세 및 거래량**

### **🔍 기술적 분석**
- **RSI** - 과매수/과매도 판단
- **MACD** - 추세 전환 시점
- **볼린저밴드** - 변동성 및 지지/저항
- **거래량 분석** - 시장 관심도
- **EMA, 스토캐스틱, ATR** 등

### **🎨 전문 차트**
- **캔들스틱 차트** - 매수/매도 타점 표시
- **기술지표 차트** - 다중 지표 통합 분석
- **고해상도 PNG** - 300 DPI 전문 품질

### **🤖 AI 분석**
- **GPT-4 기반** 매매 원칙 비교 분석
- **등급 평가** (A~F)
- **장점/개선점** 구체적 피드백
- **매매 추천** 및 리스크 분석

---

## 🛠️ **Notion 연동 해결 방법**

현재 Database ID는 설정됨: `2440db11b50e803f9c98c5213f93d2f0`

### **해결 단계:**
1. [Notion Integrations](https://www.notion.so/profile/integrations) 접속
2. **"coin-futures"** Integration 클릭
3. **"Access"** 탭에서 **"Add pages"** 클릭
4. [제공해주신 Database](https://www.notion.so/2440db11b50e803f9c98c5213f93d2f0) 선택
5. **"Configuration"** 탭에서 **새 토큰 복사**
6. 새 토큰을 `.env` 파일에 업데이트

---

## 💡 **사용 팁**

### **다양한 시간대 분석**
```bash
# 오전 장 시작 후
python3 quick_analysis.py BTCUSDT

# 오후 변동성 높은 시간
python3 quick_analysis.py ETHUSDT

# 저녁 미국 시장 연동
python3 quick_analysis.py SOLUSDT
```

### **차트 확인**
```bash
# 생성된 차트 보기
open charts/
ls -la charts/ | tail -5
```

### **로그 확인**
```bash
# 상세 로그 보기
tail -f *.log
```

---

## 🎁 **현재 상태**

**✅ 즉시 사용 가능:**
- 실시간 암호화폐 분석
- 전문가급 차트 생성  
- AI 매매 피드백
- 기술지표 종합 분석

**📊 이미 생성된 차트들:**
- BTC 분석 차트 (173KB, 107KB)
- ETH 분석 차트 (168KB, 101KB)

**🚀 지금 바로 사용해보세요!**
```bash
python3 quick_analysis.py BTCUSDT
```

---

*⚡ 1분만에 완전한 암호화폐 분석 완료!*  
*🎯 Notion 연동은 선택사항 - 핵심 기능 모두 작동!* 