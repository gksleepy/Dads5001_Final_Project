"""
src/config.py — App configuration
"""

APP_TITLE        = "AI Stock Decision Support System"
DEFAULT_TICKERS  = ["NVDA", "GOOGL", "MSFT"]
SUPPORTED_TICKERS = [
    # Mega Cap Tech
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA",
    # Semiconductor
    "TSM", "ASML", "AMD", "INTC", "QCOM", "MU", "AVGO", "ARM", "AMAT",
    # Software / Cloud
    "ORCL", "CRM", "ADBE", "NOW", "SNOW", "PLTR",
    # Entertainment
    "NFLX", "DIS", "SPOT",
    # EV / Energy
    "RIVN", "NIO", "ENPH",
    # Finance
    "JPM", "BAC", "GS", "V", "MA", "PYPL",
    # Healthcare
    "JNJ", "PFE", "LLY",
    # Other
    "BRK-B", "UBER", "ABNB", "COIN", "SHOP",
]
USER_ID          = "demo_user"

# ช่วงเวลาข้อมูลหุ้น
PRICE_PERIOD = "1y"   # yfinance period string

# Groq model
GROQ_MODEL = "llama-3.3-70b-versatile"

# สี palette ต่อหุ้น
PALETTE = {
    # Mega Cap Tech
    "NVDA":  "#76b900",  # เขียว NVIDIA
    "GOOGL": "#4285F4",  # น้ำเงิน Google
    "MSFT":  "#00A4EF",  # ฟ้า Microsoft
    "AAPL":  "#A2AAAD",  # เทา Apple
    "AMZN":  "#FF9900",  # ส้ม Amazon
    "META":  "#0866FF",  # น้ำเงิน Meta
    "TSLA":  "#E31937",  # แดง Tesla
    # Semiconductor
    "TSM":   "#EE1C25",  # แดง TSMC
    "ASML":  "#0071C5",  # น้ำเงิน ASML
    "AMD":   "#ED1C24",  # แดง AMD
    "INTC":  "#0071C5",  # น้ำเงิน Intel
    "QCOM":  "#3253DC",  # น้ำเงิน Qualcomm
    "MU":    "#E4002B",  # แดง Micron
    "AVGO":  "#CC0000",  # แดงเข้ม Broadcom
    "ARM":   "#0091BD",  # ฟ้า ARM
    "AMAT":  "#00A0E4",  # ฟ้า Applied Materials
    # Software / Cloud
    "ORCL":  "#F80000",  # แดง Oracle
    "CRM":   "#00A1E0",  # ฟ้า Salesforce
    "ADBE":  "#FF0000",  # แดง Adobe
    "NOW":   "#62D84E",  # เขียว ServiceNow
    "SNOW":  "#29B5E8",  # ฟ้า Snowflake
    "PLTR":  "#7B68EE",  # ม่วง Palantir
    # Entertainment
    "NFLX":  "#E50914",  # แดง Netflix
    "DIS":   "#006E99",  # น้ำเงิน Disney
    "SPOT":  "#1DB954",  # เขียว Spotify
    # EV / Energy
    "RIVN":  "#00A651",  # เขียว Rivian
    "NIO":   "#00AEEF",  # ฟ้า NIO
    "ENPH":  "#F5A623",  # ส้ม Enphase
    # Finance
    "JPM":   "#005EB8",  # น้ำเงิน JPMorgan
    "BAC":   "#E31837",  # แดง BofA
    "GS":    "#7399C6",  # ฟ้าอ่อน Goldman
    "V":     "#1A1F71",  # กรมท่า Visa
    "MA":    "#EB001B",  # แดง Mastercard
    "PYPL":  "#003087",  # น้ำเงินเข้ม PayPal
    # Healthcare
    "JNJ":   "#D50032",  # แดง J&J
    "PFE":   "#0093D0",  # ฟ้า Pfizer
    "LLY":   "#D52B1E",  # แดง Eli Lilly
    # Other
    "BRK-B": "#7B6844",  # น้ำตาล Berkshire
    "UBER":  "#000000",  # ดำ Uber
    "ABNB":  "#FF5A5F",  # ชมพูแดง Airbnb
    "COIN":  "#0052FF",  # น้ำเงิน Coinbase
    "SHOP":  "#96BF48",  # เขียว Shopify
}

DEFAULT_PALETTE_COLOR = "#888888"

# Sector groupings สำหรับ Sector Screening (Top 10 ต่อ sector)
SECTORS = {
    "Technology": ["NVDA", "MSFT", "AAPL", "META", "GOOGL", "AMD", "ORCL", "CRM", "INTC", "QCOM"],
    "E-Commerce / Cloud": ["AMZN", "GOOGL", "MSFT", "SHOP", "BABA", "JD", "MELI", "ETSY", "EBAY", "PINS"],
    "EV / Clean Energy": ["TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "F", "GM", "PLUG", "ENPH"],
    "Finance": ["JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "AXP", "V", "MA"],
    "Healthcare": ["JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY", "AMGN", "GILD", "CVS", "UNH"],
}
