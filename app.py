"""
RSI Check - 3개의 RSI 지표를 활용한 매매 신호 웹 앱
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

from data_fetcher import DataFetcher
from rsi_calculator import RSICalculator
from signal_generator import SignalGenerator


# 페이지 설정
st.set_page_config(
    page_title="RSI Check - 매매 신호 분석",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 제목
st.title("📈 RSI Check - 매매 신호 분석 대시보드")
st.markdown("**3개의 RSI 지표(단기/중기/장기)를 활용한 매수/매도 시점 추천**")
st.markdown("---")

# 인스턴스 생성
@st.cache_resource
def get_instances():
    """싱글톤 인스턴스 생성"""
    fetcher = DataFetcher()
    rsi_calc = RSICalculator(short_period=9, medium_period=14, long_period=26)
    signal_gen = SignalGenerator(rsi_calc)
    return fetcher, rsi_calc, signal_gen

fetcher, rsi_calc, signal_gen = get_instances()

# 사이드바 설정
st.sidebar.header("⚙️ 설정")

# 종목 선택
stock_list = fetcher.get_stock_list()
stock_names = list(stock_list.keys())
selected_stock_name = st.sidebar.selectbox(
    "종목 선택",
    stock_names,
    index=0
)
selected_symbol = stock_list[selected_stock_name]

# 기간 선택
period_options = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y"
}
selected_period_name = st.sidebar.selectbox(
    "조회 기간",
    list(period_options.keys()),
    index=2  # 기본 6개월
)
selected_period = period_options[selected_period_name]

# 새로고침 버튼
if st.sidebar.button("🔄 데이터 새로고침", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ 정보")
st.sidebar.markdown("""
**RSI 설정:**
- 단기: 9일
- 중기: 14일
- 장기: 26일

