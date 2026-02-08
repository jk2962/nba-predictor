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
                gap: 'var(--space-md)',
                alignItems: 'center',
            }}>
                {/* Player Image */}
                <div style={{
                    width: '72px',
                    height: '72px',
                    borderRadius: 'var(--radius-lg)',
                    overflow: 'hidden',
                    background: 'var(--surface-3)',
                    border: '1px solid var(--border)',
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
                            fontSize: '1.5rem',
                            fontWeight: 700,
                            color: 'var(--text-muted)',
                        }}>
                            {playerName.charAt(0)}
                        </div>
                    )}
                </div>

                {/* Player Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-sm)',
                        marginBottom: 'var(--space-xs)',
                    }}>
                        {player.position && (
                            <span
                                className={`position-badge ${getPositionClass(player.position)}`}
                            >
                                {player.position.charAt(0)}
                            </span>
                        )}
                        <h3 style={{
                            fontSize: '1rem',
                            fontWeight: 600,
                            color: 'var(--text-primary)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            letterSpacing: '-0.01em',
                        }}>
                            {playerName}
                        </h3>
                    </div>

                    <p style={{
                        fontSize: '0.8125rem',
                        color: 'var(--text-tertiary)',
                        marginBottom: 'var(--space-sm)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.02em',
                    }}>
                        {player.team_abbreviation || player.team || 'Free Agent'}
                    </p>

                    {/* Stats */}
                    <div style={{
                        display: 'flex',
                        gap: 'var(--space-sm)',
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
                        textAlign: 'right',
                        minWidth: '64px',
                    }}>
                        <div className="data-primary" style={{
                            fontSize: '1.75rem',
                            color: 'var(--hot)',
                            marginBottom: 'var(--space-xs)',
                        }}>
                            {(player as TopPerformer).fantasy_score.toFixed(1)}
                        </div>
                        <div className="data-label">
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
        <div className="stat-badge">
            <span style={{
                color: isPrediction ? 'var(--hot)' : 'var(--text-primary)',
                fontWeight: 700,
                fontSize: '0.875rem',
            }}>
                {value.toFixed(1)}
            </span>
            <span style={{
                color: 'var(--text-tertiary)',
                fontSize: '0.6875rem',
                textTransform: 'uppercase',
                letterSpacing: '0.02em',
            }}>
                {label}
            </span>
        </div>
    );
}
