import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def setup_scheduler():
    from screeners.crypto_screener import run_screener
    from screeners.news_screener import run_news_screener
    from agents.graph import run_cycle
    from api.websocket.agent_log_stream import push_logs

    def _screener_job():
        try:
            run_screener()
        except Exception as e:
            logger.error(f"Screener job failed: {e}")

    def _news_job():
        try:
            run_news_screener()
        except Exception as e:
            logger.error(f"News job failed: {e}")

    async def _agent_cycle_job():
        try:
            logger.info("Agent cycle starting...")
            state = run_cycle()
            push_logs(state.get("agent_logs", []))
            logger.info(f"Agent cycle complete. Trade placed: {state.get('order_result') is not None}")
        except Exception as e:
            logger.error(f"Agent cycle failed: {e}")

    def _daily_report_job():
        try:
            from risk.daily_report import generate_report
            generate_report()
        except Exception as e:
            logger.error(f"Daily report failed: {e}")

    from config import settings

    scheduler.add_job(_screener_job, IntervalTrigger(seconds=60), id="screener",
                      max_instances=1, coalesce=True)
    scheduler.add_job(_news_job, IntervalTrigger(seconds=300), id="news",
                      max_instances=1, coalesce=True)
    scheduler.add_job(_agent_cycle_job, IntervalTrigger(seconds=settings.agent_cycle_interval_seconds),
                      id="agent_cycle", max_instances=1, coalesce=True)
    scheduler.add_job(_daily_report_job, CronTrigger(hour=0, minute=5), id="daily_report")

    scheduler.start()
    logger.info("Scheduler started: screener(60s), news(5min), agent_cycle(15min), daily_report(00:05 UTC)")
