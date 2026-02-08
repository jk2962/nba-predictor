/**
 * Player Card Component
 */
import { Link } from 'react-router-dom';
import type { Player, TopPerformer } from '../types';

interface PlayerCardProps {
    player: Player | TopPerformer;
    showPredictions?: boolean;
}

export default function PlayerCard({ player, showPredictions = false }: PlayerCardProps) {
    const isTopPerformer = 'predicted_points' in player;
    const playerId = isTopPerformer
        ? (player as TopPerformer).player_id
        : (player as Player).id;
    const playerName = isTopPerformer
        ? (player as TopPerformer).player_name
        : (player as Player).name;

    const getPositionClass = (position: string | null) => {
        if (!position) return '';
        if (position.includes('G')) return 'position-G';
        if (position.includes('F')) return 'position-F';
        if (position.includes('C')) return 'position-C';
        return '';
    };

    return (
        <Link
            to={`/player/${playerId}`}
            className="card animate-fadeIn"
            style={{
                display: 'block',
                padding: '1.25rem',
                textDecoration: 'none',
                cursor: 'pointer',
            }}
        >
            <div style={{
                display: 'flex',
                gap: '1rem',
                alignItems: 'center',
            }}>
                {/* Player Image */}
                <div style={{
                    width: '80px',
                    height: '80px',
                    borderRadius: '1rem',
                    overflow: 'hidden',
                    background: 'var(--color-bg-tertiary)',
                    flexShrink: 0,
                }}>
                    {player.headshot_url ? (
                        <img
                            src={player.headshot_url}
                            alt={playerName}
                            style={{
                                width: '100%',
                                height: '100%',
                                objectFit: 'cover',
                            }}
                            onError={(e) => {
                                (e.target as HTMLImageElement).style.display = 'none';
                            }}
                        />
                    ) : (
                        <div style={{
                            width: '100%',
                            height: '100%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '2rem',
                        }}>
                            🏀
                        </div>
                    )}
                </div>

                {/* Player Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        marginBottom: '0.25rem',
                    }}>
                        {player.position && (
                            <span
                                className={`position-badge ${getPositionClass(player.position)}`}
                            >
                                {player.position.charAt(0)}
                            </span>
                        )}
                        <h3 style={{
                            fontSize: '1.1rem',
                            fontWeight: 600,
                            color: 'var(--color-text-primary)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                        }}>
                            {playerName}
                        </h3>
                    </div>

                    <p style={{
                        fontSize: '0.875rem',
                        color: 'var(--color-text-secondary)',
                        marginBottom: '0.75rem',
                    }}>
                        {player.team_abbreviation || player.team || 'Free Agent'}
                    </p>

                    {/* Stats */}
                    <div style={{
                        display: 'flex',
                        gap: '0.75rem',
                    }}>
                        {showPredictions && isTopPerformer ? (
                            <>
                                <StatBadge
                                    label="PTS"
                                    value={(player as TopPerformer).predicted_points}
                                    isPrediction
                                />
                                <StatBadge
                                    label="REB"
                                    value={(player as TopPerformer).predicted_rebounds}
                                    isPrediction
                                />
                                <StatBadge
                                    label="AST"
                                    value={(player as TopPerformer).predicted_assists}
                                    isPrediction
                                />
                            </>
                        ) : (
                            <>
                                {(player as Player).season_ppg != null && (
                                    <StatBadge label="PPG" value={(player as Player).season_ppg!} />
                                )}
                                {(player as Player).season_rpg != null && (
                                    <StatBadge label="RPG" value={(player as Player).season_rpg!} />
                                )}
                                {(player as Player).season_apg != null && (
                                    <StatBadge label="APG" value={(player as Player).season_apg!} />
                                )}
                            </>
                        )}
                    </div>
                </div>

                {/* Fantasy Score (for top performers) */}
                {isTopPerformer && (
                    <div style={{
                        textAlign: 'center',
                        padding: '0.75rem',
                        background: 'var(--gradient-primary)',
                        borderRadius: '0.75rem',
                        minWidth: '70px',
                    }}>
                        <div style={{
                            fontSize: '1.25rem',
                            fontWeight: 700,
                            color: 'white',
                        }}>
                            {(player as TopPerformer).fantasy_score.toFixed(1)}
                        </div>
                        <div style={{
                            fontSize: '0.65rem',
                            color: 'rgba(255,255,255,0.8)',
                            textTransform: 'uppercase',
                        }}>
                            Fantasy
                        </div>
                    </div>
                )}
            </div>
        </Link>
    );
}

function StatBadge({
    label,
    value,
    isPrediction = false
}: {
    label: string;
    value: number;
    isPrediction?: boolean;
}) {
    return (
        <div className="stat-badge" style={{
            background: isPrediction
                ? 'linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(251, 146, 60, 0.2))'
                : 'var(--gradient-card)',
            borderColor: isPrediction ? 'rgba(249, 115, 22, 0.3)' : undefined,
        }}>
            <span style={{
                color: isPrediction ? 'var(--color-nba-orange)' : 'var(--color-accent-primary)',
                fontWeight: 600,
            }}>
                {value.toFixed(1)}
            </span>
            <span style={{
                color: 'var(--color-text-muted)',
                fontSize: '0.75rem',
            }}>
                {label}
            </span>
        </div>
    );
}
