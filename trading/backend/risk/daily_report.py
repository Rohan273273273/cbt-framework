import logging
from datetime import datetime, timezone
import psycopg2
import psycopg2.extras
from config import settings
from gateway.alpaca_gateway import gateway
from risk.cro import get_daily_used_pct

logger = logging.getLogger(__name__)


def generate_report():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        account = gateway.get_account()
        equity = account.get("equity", 1000)
        daily_pnl = account.get("daily_pnl", 0)
        daily_pnl_pct = daily_pnl / equity * 100

        conn = psycopg2.connect(settings.timescale_url)
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                           SUM(pnl) as net_pnl
                    FROM trades
                    WHERE DATE(entry_time) = %s AND is_paper = %s
                """, (today, settings.paper))
                stats = dict(cur.fetchone() or {})
        conn.close()

        total = stats.get("total", 0) or 0
        wins = stats.get("wins", 0) or 0
        net_pnl = stats.get("net_pnl", 0) or 0
        win_rate = (wins / total * 100) if total > 0 else 0

        report = (
            f"\n{'='*50}\n"
            f"DAILY REPORT — {today}\n"
            f"{'='*50}\n"
            f"Equity:       ${equity:,.2f}\n"
            f"Day P&L:      ${daily_pnl:+,.2f} ({daily_pnl_pct:+.2f}%)\n"
            f"Trades today: {total}\n"
            f"Win rate:     {win_rate:.1f}%\n"
            f"Net PnL:      ${net_pnl:+,.2f}\n"
            f"Daily limit used: {get_daily_used_pct(equity):.1f}% / {settings.cro_max_daily_loss_pct}%\n"
            f"{'='*50}"
        )
        logger.info(report)
    except Exception as e:
        logger.error(f"Daily report failed: {e}")
