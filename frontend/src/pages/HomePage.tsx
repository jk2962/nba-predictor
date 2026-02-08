/**
 * Home Page - Search and Top Performers
 */
import { useState, useEffect } from 'react';
import SearchBar from '../components/SearchBar';
import PlayerCard from '../components/PlayerCard';
import { LoadingState, ErrorState, EmptyState } from '../components/LoadingState';
import { playerApi, metricsApi } from '../services/api';
import type { TopPerformer, AllModelMetrics } from '../types';

export default function HomePage() {
    const [topPerformers, setTopPerformers] = useState<TopPerformer[]>([]);
    const [metrics, setMetrics] = useState<AllModelMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sortBy, setSortBy] = useState<'fantasy' | 'points' | 'rebounds' | 'assists'>('fantasy');

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [performers, modelMetrics] = await Promise.all([
                playerApi.getTopPerformers({ limit: 10, stat: sortBy }),
                metricsApi.getMetrics().catch(() => null),
            ]);
            setTopPerformers(performers);
            setMetrics(modelMetrics);
        } catch (err) {
            setError('Failed to load data. Make sure the backend is running.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [sortBy]);

    return (
        <div className="container" style={{ padding: '2rem 1.5rem' }}>
            {/* Hero Section */}
            <section style={{
                textAlign: 'center',
                marginBottom: '3rem',
            }}>
                <h1 style={{
                    fontSize: '2.75rem',
                    fontWeight: 700,
                    marginBottom: '1rem',
                    background: 'linear-gradient(135deg, #fff 0%, #94a3b8 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                }}>
                    NBA Performance Predictor
                </h1>
                <p style={{
                    fontSize: '1.125rem',
                    color: 'var(--color-text-secondary)',
                    maxWidth: '600px',
                    margin: '0 auto 2rem',
                }}>
                    AI-powered predictions for fantasy basketball. Search players, view stats,
                    and get next-game performance forecasts.
                </p>

                {/* Search Bar */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'center',
                    marginBottom: '2rem',
                }}>
                    <SearchBar placeholder="Search for any NBA player..." />
                </div>

                {/* Model Metrics Badge */}
                {metrics && (
                    <div style={{
                        display: 'flex',
                        justifyContent: 'center',
                        gap: '1.5rem',
                        flexWrap: 'wrap',
                    }}>
                        <MetricBadge
                            label="Points Model"
                            mae={metrics.points_model.mae}
                        />
                        <MetricBadge
                            label="Rebounds Model"
                            mae={metrics.rebounds_model.mae}
                        />
                        <MetricBadge
                            label="Assists Model"
                            mae={metrics.assists_model.mae}
                        />
                    </div>
                )}
            </section>

            {/* Top Performers Section */}
            <section>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '1.5rem',
                    flexWrap: 'wrap',
                    gap: '1rem',
                }}>
                    <h2 style={{
                        fontSize: '1.5rem',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                    }}>
                        <span>🔥</span>
                        Top Predicted Performers
                    </h2>

                    {/* Sort Filter */}
                    <div style={{
                        display: 'flex',
                        gap: '0.5rem',
                    }}>
                        {(['fantasy', 'points', 'rebounds', 'assists'] as const).map((stat) => (
                            <button
                                key={stat}
                                onClick={() => setSortBy(stat)}
                                className={sortBy === stat ? 'btn btn-primary' : 'btn btn-secondary'}
                                style={{
                                    padding: '0.5rem 1rem',
                                    fontSize: '0.85rem',
                                    textTransform: 'capitalize',
                                }}
                            >
                                {stat}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Content */}
                {loading ? (
                    <LoadingState message="Loading top performers..." />
                ) : error ? (
                    <ErrorState message={error} onRetry={fetchData} />
                ) : topPerformers.length === 0 ? (
                    <EmptyState
                        title="No predictions available"
                        description="Run the seed script to populate player data and train models."
                        icon="📊"
                    />
                ) : (
                    <div className="grid-players">
                        {topPerformers.map((player, index) => (
                            <div
                                key={player.player_id}
                                className="animate-fadeIn"
                                style={{ animationDelay: `${index * 0.05}s` }}
                            >
                                <PlayerCard player={player} showPredictions />
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}

function MetricBadge({ label, mae }: { label: string; mae: number }) {
    const isGood = mae < 5;

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            background: 'var(--color-bg-tertiary)',
            borderRadius: '2rem',
            fontSize: '0.85rem',
        }}>
            <span style={{
                color: isGood ? 'var(--color-success)' : 'var(--color-warning)',
            }}>
                {isGood ? '✓' : '⚠'}
            </span>
            <span style={{ color: 'var(--color-text-secondary)' }}>
                {label}:
            </span>
            <span style={{
                fontWeight: 600,
                color: isGood ? 'var(--color-success)' : 'var(--color-warning)',
            }}>
                MAE {mae.toFixed(2)}
            </span>
        </div>
    );
}
