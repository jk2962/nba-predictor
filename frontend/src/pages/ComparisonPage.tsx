/**
 * Comparison Page - Compare 2-3 players side by side
 */
import { useState } from 'react';
import SearchBar from '../components/SearchBar';
import { ComparisonChart } from '../components/StatsChart';
import { LoadingState, EmptyState } from '../components/LoadingState';
import { playerApi } from '../services/api';
import type { PlayerSearchResult, PredictionResult, PlayerDetail } from '../types';

interface SelectedPlayer {
    info: PlayerDetail;
    prediction: PredictionResult | null;
}

export default function ComparisonPage() {
    const [selectedPlayers, setSelectedPlayers] = useState<SelectedPlayer[]>([]);
    const [loading, setLoading] = useState(false);

    const handleSelectPlayer = async (player: PlayerSearchResult) => {
        if (selectedPlayers.length >= 3) {
            alert('Maximum 3 players can be compared');
            return;
        }

        if (selectedPlayers.some(p => p.info.id === player.id)) {
            return; // Already selected
        }

        setLoading(true);
        try {
            const [info, prediction] = await Promise.all([
                playerApi.getPlayer(player.id),
                playerApi.getPlayerPredictions(player.id).catch(() => null),
            ]);

            setSelectedPlayers(prev => [...prev, { info, prediction }]);
        } catch (error) {
            console.error('Failed to load player:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleRemovePlayer = (playerId: number) => {
        setSelectedPlayers(prev => prev.filter(p => p.info.id !== playerId));
    };

    const predictions = selectedPlayers
        .filter(p => p.prediction)
        .map(p => p.prediction!);

    return (
        <div className="container" style={{ padding: '2rem 1.5rem' }}>
            {/* Header */}
            <header style={{ marginBottom: '2rem' }}>
                <h1 style={{
                    fontSize: '2rem',
                    fontWeight: 700,
                    marginBottom: '0.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                }}>
                    <span>⚖️</span>
                    Player Comparison
                </h1>
                <p style={{
                    color: 'var(--color-text-secondary)',
                    marginBottom: '1.5rem',
                }}>
                    Compare predictions and stats for up to 3 players side by side
                </p>

                {/* Search */}
                <div style={{ maxWidth: '400px' }}>
                    <SearchBar
                        placeholder="Add player to compare..."
                        onSelect={handleSelectPlayer}
                        autoNavigate={false}
                    />
                </div>
            </header>

            {/* Loading */}
            {loading && <LoadingState message="Loading player..." />}

            {/* Empty State */}
            {selectedPlayers.length === 0 && !loading && (
                <EmptyState
                    title="No players selected"
                    description="Search and add 2-3 players to compare their predictions and stats."
                    icon="⚖️"
                />
            )}

            {/* Selected Players */}
            {selectedPlayers.length > 0 && (
                <>
                    {/* Player Cards Row */}
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: `repeat(${selectedPlayers.length}, 1fr)`,
                        gap: '1.5rem',
                        marginBottom: '2rem',
                    }}>
                        {selectedPlayers.map(({ info, prediction }) => (
                            <div key={info.id} className="card" style={{ padding: '1.5rem' }}>
                                {/* Remove Button */}
                                <button
                                    onClick={() => handleRemovePlayer(info.id)}
                                    style={{
                                        position: 'absolute',
                                        top: '0.75rem',
                                        right: '0.75rem',
                                        background: 'var(--color-bg-tertiary)',
                                        border: 'none',
                                        borderRadius: '50%',
                                        width: '28px',
                                        height: '28px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: '0.875rem',
                                        color: 'var(--color-text-secondary)',
                                    }}
                                >
                                    ✕
                                </button>

                                {/* Player Info */}
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '1rem',
                                    marginBottom: '1.5rem',
                                }}>
                                    <div style={{
                                        width: '60px',
                                        height: '60px',
                                        borderRadius: '0.75rem',
                                        overflow: 'hidden',
                                        background: 'var(--color-bg-tertiary)',
                                    }}>
                                        {info.headshot_url ? (
                                            <img
                                                src={info.headshot_url}
                                                alt={info.name}
                                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                            />
                                        ) : (
                                            <div style={{
                                                width: '100%',
                                                height: '100%',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                fontSize: '1.5rem',
                                            }}>
                                                🏀
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        <h3 style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                                            {info.name}
                                        </h3>
                                        <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                                            {info.team_abbreviation} • {info.position}
                                        </p>
                                    </div>
                                </div>

                                {/* Season Stats */}
                                <div style={{ marginBottom: '1.5rem' }}>
                                    <h4 style={{
                                        fontSize: '0.8rem',
                                        color: 'var(--color-text-muted)',
                                        textTransform: 'uppercase',
                                        marginBottom: '0.75rem',
                                    }}>
                                        Season Averages
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                                        <StatCell label="PPG" value={info.season_ppg} />
                                        <StatCell label="RPG" value={info.season_rpg} />
                                        <StatCell label="APG" value={info.season_apg} />
                                    </div>
                                </div>

                                {/* Predictions */}
                                {prediction && (
                                    <div>
                                        <h4 style={{
                                            fontSize: '0.8rem',
                                            color: 'var(--color-text-muted)',
                                            textTransform: 'uppercase',
                                            marginBottom: '0.75rem',
                                        }}>
                                            🔮 Next Game
                                        </h4>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                                            <StatCell
                                                label="PTS"
                                                value={prediction.predicted_points}
                                                isPrediction
                                            />
                                            <StatCell
                                                label="REB"
                                                value={prediction.predicted_rebounds}
                                                isPrediction
                                            />
                                            <StatCell
                                                label="AST"
                                                value={prediction.predicted_assists}
                                                isPrediction
                                            />
                                        </div>

                                        {prediction.fantasy_score && (
                                            <div style={{
                                                marginTop: '1rem',
                                                textAlign: 'center',
                                                padding: '0.75rem',
                                                background: 'var(--gradient-primary)',
                                                borderRadius: '0.5rem',
                                            }}>
                                                <div style={{ fontSize: '0.7rem', opacity: 0.8 }}>FANTASY</div>
                                                <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                                                    {prediction.fantasy_score.toFixed(1)}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Comparison Chart */}
                    {predictions.length >= 2 && (
                        <div className="card" style={{ padding: '1.5rem' }}>
                            <h3 style={{
                                fontSize: '1.1rem',
                                fontWeight: 600,
                                marginBottom: '1rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                            }}>
                                <span>📊</span>
                                Prediction Comparison
                            </h3>
                            <ComparisonChart predictions={predictions} />
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

function StatCell({
    label,
    value,
    color,
    isPrediction = false,
}: {
    label: string;
    value: number | null;
    color?: string;
    isPrediction?: boolean;
}) {
    if (value === null || value === undefined) return <div />;

    return (
        <div style={{
            textAlign: 'center',
            padding: '0.5rem',
            background: isPrediction ? 'rgba(249, 115, 22, 0.1)' : 'rgba(0,0,0,0.2)',
            borderRadius: '0.5rem',
        }}>
            <div style={{
                fontSize: '1.1rem',
                fontWeight: 600,
                color,
            }}>
                {value.toFixed(1)}
            </div>
            <div style={{
                fontSize: '0.65rem',
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
            }}>
                {label}
            </div>
        </div>
    );
}