**신호 기준:**
- 과매도: RSI < 30
- 과매수: RSI > 70
""")

# 데이터 로딩 함수
@st.cache_data(ttl=300)  # 5분 캐시
def load_stock_data(symbol, period):
    """주식 데이터 로드"""
    return fetcher.get_stock_data(symbol, period)

@st.cache_data(ttl=60)  # 1분 캐시
def load_current_price(symbol):
    """현재가 로드"""
    return fetcher.get_current_price(symbol)

# 메인 화면
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.subheader(f"📊 {selected_stock_name} ({selected_symbol})")

# 현재가 정보 표시
with st.spinner("현재가 정보를 가져오는 중..."):
    current_price, change_percent, change_amount = load_current_price(selected_symbol)
    
    if current_price:
        with col2:
            st.metric(
                label="현재가",
                value=f"${current_price:.2f}" if selected_symbol not in ['069500.KS'] else f"₩{current_price:,.0f}",
                delta=f"{change_amount:.2f}" if selected_symbol not in ['069500.KS'] else f"{change_amount:,.0f}"
            )
        
        with col3:
            st.metric(
                label="등락률",
                value=f"{change_percent:.2f}%",
                delta=None
            )
    else:
        with col2:
            st.warning("현재가 정보를 가져올 수 없습니다.")

# 데이터 로드
with st.spinner("데이터를 불러오는 중..."):
    data = load_stock_data(selected_symbol, selected_period)

if data is None or data.empty:
    st.error("❌ 데이터를 불러올 수 없습니다. 다른 종목을 선택하거나 나중에 다시 시도해주세요.")
    st.stop()

# RSI 계산
data_with_rsi = rsi_calc.calculate_all_rsi(data)

# 신호 생성
signal, description, strength = signal_gen.generate_signal(data_with_rsi)
signal_color = signal_gen.get_signal_color(signal)

# 신호 표시
st.markdown("### 🎯 매매 신호")
col1, col2 = st.columns([1, 2])

with col1:
    # 신호 표시
    signal_emoji = {
        "강력 매수": "🟦",
        "매수": "🟢",
        "관망": "⚪",
        "매도": "🟠",
        "강력 매도": "🔴"
    }
    st.markdown(f"## {signal_emoji.get(signal, '⚪')} {signal}")
    
    # 신호 강도 프로그레스바
    if strength > 0:
        st.progress(strength / 100)
        st.caption(f"신호 강도: {strength:.1f}/100")

with col2:
    st.info(f"**분석 결과:** {description}")

st.markdown("---")

# 최신 RSI 값 표시
short_rsi, medium_rsi, long_rsi = rsi_calc.get_latest_rsi_values(data_with_rsi)

col1, col2, col3 = st.columns(3)

with col1:
    rsi_status = "과매도" if short_rsi < 30 else "과매수" if short_rsi > 70 else "중립"
    rsi_color = "🔴" if short_rsi < 30 else "🔵" if short_rsi > 70 else "⚪"
    st.metric(
        label=f"{rsi_color} 단기 RSI (9일)",
        value=f"{short_rsi:.2f}",
        delta=rsi_status
    )

with col2:
    rsi_status = "과매도" if medium_rsi < 30 else "과매수" if medium_rsi > 70 else "중립"
    rsi_color = "🔴" if medium_rsi < 30 else "🔵" if medium_rsi > 70 else "⚪"
    st.metric(
        label=f"{rsi_color} 중기 RSI (14일)",
        value=f"{medium_rsi:.2f}",
        delta=rsi_status
    )

with col3:
    rsi_status = "과매도" if long_rsi < 30 else "과매수" if long_rsi > 70 else "중립"
    rsi_color = "🔴" if long_rsi < 30 else "🔵" if long_rsi > 70 else "⚪"
    st.metric(
        label=f"{rsi_color} 장기 RSI (26일)",
        value=f"{long_rsi:.2f}",
        delta=rsi_status
    )

st.markdown("---")

# 차트 생성
st.markdown("### 📈 가격 및 RSI 차트")

# 서브플롯 생성 (4행 1열)
fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    subplot_titles=('가격', '단기 RSI (9일)', '중기 RSI (14일)', '장기 RSI (26일)'),
    row_heights=[0.4, 0.2, 0.2, 0.2]
)

# 가격 차트 (캔들스틱)
fig.add_trace(
    go.Candlestick(
        x=data_with_rsi.index,
        open=data_with_rsi['Open'],
        high=data_with_rsi['High'],
        low=data_with_rsi['Low'],
        close=data_with_rsi['Close'],
        name='가격',
        increasing_line_color='green',
        decreasing_line_color='red'
    ),
    row=1, col=1
)

# 단기 RSI 차트
fig.add_trace(
    go.Scatter(
        x=data_with_rsi.index,
        y=data_with_rsi['RSI_Short'],
        name='단기 RSI (9일)',
        line=dict(color='blue', width=2)
    ),
    row=2, col=1
)

# 중기 RSI 차트
fig.add_trace(
    go.Scatter(
        x=data_with_rsi.index,
        y=data_with_rsi['RSI_Medium'],
        name='중기 RSI (14일)',
        line=dict(color='purple', width=2)
    ),
    row=3, col=1
)

# 장기 RSI 차트
fig.add_trace(
    go.Scatter(
        x=data_with_rsi.index,
        y=data_with_rsi['RSI_Long'],
        name='장기 RSI (26일)',
        line=dict(color='orange', width=2)
    ),
    row=4, col=1
)

# RSI 기준선 추가 (과매수/과매도)
for row in [2, 3, 4]:
    # 과매수 (70)
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=row, col=1)
    # 과매도 (30)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=row, col=1)
    # 중립 (50)
    fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=row, col=1)

# 레이아웃 설정
fig.update_layout(
    height=1000,
    showlegend=False,
    hovermode='x unified',
    xaxis_rangeslider_visible=False
)

# Y축 범위 설정
fig.update_yaxes(title_text="가격", row=1, col=1)
fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)
fig.update_yaxes(title_text="RSI", range=[0, 100], row=4, col=1)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 전체 종목 요약
st.markdown("### 📋 전체 종목 요약")

@st.cache_data(ttl=300)
def load_all_signals(period):
    """모든 종목의 신호 로드"""
    all_data = {}
    for name, symbol in stock_list.items():
        df = fetcher.get_stock_data(symbol, period)
        if df is not None and not df.empty:
            df_with_rsi = rsi_calc.calculate_all_rsi(df)
            all_data[f"{name} ({symbol})"] = df_with_rsi
    
    return signal_gen.get_all_signals(all_data)

with st.spinner("전체 종목 신호를 불러오는 중..."):
    summary_df = load_all_signals(selected_period)
    
    if not summary_df.empty:
        # 신호에 따라 색상 적용
        def highlight_signal(row):
            colors = {
                "강력 매수": "background-color: #0066cc; color: white",
                "매수": "background-color: #00cc66; color: white",
                "관망": "background-color: #cccccc; color: black",
                "매도": "background-color: #ff9933; color: white",
                "강력 매도": "background-color: #cc0000; color: white"
            }
            return [colors.get(row['신호'], '')] * len(row)
        
        styled_df = summary_df.style.apply(highlight_signal, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.warning("전체 종목 데이터를 불러올 수 없습니다.")

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
<p>⚠️ <strong>투자 유의사항</strong></p>
<p>이 앱은 RSI 지표를 기반으로 한 참고 정보를 제공합니다.</p>
<p>실제 투자 결정은 본인의 판단과 책임 하에 이루어져야 하며, 투자 권유가 아닙니다.</p>
<p>과거 데이터는 미래 수익을 보장하지 않습니다.</p>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<div style='text-align: center; color: gray; font-size: 0.8em;'>마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
