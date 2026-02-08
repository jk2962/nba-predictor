/**
 * Player Detail Page
 */
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import StatsChart from '../components/StatsChart';
import PredictionCard from '../components/PredictionCard';
import { LoadingState, ErrorState } from '../components/LoadingState';
import { playerApi } from '../services/api';
import type { PlayerDetail, GameStats, PredictionResult } from '../types';

export default function PlayerDetailPage() {
    const { playerId } = useParams<{ playerId: string }>();
    const [player, setPlayer] = useState<PlayerDetail | null>(null);
    const [games, setGames] = useState<GameStats[]>([]);
    const [prediction, setPrediction] = useState<PredictionResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            if (!playerId) return;

            setLoading(true);
            setError(null);

            try {
                const [playerData, gamesData, predictionData] = await Promise.all([
                    playerApi.getPlayer(parseInt(playerId)),
                    playerApi.getPlayerGames(parseInt(playerId), 10),
                    playerApi.getPlayerPredictions(parseInt(playerId)).catch(() => null),
                ]);

                setPlayer(playerData);
                setGames(gamesData);
                setPrediction(predictionData);
            } catch (err) {
                setError('Failed to load player data.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [playerId]);

    if (loading) return <LoadingState message="Loading player data..." />;
    if (error) return <ErrorState message={error} />;
    if (!player) return <ErrorState message="Player not found" />;

    return (
        <div className="container" style={{ padding: '2rem 1.5rem' }}>
            {/* Back Link */}
            <Link
                to="/"
                style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    color: 'var(--color-text-secondary)',
                    marginBottom: '1.5rem',
                    fontSize: '0.9rem',
                }}
            >
                ← Back to Home
            </Link>

            {/* Player Header */}
            <header className="card" style={{
                display: 'flex',
                gap: '2rem',
                padding: '2rem',
                marginBottom: '2rem',
                flexWrap: 'wrap',
            }}>
                {/* Player Image */}
                <div style={{
                    width: '160px',
                    height: '160px',
                    borderRadius: '1rem',
                    overflow: 'hidden',
                    background: 'var(--color-bg-tertiary)',
                    flexShrink: 0,
                }}>
                    {player.headshot_url ? (
                        <img
                            src={player.headshot_url}
                            alt={player.name}
                            style={{
                                width: '100%',
                                height: '100%',
                                objectFit: 'cover',
                            }}
                            onError={(e) => {
                                (e.target as HTMLImageElement).src = '';
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
                            fontSize: '4rem',
                        }}>
                            🏀
                        </div>
                    )}
                </div>

                {/* Player Info */}
                <div style={{ flex: 1, minWidth: '200px' }}>
                    <h1 style={{
                        fontSize: '2rem',
                        fontWeight: 700,
                        marginBottom: '0.5rem',
                    }}>
                        {player.name}
                    </h1>

                    <div style={{
                        display: 'flex',
                        gap: '1rem',
                        flexWrap: 'wrap',
                        marginBottom: '1.5rem',
                    }}>
                        <InfoBadge label="Team" value={player.team_abbreviation || player.team || 'FA'} />
                        <InfoBadge label="Position" value={player.position || 'N/A'} />
                        <InfoBadge label="Height" value={player.height || 'N/A'} />
                        <InfoBadge label="Weight" value={player.weight ? `${player.weight} lbs` : 'N/A'} />
                    </div>

                    {/* Season Stats */}
                    <div style={{
                        display: 'flex',
                        gap: '1.5rem',
                        flexWrap: 'wrap',
                    }}>
                        <StatDisplay label="PPG" value={player.season_ppg} color="#6366f1" />
                        <StatDisplay label="RPG" value={player.season_rpg} color="#22c55e" />
                        <StatDisplay label="APG" value={player.season_apg} color="#f97316" />
                        <StatDisplay label="FG%" value={player.season_fg_pct} suffix="%" />
                        <StatDisplay label="3P%" value={player.season_fg3_pct} suffix="%" />
                        <StatDisplay label="MPG" value={player.season_mpg} />
                    </div>
                </div>
            </header>

            {/* Main Content Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                gap: '1.5rem',
            }}>
                {/* Prediction Card */}
                {prediction && (
                    <PredictionCard prediction={prediction} />
                )}

                {/* Performance Chart */}
                <div className="card" style={{ padding: '1.5rem' }}>
                    <h3 style={{
                        fontSize: '1.1rem',
                        fontWeight: 600,
                        marginBottom: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                    }}>
                        <span>📈</span>
                        Recent Performance
                    </h3>

                    {games.length > 0 ? (
                        <StatsChart games={games} prediction={prediction || undefined} />
                    ) : (
                        <div style={{
                            textAlign: 'center',
                            padding: '2rem',
                            color: 'var(--color-text-secondary)',
                        }}>
                            No recent games available
                        </div>
                    )}
                </div>
            </div>

            {/* Recent Games Table */}
            {games.length > 0 && (
                <div className="card" style={{ marginTop: '1.5rem', overflow: 'hidden' }}>
                    <h3 style={{
                        fontSize: '1.1rem',
                        fontWeight: 600,
                        padding: '1.5rem',
                        borderBottom: '1px solid rgba(255,255,255,0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                    }}>
                        <span>📋</span>
                        Last {games.length} Games
                    </h3>

                    <div style={{ overflowX: 'auto' }}>
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Opponent</th>
                                    <th>MIN</th>
                                    <th>PTS</th>
                                    <th>REB</th>
                                    <th>AST</th>
                                    <th>STL</th>
                                    <th>BLK</th>
                                    <th>FG%</th>
                                    <th>3P%</th>
                                </tr>
                            </thead>
                            <tbody>
                                {games.map((game) => (
                                    <tr key={game.id}>
                                        <td>{new Date(game.game_date).toLocaleDateString()}</td>
                                        <td>
                                            {game.is_home ? 'vs' : '@'} {game.opponent_abbreviation || game.opponent_team}
                                        </td>
                                        <td>{game.minutes.toFixed(0)}</td>
                                        <td style={{ fontWeight: 600, color: '#6366f1' }}>{game.points}</td>
                                        <td style={{ fontWeight: 600, color: '#22c55e' }}>{game.rebounds}</td>
                                        <td style={{ fontWeight: 600, color: '#f97316' }}>{game.assists}</td>
                                        <td>{game.steals}</td>
                                        <td>{game.blocks}</td>
                                        <td>{(game.fg_pct * 100).toFixed(1)}%</td>
                                        <td>{(game.fg3_pct * 100).toFixed(1)}%</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

function InfoBadge({ label, value }: { label: string; value: string }) {
    return (
        <div style={{
            padding: '0.5rem 1rem',
            background: 'var(--color-bg-tertiary)',
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
        }}>
            <span style={{ color: 'var(--color-text-muted)' }}>{label}: </span>
            <span style={{ fontWeight: 500 }}>{value}</span>
        </div>
    );
}

function StatDisplay({
    label,
    value,
    color = 'var(--color-text-primary)',
    suffix = ''
}: {
    label: string;
    value: number | null;
    color?: string;
    suffix?: string;
}) {
    if (value === null || value === undefined) return null;

    return (
        <div style={{ textAlign: 'center' }}>
            <div style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color,
            }}>
                {value.toFixed(1)}{suffix}
            </div>
            <div style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
            }}>
                {label}
            </div>
        </div>
    );
}
