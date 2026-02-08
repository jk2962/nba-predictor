from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguedashplayerstats
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_player_names():
    logger.info("Fetching active players...")
    all_active = players.get_active_players()
    
    jokic_static = [p for p in all_active if "Jokic" in p['full_name'] or "Jokić" in p['full_name']]
    doncic_static = [p for p in all_active if "Doncic" in p['full_name'] or "Dončić" in p['full_name']]
    
    logger.info(f"Static Jokic: {jokic_static}")
    logger.info(f"Static Doncic: {doncic_static}")
    
    logger.info("Fetching stats names...")
    try:
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season='2024-25',
            per_mode_detailed='PerGame'
        ).get_data_frames()[0]
        
        jokic_stats = stats[stats['PLAYER_NAME'].str.contains("Jokic|Jokić", case=False, na=False)]
        doncic_stats = stats[stats['PLAYER_NAME'].str.contains("Doncic|Dončić", case=False, na=False)]
        
        logger.info(f"Stats Jokic: {jokic_stats[['PLAYER_ID', 'PLAYER_NAME']].to_dict('records')}")
        logger.info(f"Stats Doncic: {doncic_stats[['PLAYER_ID', 'PLAYER_NAME']].to_dict('records')}")
        
    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")

if __name__ == "__main__":
    check_player_names()
