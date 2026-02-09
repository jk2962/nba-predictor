/**
 * Player Card Component
 */
import { Link } from 'react-router-dom';
import type { Player, TopPerformer } from '../types';

type StatFilter = 'fantasy' | 'points' | 'rebounds' | 'assists';

interface PlayerCardProps {
    player: Player | TopPerformer;
    showPredictions?: boolean;
    statFilter?: StatFilter;
}

export default function PlayerCard({ player, statFilter = 'fantasy' }: PlayerCardProps) {
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

    // Get the appropriate stat value and label based on the filter
    const getDisplayStat = (): { value: number; label: string } => {
        if (!isTopPerformer) {
            const p = player as Player;
            switch (statFilter) {
                case 'points':
                    return { value: p.season_ppg ?? 0, label: 'PPG' };
                case 'rebounds':
                    return { value: p.season_rpg ?? 0, label: 'RPG' };
                case 'assists':
                    return { value: p.season_apg ?? 0, label: 'APG' };
                default:
                    return { value: (p.fantasy_score ?? 0), label: 'FPT' };
            }
        }
        const p = player as TopPerformer;
        switch (statFilter) {
            case 'points':
                return { value: p.predicted_points, label: 'PTS' };
            case 'rebounds':
                return { value: p.predicted_rebounds, label: 'REB' };
            case 'assists':
                return { value: p.predicted_assists, label: 'AST' };
            default:
                return { value: p.fantasy_score, label: 'FPT' };
        }
    };

    const displayStat = getDisplayStat();

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
                    {/* Name Row */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: 'var(--space-sm)',
                        marginBottom: 'var(--space-xs)',
                    }}>
                        {player.position && (
                            <span
                                className={`position-badge ${getPositionClass(player.position)}`}
                                style={{ flexShrink: 0 }}
                            >
                                {player.position.charAt(0)}
                            </span>
                        )}
                        <h3 style={{
                            fontSize: '1rem',
                            fontWeight: 600,
                            color: 'var(--text-primary)',
                            letterSpacing: '-0.01em',
                            lineHeight: 1.3,
                        }}>
                            {playerName}
                        </h3>
                    </div>

                    {/* Team + Stat Row */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-md)',
                    }}>
                        <p style={{
                            fontSize: '0.8125rem',
                            color: 'var(--text-tertiary)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.02em',
                            margin: 0,
                        }}>
                            {player.team_abbreviation || player.team || 'Free Agent'}
                        </p>

                        {/* Stat Display */}
                        <div style={{
                            display: 'flex',
                            alignItems: 'baseline',
                            gap: 'var(--space-xs)',
                        }}>
                            <span style={{
                                fontSize: '1.5rem',
                                fontWeight: 700,
                                color: 'var(--hot)',
                                fontVariantNumeric: 'tabular-nums',
                            }}>
                                {displayStat.value.toFixed(1)}
                            </span>
                            <span style={{
                                fontSize: '0.75rem',
                                fontWeight: 500,
                                color: 'var(--text-tertiary)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.02em',
                            }}>
                                {displayStat.label}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </Link>
    );
}
